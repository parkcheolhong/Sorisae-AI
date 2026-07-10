from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import Request
from sqlalchemy.orm import Session

from .flow_trace import (
    build_admin_flow_trace,
    build_lightweight_flow_trace,
    build_multi_command_plan,
)
from .project_context_store import get_project_context_bundle, upsert_project_memory_snapshot
from .llm_client import call_orchestrator_chat_llm
from .session_store import load_chat_session_snapshot, save_chat_session_snapshot
from .web_search import build_web_grounding_block, fetch_web_grounding, should_use_web_search
from .models import (
    AutoConnectMeta,
    AdvisoryEvidenceItem,
    AdvisoryNextAction,
    AdvisoryQuestion,
    ConversationMessage,
    OrchestratorChatRequest,
    OrchestratorChatResponse,
    ProposalItem,
    TargetPatchHint,
    TechnologyRecommendation,
    WebGroundingItem,
)


def _normalize_chat_message(message: str) -> str:
    return " ".join(str(message or "").strip().split())


def _contains_any(text: str, tokens: List[str]) -> bool:
    return any(token in text for token in tokens)


def _is_banter_message(message: str) -> bool:
    normalized = _normalize_chat_message(message)
    lowered = normalized.lower().rstrip("!?.,~ ")
    if not lowered:
        return False
    if lowered in {
        "안녕",
        "안녕하세요",
        "반가워",
        "반갑습니다",
        "고마워",
        "감사해",
        "감사합니다",
        "오케이",
        "okay",
        "ok",
        "hello",
        "hi",
        "hey",
    }:
        return True
    if len(lowered) <= 12 and _contains_any(lowered, ["ㅋㅋ", "ㅎㅎ", "ㄱㅅ", "thx", "thanks"]):
        return True
    return False


def _is_meta_conversation_question(message: str) -> bool:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return False
    return _contains_any(
        lowered,
        [
            "자유롭게 질문",
            "자유 질문",
            "질문해도 돼",
            "물어봐도 돼",
            "잡담해도 돼",
            "대화해도 돼",
            "이어서 물어봐도 돼",
            "편하게 질문",
            "질문 가능",
            "잡담 가능",
            "그냥 이어서 물어봐도 돼",
        ],
    )


def _is_freepace_conversation_mode(requested_conversation_mode: str) -> bool:
    normalized = str(requested_conversation_mode or "").strip().lower()
    if not normalized:
        return True
    return normalized in {
        "auto",
        "free",
        "freepace",
        "free_pace",
        "freetalk",
        "free_talk",
        "chat",
        "casual",
        "natural",
    }


def _should_force_reciprocal_question(requested_conversation_mode: str, response_style: str) -> bool:
    mode = str(requested_conversation_mode or "").strip().lower()
    style = str(response_style or "").strip().lower()
    if mode in {"reverse_question", "reciprocal", "interview"}:
        return True
    if "reverse_question" in style or "reciprocal" in style:
        return True
    return False


def _merge_conversation_dicts(*conversation_sets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for conversation in conversation_sets:
        for item in conversation or []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            timestamp = str(item.get("timestamp") or "").strip()
            if not role or not content:
                continue
            key = (role, content, timestamp)
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
    return merged[-60:]


def _message_models_to_dicts(messages: List[ConversationMessage]) -> List[Dict[str, Any]]:
    return [message.model_dump() for message in messages]


def _extract_session_id(request: OrchestratorChatRequest, auto_connect: AutoConnectMeta) -> str:
    return str(request.session_id or request.run_id or auto_connect.connection_id or "").strip()


def _chat_session_owner_id(current_user: Any) -> str | None:
    owner_id = getattr(current_user, "id", None)
    if owner_id is None:
        return None
    normalized = str(owner_id).strip()
    return normalized or None


def _load_session_state(
    request: OrchestratorChatRequest,
    auto_connect: AutoConnectMeta,
    *,
    session_owner_id: str | None = None,
) -> tuple[str, Dict[str, Any]]:
    session_id = _extract_session_id(request, auto_connect)
    snapshot = load_chat_session_snapshot(session_id, session_owner_id=session_owner_id) if session_id else {}
    if snapshot:
        request.conversation = _merge_conversation_dicts(
            list(snapshot.get("conversation") or []),
            list(request.conversation or []),
        )
        session_memory = dict(snapshot.get("project_memory") or {})
        session_memory.update(dict(request.project_memory or {}))
        request.project_memory = session_memory
    return session_id, snapshot


def _save_response_session(
    session_id: str,
    response: OrchestratorChatResponse,
    *,
    project_memory: Dict[str, Any],
    session_owner_id: str | None = None,
) -> None:
    if not session_id:
        return
    save_chat_session_snapshot(
        session_id,
        {
            "session_id": session_id,
            "run_id": response.run_id,
            "updated_at": datetime.now().isoformat(),
            "conversation": _message_models_to_dicts(response.conversation),
            "conversation_summary": response.conversation_summary,
            "inferred_goal": response.inferred_goal,
            "project_memory": project_memory,
            "open_questions": [item.prompt for item in response.clarification_questions],
            "technology_recommendations": [item.model_dump() for item in response.technology_recommendations],
            "new_technology_candidates": list(response.new_technology_candidates or []),
            "next_action_suggestions": [item.model_dump() for item in response.next_action_suggestions],
            "session_owner_id": session_owner_id,
        },
        session_owner_id=session_owner_id,
    )


def _resolve_tone_preset(
    requested_conversation_mode: str,
    response_style: str,
    tone_preset: str,
) -> tuple[str, str, str]:
    preset = str(tone_preset or "").strip().lower()
    mode = str(requested_conversation_mode or "").strip().lower()
    style = str(response_style or "").strip().lower()

    if preset in {"execution", "directive", "run"}:
        return "execution", "directive_fixed", "execution"
    if preset in {"concise", "brief", "short"}:
        return "concise", mode or "free", "concise"
    if preset in {"free_talk", "free", "natural", "casual"}:
        return "free_talk", "free", "free_talk"

    if mode == "directive_fixed" or style == "execution":
        return "execution", "directive_fixed", "execution"
    if style in {"concise", "brief", "short"}:
        return "concise", mode or "free", "concise"
    normalized_mode = "free" if mode in {"", "auto"} else mode
    normalized_style = "free_talk" if style in {"", "auto", "balanced"} else style
    return "free_talk", normalized_mode, normalized_style


def _extract_tone_preset_from_text(message: str) -> str | None:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return None

    if lowered in {"1", "1번", "1번으로", "자유", "자유대화", "자유 대화"}:
        return "free_talk"
    if lowered in {"2", "2번", "2번으로", "간결", "짧게", "간단히"}:
        return "concise"
    if lowered in {"3", "3번", "3번으로", "실행형", "지시형", "바로 실행"}:
        return "execution"

    if _contains_any(lowered, ["1번", "1 번"]):
        return "free_talk"
    if _contains_any(lowered, ["2번", "2 번"]):
        return "concise"
    if _contains_any(lowered, ["3번", "3 번"]):
        return "execution"

    if _contains_any(lowered, ["실행형", "지시형", "실행 모드", "바로 실행", "실행 중심"]):
        return "execution"
    if _contains_any(lowered, ["간결", "짧게", "핵심만", "요약", "짧은 답"]):
        return "concise"
    if _contains_any(lowered, ["자유대화", "자유 대화", "편하게", "자연스럽게", "잡담처럼"]):
        return "free_talk"
    return None


def _infer_tone_preset_from_history(conversation: List[Dict[str, Any]]) -> str | None:
    for item in reversed(conversation or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").strip().lower() != "user":
            continue
        selected = _extract_tone_preset_from_text(str(item.get("content") or ""))
        if selected:
            return selected
    return None


def _needs_tone_selection(
    requested_conversation_mode: str,
    response_style: str,
    tone_preset: str,
    conversation: List[Dict[str, Any]],
    message: str,
) -> bool:
    preset = str(tone_preset or "").strip().lower()
    mode = str(requested_conversation_mode or "").strip().lower()
    style = str(response_style or "").strip().lower()

    # Never interrupt ongoing conversations with a tone picker.
    for item in conversation or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("content") or "").strip():
            return False

    # If this message already carries an explicit tone choice, do not force prompt.
    if _extract_tone_preset_from_text(message):
        return False

    # Keep explicit request-only mode for clients that intentionally ask for picker UX.
    if preset == "ask":
        return True

    if preset in {"", "auto", "none", "unset"}:
        return False
    if mode in {"", "auto"} and style in {"", "auto", "balanced"}:
        return False
    return False


def _is_tone_selection_only_message(message: str) -> bool:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return False
    if not _extract_tone_preset_from_text(lowered):
        return False

    cleaned = lowered
    for token in [
        "자유대화", "자유 대화", "자유", "간결", "실행형", "지시형",
        "1번", "2번", "3번", "1", "2", "3", "번", "모드", "톤", "스타일",
        "으로", "로", "해줘", "해주세요", "선택", "할게", "할래", "하자",
    ]:
        cleaned = cleaned.replace(token, " ")
    cleaned = "".join(ch for ch in cleaned if ch not in "?!.,~")
    cleaned = _normalize_chat_message(cleaned)
    return len(cleaned) <= 2


def _looks_like_question(message: str) -> bool:
    normalized = _normalize_chat_message(message)
    lowered = normalized.lower()
    if not lowered:
        return False
    if "?" in normalized or "？" in normalized:
        return True
    if _is_meta_conversation_question(normalized):
        return True
    if lowered.startswith(("왜", "뭐", "무엇", "어떻게", "어디", "언제", "누가", "혹시", "그럼")):
        return True
    if _contains_any(
        lowered,
        [
            "궁금",
            "가능할까",
            "가능해",
            "될까",
            "되나",
            "되나요",
            "맞아",
            "맞나요",
            "알 수 있을까",
            "설명해줄 수",
            "비교해줄 수",
            "왜 그런지",
            "무슨 차이",
            "어떤 차이",
        ],
    ):
        return True
    return lowered.endswith(("인가", "인가요", "일까", "일까요", "될까", "될까요", "되나요", "맞나요", "있나요", "가능해", "가능한가"))


def _looks_like_directive(message: str) -> bool:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return False
    if lowered.startswith((
        "/run", "/pass", "/fix", "/fail", "/verify", "/search", "/news", "/ask", "/revise", "/resume",
        "/diagnose", "/improve", "/expand", "/analyze", "/test", "/script", "/task", "/실행", "/진단",
        "/개선", "/확장", "/분석", "/스크립트",
    )):
        return True
    if _contains_any(
        lowered,
        [
            # 기존
            "수정해줘",
            "구현해줘",
            "만들어줘",
            "바꿔줘",
            "고쳐줘",
            "다듬어줘",
            "정리해줘",
            "추가해줘",
            "삭제해줘",
            "적용해줘",
            "연결해줘",
            "연동해줘",
            "실행해줘",
            "검증해줘",
            "찾아줘",
            "분석해줘",
            "비교해줘",
            "설명해줘",
            "알려줘",
            "작성해줘",
            "해주세요",
            "부탁해",
            "부탁합니다",
            "진행해줘",
            # 자가 진단 / 개선 / 확장
            "자가진단",
            "자가 진단",
            "진단해줘",
            "자가개선",
            "자가 개선",
            "개선해줘",
            "자가확장",
            "자가 확장",
            "확장해줘",
            # 스크립트 / 생성 / 테스트 / 빌드
            "스크립트 만들어",
            "스크립트 생성",
            "스크립트 작성",
            "스크립트 추가",
            "생성해줘",
            "테스트해줘",
            "빌드해줘",
            "배포해줘",
            "설치해줘",
            "최적화해줘",
            "리팩터링",
            "리팩토링",
            "잡아줘",
            "잡아 줘",
            "설계해",
            "설계해줘",
            "설계해 줘",
            "설계부터",
            "구성해줘",
            "구성해 줘",
        ],
    ):
        return True
    return False


def _is_frustration_message(message: str) -> bool:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return False
    return _contains_any(
        lowered,
        [
            "장난", "장난하", "뭐하", "화나", "빡", "열받", "개판", "헛소리",
            "답답", "짜증", "미치", "안되", "안 돼", "말장난", "놀리",
        ],
    )


def infer_message_kind(message: str) -> str:
    normalized = _normalize_chat_message(message)
    if not normalized:
        return "general"
    if _is_banter_message(normalized):
        return "general"
    if _looks_like_question(normalized):
        return "question"
    if _looks_like_directive(normalized):
        return "directive"
    return "general"


def infer_emotion_signal(message: str) -> str:
    lowered = _normalize_chat_message(message).lower()
    if not lowered:
        return "neutral"

    urgent_tokens = ["급해", "빨리", "지금 당장", "긴급", "urgent", "asap"]
    frustration_tokens = [
        "답답", "짜증", "안 풀", "3시간", "망했", "미치겠", "frustrat", "stuck",
        "장난", "장난하", "뭐하", "화나", "빡", "열받", "개판", "헛소리",
    ]
    anxious_tokens = ["불안", "걱정", "무서", "막막", "panic", "anxious"]

    if any(token in lowered for token in urgent_tokens):
        return "urgent"
    if any(token in lowered for token in frustration_tokens):
        return "frustrated"
    if any(token in lowered for token in anxious_tokens):
        return "anxious"
    return "neutral"


def build_emotion_tone_guidance(emotion_signal: str) -> str:
    if emotion_signal == "urgent":
        return "사용자가 긴급함을 보입니다. 공감 1문장 후 즉시 실행 가능한 해결책부터 우선순위로 제시하세요."
    if emotion_signal == "frustrated":
        return "사용자가 답답함/피로를 보입니다. 방어적 설명 대신 공감하고 실패 원인 분해 + 즉시 시도 가능한 3단계 해결안을 제시하세요."
    if emotion_signal == "anxious":
        return "사용자가 불안 신호를 보입니다. 단정적 표현을 피하고 리스크/대응책을 차분히 제시하세요."
    return "사용자의 감정 신호가 중립입니다. 기본 협업 톤을 유지하세요."


def build_fast_admin_chat_reply(
    message: str,
    *,
    requested_conversation_mode: str,
    message_kind: str,
    conversation_stage: str,
) -> str:
    normalized = message.strip()
    lowered = normalized.lower()

    if not normalized:
        return "입력 내용을 한 줄로 다시 보내주세요. 바로 이어서 정리해드리겠습니다."

    if lowered in {"안녕", "안녕하세요", "hello", "hi", "hey"}:
        return "안녕하세요. 네, 자유 질문·잡담·구현 지시 모두 가능합니다. 편하게 이어서 말씀해 주세요."

    if _is_banter_message(normalized):
        return "그럴 수 있죠. 잠깐 숨 고르고, 편하게 이어서 이야기해 주세요. 그냥 잡담처럼 말해도 되고 바로 질문이나 작업 요청으로 넘어가도 됩니다."

    if _is_meta_conversation_question(normalized):
        return "네, 가능합니다. 자유 질문도 받고, 잡담형 대화도 이어갈 수 있고, 필요하면 구현 지시로도 바로 전환할 수 있습니다. 편하게 이어서 물어보세요."

    if requested_conversation_mode == "directive_fixed" and len(normalized) <= 40:
        return (
            "지시형 입력으로 받았습니다.\n"
            "- 수정 대상 파일\n"
            "- 원하는 결과\n"
            "- 금지하거나 유지할 조건\n"
            "이 세 가지만 덧붙이면 바로 실행형 답으로 좁혀드리겠습니다."
        )

    return ""


def _build_stock_trading_design_outline() -> str:
    return "\n".join([
        "## 기본 AI 주식 자동매매 설계 초안",
        "### 1. 목표",
        "- 실시간 시세 수집 → 특징량 생성 → AI 신호 → 리스크 게이트 → 주문(또는 모의체결) → 성과 기록",
        "### 2. 데이터 소스(기본값)",
        "- 1차: 공개 REST/WebSocket 시세 API(종목·분봉·체결)",
        "- 2차: PostgreSQL(시세 캐시·체결·포지션·전략 파라미터)",
        "- 3차: Redis(실시간 틱/신호 큐)",
        "### 3. 핵심 모듈",
        "- `market_data`: 수집·정규화·결측 보정",
        "- `features`: 이동평균·변동성·거래량 급증 등",
        "- `model_service`: 학습/추론(Scikit-learn 또는 PyTorch)",
        "- `strategy`: 단타 규칙(진입·손절·익절·쿨다운)",
        "- `risk`: 일손실 한도·종목당 비중·중복 주문 차단",
        "- `execution`: 모의/실거래 어댑터 분리",
        "- `reporting`: 체결·PnL·드로다운",
        "### 4. API(초안)",
        "- `GET /health`, `GET /quotes/{symbol}`, `POST /signals/predict`, `POST /orders`, `GET /positions`, `GET /reports/daily`",
        "### 5. 다음 결정(1개만 답해 주세요)",
        "- **A** 모의투자만 / **B** 실거래 연동 / **C** 백테스트 우선",
    ])


def build_admin_chat_fallback_reply(
    message: str,
    *,
    message_kind: str,
    conversation_stage: str,
    command_plan: List[Any],
) -> str:
    normalized = message.strip()
    reply_lines: List[str] = []

    if _is_frustration_message(normalized):
        return "\n".join([
            "불편 드려 죄송합니다. 확인 질문만 반복된 것처럼 느껴지셨다면 그 지적이 맞습니다.",
            "지금부터는 역질문 대신 설계 초안을 바로 드립니다.",
            _build_stock_trading_design_outline(),
        ])

    if message_kind == "directive" and conversation_stage == "architecture":
        return "\n".join([
            f"요청 이해했습니다. '{normalized}' 기준으로 설계 초안을 바로 정리합니다.",
            _build_stock_trading_design_outline(),
        ])

    if message_kind == "directive":
        reply_lines.extend([
            f"요청 이해했습니다. ({conversation_stage} 단계)",
            f"핵심은 '{normalized}' 입니다.",
            "원하면 바로 실행형으로 좁혀서 진행할게요. 수정 파일, 원하는 결과, 유지 조건만 알려주세요.",
        ])
        if command_plan:
            reply_lines.append("지금 기준 제안 순서는 다음과 같습니다.")
            reply_lines.extend([f"- {item.command_text}" for item in command_plan[:2]])
        return "\n".join(reply_lines)

    if message_kind == "question":
        reply_lines.extend([
            f"질문 이해했습니다. ({conversation_stage} 단계)",
            f"질문 요약: {normalized}",
            "바로 답변 가능합니다. 원하면 원인 중심/수정안 중심처럼 답변 스타일만 지정해 주세요.",
        ])
        return "\n".join(reply_lines)

    return "\n".join([
        "좋습니다. 계속 이어서 대화할 수 있습니다.",
        f"현재 단계는 {conversation_stage}이고, 입력은 '{normalized}'로 이해했습니다.",
        "원하면 바로 답변만 간단히 드리고, 필요할 때만 실행 계획을 붙이겠습니다.",
    ])


def _append_reciprocal_question(
    reply_content: str,
    *,
    message: str,
    lightweight: bool,
    requested_conversation_mode: str,
    response_style: str,
    message_kind: str,
    conversation_stage: str,
) -> str:
    text = str(reply_content or "").strip()
    if not text:
        return text
    if lightweight:
        return text
    if _is_frustration_message(message):
        return text
    if message_kind == "directive" and conversation_stage in {"architecture", "implementation"}:
        return text
    if requested_conversation_mode == "directive_fixed":
        return text
    if _is_freepace_conversation_mode(requested_conversation_mode) and not _should_force_reciprocal_question(
        requested_conversation_mode,
        response_style,
    ):
        return text
    if not _should_force_reciprocal_question(requested_conversation_mode, response_style):
        return text
    if "?" in text[-180:] or "？" in text[-180:]:
        return text

    follow_up = ""
    if _is_meta_conversation_question(message):
        follow_up = "지금부터 제가 먼저 한 가지씩 역질문하면서 진행할게요. 먼저, 이번 턴에서 가장 먼저 확정할 목표 1개는 무엇인가요?"
    elif message_kind == "directive":
        follow_up = "바로 실행 품질을 올리기 위해 확인할게요. 이번 지시에서 절대 바꾸면 안 되는 파일/동작 1가지는 무엇인가요?"
    elif conversation_stage == "research":
        follow_up = "비교 정확도를 높이기 위해 역질문 하나만 할게요. 이번에 비교할 후보를 2개로 좁히면 무엇과 무엇인가요?"
    elif conversation_stage == "implementation":
        follow_up = "구현으로 바로 연결하기 위해 확인할게요. 우선 수정 대상을 파일 기준으로 1~2개만 지정해줄 수 있나요?"
    elif conversation_stage == "operations":
        follow_up = "운영 진단 정확도를 위해 확인할게요. 지금 가장 먼저 봐야 할 실패 신호를 1개만 지정해줄 수 있나요?"
    else:
        follow_up = "대화를 끊지 않고 이어가기 위해 제가 역질문 하나 할게요. 지금 이 주제에서 먼저 해결하고 싶은 우선순위 1번은 무엇인가요?"

    return f"{text}\n\n{follow_up}".strip()


def _build_approval_gate_warning(project_memory: Dict[str, Any], message: str) -> str:
    approval_gate = project_memory.get("approval_gate") if isinstance(project_memory, dict) else None
    if not isinstance(approval_gate, dict):
        return ""
    blocked_paths = [str(item).strip() for item in (approval_gate.get("blocked_paths") or []) if str(item).strip()]
    matched = [path for path in blocked_paths if path and path in message]
    if not matched:
        return ""
    return (
        "승인 게이트 경고:\n"
        + "\n".join([f"- 금지 경로 감지: {path}" for path in matched])
        + "\n- 승인 범위와 금지 경로를 먼저 조정하거나 해당 파일을 제외한 작업문으로 다시 요청하세요."
    )


def is_lightweight_chat_request(
    request_model: OrchestratorChatRequest,
    request_context: Request,
) -> bool:
    return bool(request_model.lightweight) or request_context.url.path.endswith("/light")


def build_chat_history_context(
    conversation: List[Dict[str, Any]],
    *,
    history_limit: int,
    char_budget: int,
    re_module,
) -> str:
    if history_limit <= 0 or char_budget <= 0:
        return "assistant: 이전 대화 없음"

    history_lines: List[str] = []
    remaining = char_budget
    for item in reversed(conversation[-history_limit:]):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "assistant")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        compact_content = re_module.sub(r"\s+", " ", content)
        line = f"{role}: {compact_content[:remaining]}"
        if len(line) > remaining:
            line = line[:remaining]
        if not line:
            continue
        history_lines.append(line)
        remaining -= len(line) + 1
        if remaining <= 0:
            break

    if not history_lines:
        return "assistant: 이전 대화 없음"
    history_lines.reverse()
    return "\n".join(history_lines)


def build_chat_system_prompt(
    mode_label: str,
    conversation_stage: str,
    requested_conversation_mode: str,
    *,
    lightweight: bool,
    response_style: str,
    multi_turn_enabled: bool,
    context_tags: List[str],
    emotion_tone_guidance: str,
    web_grounding_enabled: bool,
) -> str:
    base_lines = [
        f"당신은 관리자 {mode_label} 오케스트레이터입니다.",
        "반드시 한국어로만 답변하세요.",
        "관리자 오케스트레이터는 정보 실험, 연구, 신기술 검토, 수동형/반자동 운영 보조 목적입니다.",
        "마켓플레이스 오케스트레이터처럼 자동 실행을 강제하지 말고, 연구·검토·지시 대화를 자율적으로 이어가세요.",
        "관리자 오케스트레이터는 동료 개발자처럼 자연스럽게 대화해야 합니다.",
        "질문이 모호하면 먼저 사용자의 의도를 한 문장으로 재진술하고, 필요한 확인 질문은 1개만 하세요.",
        "답변은 공감/확인 1문장 이하 + 핵심 답변 2~4문장 중심으로 구성하세요.",
        "의미 없는 수사, 반복 문장, 고정 문구(템플릿) 재사용을 피하고 맥락에 맞춰 표현을 바꾸세요.",
        "모르거나 확실하지 않은 부분은 솔직하게 말하세요. '이 부분은 제 학습 데이터 한계로 정확하지 않을 수 있습니다'라고 표현해서 신뢰성을 유지하세요.",
        "사용자가 인터넷/최신 기술/조사를 요청하면 문제를 함께 정의하고, 핵심 개념·적용 방식·주의점·다음 선택지를 설명하세요.",
        "사용자가 자가 확장이나 필요한 기능을 말하면 어떤 분석, 신기술, 접근법이 적합한지 제안하고 이유를 설명하세요.",
        "사용자가 실험을 요청하면 실험 목적, 가설, 확인 방법, 기대 결과를 짧게 정리한 뒤 결과를 설명하는 동료 개발자 말투를 유지하세요.",
        "사용자가 결과를 반영해 자가확장해달라고 하면 코드 자동생성기와 연결되는 실행 제안, 수정 포인트, 검증 순서를 함께 제시하세요.",
        "항상 질문에 직접 답하고, 필요하면 조사 요약 → 실험 포인트 → 실행 제안 순서로 이어가세요.",
        "답변 길이는 사용자 입력 길이에 맞추세요: 짧은 입력(1-2문장)→핵심만(1-2문장), 중간(3-5문장)→중간(3-5문장), 길게→상세 설명. '자세히' 요청 시만 1개 추가 단락 덧붙이세요.",
        "복잡한 주제는 이 구조로 답하세요: 핵심(1줄)→행동(1줄)→선택지(2-3개: 더 알고 싶으신 게?).",
        f"현재 대화 단계: {conversation_stage}",
        f"현재 대화 모드: {requested_conversation_mode}",
        f"응답 스타일: {response_style}",
        f"멀티 대화 유지: {'enabled' if multi_turn_enabled else 'disabled'}",
        f"감정 톤 가이드: {emotion_tone_guidance}",
        f"웹 검색 근거 사용: {'enabled' if web_grounding_enabled else 'disabled'}",
        "응답은 질문에 직접 답한 뒤, 필요하면 근거/선택지/다음 단계만 짧게 덧붙이세요.",
    ]
    if web_grounding_enabled:
        base_lines.extend([
            "웹 검색 근거가 제공되면 해당 근거를 우선 반영하고, 출처를 짧게 표시하세요.",
            "검색 근거가 부족하거나 상충하면 확실하지 않음을 명시하고 검증 경로를 안내하세요.",
        ])
    if context_tags:
        base_lines.append(f"현재 컨텍스트 태그: {', '.join(context_tags[:8])}")
    if lightweight:
        base_lines.extend([
            "경량 chat/light 경로입니다.",
            "불필요한 서론, 장황한 근거, 긴 실행 계획은 생략하세요.",
            "질문 요약 1줄, 핵심 답변, 필요 시 다음 단계 1개만 제시하세요.",
        ])
    else:
        base_lines.extend([
            "질문이 연구형이면 비교, 장단점, 리스크, 적용 가능성을 우선 정리하세요.",
            "질문이 지시형이면 구현 방향, 파일 단위 수정 포인트, 검증 순서를 우선 정리하세요.",
            "설명만 끝내지 말고 사용자가 바로 이어서 실험·검증·자가확장으로 넘어갈 수 있게 다음 선택지를 제안하세요.",
            "자동 패널 숨김 여부와 관계없이 대화 자체는 막지 말고 자유 질의에 계속 응답하세요.",
        ])
    if _should_force_reciprocal_question(requested_conversation_mode, response_style):
        base_lines.extend([
            "역질문 모드입니다. 답변 끝에는 반드시 사용자가 다음 결정을 쉽게 내릴 수 있는 확인 질문 1개를 붙이세요.",
            "질문은 구현 조건, 기술 후보 선택, 리스크 허용 범위, 실행 여부 중 현재 맥락에 가장 중요한 1개만 선택하세요.",
            "자유대화 톤은 유지하되, 실행은 사용자가 /run 또는 명시 버튼으로 승인하기 전까지 시작하지 마세요.",
        ])
    elif _is_freepace_conversation_mode(requested_conversation_mode):
        base_lines.extend([
            "자연 대화 모드입니다. 사람과 대화하듯 짧고 자연스럽게 답하세요.",
            "답변은 먼저 질문 의도에 바로 반응하고, 필요 시에만 후속 질문 1개를 덧붙이세요.",
            "역질문 모드가 명시되지 않은 자유대화에서는 불필요한 체크리스트와 고정 템플릿을 붙이지 마세요.",
            "사용자가 명시적으로 요청할 때만 단계화/형식화된 응답을 제공합니다.",
        ])
    return "\n".join(base_lines)


def build_chat_user_prompt(
    message: str,
    conversation_context: str,
    command_plan_lines: str,
    *,
    lightweight: bool,
    conversation_summary: str,
    message_kind: str,
    project_root: str,
    project_memory_summary: str,
    emotion_signal: str,
    web_grounding_block: str,
) -> str:
    prompt_lines = [
        f"[메시지 종류]\n{message_kind}",
        f"[대화 요약]\n{conversation_summary}",
        f"[작업 프로젝트 루트]\n{project_root or '-'}",
        f"[프로젝트 메모리]\n{project_memory_summary}",
        f"[감정 신호]\n{emotion_signal}",
        f"[현재 질문]\n{message}",
        f"[최근 대화]\n{conversation_context}",
    ]
    if web_grounding_block:
        prompt_lines.append(web_grounding_block)
    if not lightweight:
        prompt_lines.append(f"[Flow 계획 후보]\n{command_plan_lines}")
    return "\n".join(prompt_lines)


def summarize_project_memory(project_memory: Dict[str, Any]) -> str:
    if not isinstance(project_memory, dict) or not project_memory:
        return "프로젝트 메모리 없음"

    summary_lines: List[str] = []
    project_name = str(project_memory.get("project_name") or "").strip()
    if project_name:
        summary_lines.append(f"- 프로젝트명: {project_name}")

    remembered_goal = str(project_memory.get("remembered_goal") or "").strip()
    if remembered_goal:
        summary_lines.append(f"- 현재 목표: {remembered_goal}")

    constraints = [str(item).strip() for item in (project_memory.get("constraints") or []) if str(item).strip()]
    if constraints:
        summary_lines.append("- 제약 조건: " + " / ".join(constraints[:4]))

    decisions = [str(item).strip() for item in (project_memory.get("decisions") or []) if str(item).strip()]
    if decisions:
        summary_lines.append("- 기억한 결정: " + " / ".join(decisions[:4]))

    pending_tasks = [str(item).strip() for item in (project_memory.get("pending_tasks") or []) if str(item).strip()]
    if pending_tasks:
        summary_lines.append("- 남은 작업: " + " / ".join(pending_tasks[:4]))

    last_experiment = str(project_memory.get("last_experiment") or "").strip()
    if last_experiment:
        summary_lines.append(f"- 최근 실험: {last_experiment}")

    return "\n".join(summary_lines) if summary_lines else "프로젝트 메모리 없음"


def build_updated_project_memory(
    project_memory: Dict[str, Any],
    *,
    project_root: str,
    message: str,
    reply_content: str,
    conversation_stage: str,
    message_kind: str,
) -> Dict[str, Any]:
    next_memory = dict(project_memory or {})
    if project_root:
        next_memory["project_root"] = project_root
    next_memory["last_user_instruction"] = message.strip()
    next_memory["last_assistant_summary"] = reply_content[:600]
    next_memory["last_conversation_stage"] = conversation_stage
    next_memory["last_message_kind"] = message_kind

    lowered = message.lower()
    if any(token in lowered for token in ("목표", "완성", "구현", "확장", "개선")):
        next_memory["remembered_goal"] = message.strip()
    if any(token in lowered for token in ("하지마", "제외", "금지", "유지")):
        existing_constraints = [str(item).strip() for item in (next_memory.get("constraints") or []) if str(item).strip()]
        if message.strip() not in existing_constraints:
            existing_constraints.append(message.strip())
        next_memory["constraints"] = existing_constraints[-6:]
    if any(token in lowered for token in ("실험", "검증", "테스트")):
        next_memory["last_experiment"] = message.strip()
    if any(token in lowered for token in ("다음", "남은", "TODO", "todo", "작업")):
        existing_pending = [str(item).strip() for item in (next_memory.get("pending_tasks") or []) if str(item).strip()]
        if message.strip() not in existing_pending:
            existing_pending.append(message.strip())
        next_memory["pending_tasks"] = existing_pending[-8:]

    return next_memory


def infer_conversation_goal(
    message: str,
    *,
    conversation_stage: str,
    message_kind: str,
    project_memory: Dict[str, Any],
) -> str:
    remembered_goal = str(project_memory.get("remembered_goal") or "").strip()
    if remembered_goal and len(message.strip()) < 80:
        return remembered_goal
    if message_kind == "directive":
        return f"{conversation_stage} 단계 구현/수정 목표: {message.strip()}"
    if message_kind == "question":
        return f"{conversation_stage} 단계 탐색/비교 목표: {message.strip()}"
    return f"{conversation_stage} 단계 대화 목표: {message.strip()}"


def build_proposal_items(
    message: str,
    *,
    conversation_stage: str,
    message_kind: str,
) -> List[ProposalItem]:
    lowered = message.lower()
    proposals: List[ProposalItem] = []
    if conversation_stage in {"architecture", "implementation", "operations"}:
        proposals.append(
            ProposalItem(
                title="증거 우선 제안",
                category="risk",
                detail="수정 전에 hard gate, capability evidence, 운영 실검증 결과를 먼저 함께 확인하는 흐름을 권장합니다.",
                benefit="오진과 중복 수정을 줄입니다.",
                tradeoff="초기 분석 단계가 조금 늘어납니다.",
            )
        )
    if any(token in lowered for token in ("수정", "개선", "복구", "고쳐", "patch", "리팩터")):
        proposals.append(
            ProposalItem(
                title="정밀 타겟 수정 제안",
                category="targeted-change",
                detail="파일 전체 재생성보다 파일/섹션/기능/조각 ID 기준으로 수정 범위를 먼저 좁히는 방식을 권장합니다.",
                benefit="실패 범위 격리와 selective apply 에 유리합니다.",
                tradeoff="ID registry 설계가 먼저 필요합니다.",
            )
        )
    if message_kind == "question" or conversation_stage == "research":
        proposals.append(
            ProposalItem(
                title="대안 비교 제안",
                category="alternative",
                detail="단일 정답보다 구조 대안, 운영 리스크, 확장 비용을 같이 비교해 의사결정하는 흐름을 권장합니다.",
                benefit="사용자 의도와 장기 운영성을 함께 맞출 수 있습니다.",
                tradeoff="답변이 약간 길어질 수 있습니다.",
            )
        )
    if not proposals:
        proposals.append(
            ProposalItem(
                title="다음 단계 제안",
                category="next-step",
                detail="현재 대화를 바로 실행형 작업문, 연구형 비교, 또는 검증 계획으로 전환할 수 있도록 최소 1개의 다음 단계를 항상 제시합니다.",
                benefit="짧은 대화에서도 사용자가 바로 이어서 행동할 수 있습니다.",
                tradeoff="제안이 보수적으로 보일 수 있습니다.",
            )
        )
    return proposals[:4]


def build_new_technology_candidates(message: str, conversation_stage: str) -> List[str]:
    lowered = message.lower()
    candidates: List[str] = []
    if any(token in lowered for token in ("대화", "맥락", "챗봇", "orchestrator", "오케스트레이터")):
        candidates.extend([
            "intent memory scorer",
            "conversation goal summarizer",
            "proposal ranking engine",
        ])
    if any(token in lowered for token in ("수정", "patch", "리팩터", "복구", "검증")):
        candidates.extend([
            "chunk-id patch registry",
            "selective apply engine",
            "evidence replay validator",
        ])
    if conversation_stage == "operations":
        candidates.extend([
            "operation evidence replay",
            "websocket handshake monitor",
        ])
    return list(dict.fromkeys(candidates))[:5]


def build_technology_recommendations(
    message: str,
    reply_content: str,
    *,
    web_results: List[WebGroundingItem],
    fallback_candidates: List[str],
) -> List[TechnologyRecommendation]:
    signal = f"{message}\n{reply_content}".lower()
    source_candidates: List[tuple[str, str]] = []
    for item in web_results[:3]:
        title = str(item.title or "").strip()
        if title:
            source_candidates.append((title[:80], "web"))
    for candidate in fallback_candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            source_candidates.append((normalized, "llm-reply"))
    if not source_candidates and any(token in signal for token in ("대화", "역질문", "오케스트레이터", "세션", "맥락")):
        source_candidates.extend([
            ("dialogue state memory", "llm-reply"),
            ("structured proposal renderer", "llm-reply"),
            ("reciprocal-question policy router", "llm-reply"),
        ])

    recommendations: List[TechnologyRecommendation] = []
    for title, source in source_candidates:
        lowered_title = title.lower()
        if any(token in lowered_title for token in ("memory", "session", "state", "맥락")):
            risk = "중간: 개인정보/장기 메모리 보존 정책과 삭제 UX가 필요합니다."
            difficulty = "중간: session_id 저장소, 요약기, 충돌 병합이 필요합니다."
            cost = "낮음~중간: 텍스트 요약 저장 중심이면 인프라 비용은 작고 LLM 요약 호출 비용이 추가됩니다."
            alternative = "브라우저 localStorage-only 대화 복원"
        elif any(token in lowered_title for token in ("proposal", "structured", "renderer", "card", "제안")):
            risk = "낮음: 응답 스키마와 UI 렌더링 불일치만 관리하면 됩니다."
            difficulty = "낮음~중간: 기존 proposal/next_action 필드를 확장 렌더링하면 됩니다."
            cost = "낮음: 추가 API 없이 기존 chat 응답에 포함 가능합니다."
            alternative = "일반 텍스트 답변에 제안 섹션만 포함"
        elif any(token in lowered_title for token in ("question", "reciprocal", "reverse", "역질문")):
            risk = "낮음: 과도한 질문으로 UX가 느려질 수 있어 선택 모드에서만 강제해야 합니다."
            difficulty = "낮음: conversation_mode와 prompt 정책 연결이 핵심입니다."
            cost = "낮음: 별도 인프라 없이 프롬프트/후처리 정책으로 구현 가능합니다."
            alternative = "사용자가 직접 '역질문해줘'라고 요청할 때만 질문"
        else:
            risk = "중간: 최신성, 라이선스, 운영 안정성을 별도 검증해야 합니다."
            difficulty = "중간: 현재 코드 경계와 데이터 계약에 맞춘 어댑터가 필요합니다."
            cost = "중간: 검색/검증 호출과 운영 모니터링 비용이 추가될 수 있습니다."
            alternative = "검증된 내부 패턴을 먼저 적용하고 최신 후보는 실험 플래그로 격리"
        recommendations.append(
            TechnologyRecommendation(
                title=title,
                source=source,
                adoption_risk=risk,
                implementation_difficulty=difficulty,
                operating_cost=cost,
                alternative=alternative,
                rationale="현재 대화와 LLM/검색 응답에서 반복적으로 나타난 신호를 기반으로 추천했습니다.",
            )
        )
    deduped: List[TechnologyRecommendation] = []
    seen: set[str] = set()
    for item in recommendations:
        key = item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:5]


def build_target_patch_hints(message: str, conversation_stage: str) -> List[TargetPatchHint]:
    lowered = message.lower()
    hints: List[TargetPatchHint] = []
    if any(token in lowered for token in ("대화", "챗", "오케스트레이터", "맥락")):
        hints.append(
            TargetPatchHint(
                file_id="FILE-ADMIN-CHAT-SERVICE",
                section_id="SECTION-CONVERSATION-INTELLIGENCE",
                feature_id="FEATURE-CONTEXT-AWARE-REPLY",
                chunk_id="CHUNK-CONVERSATION-AI-001",
                reason="대화 맥락 인지와 제안형 응답 로직이 집중된 영역입니다.",
            )
        )
    if any(token in lowered for token in ("수정", "검증", "hard gate", "증거", "운영")):
        hints.append(
            TargetPatchHint(
                file_id="FILE-ADMIN-LLM-PAGE",
                section_id="SECTION-CHAT-ADVISORY-PANEL",
                feature_id="FEATURE-EVIDENCE-FIRST-UX",
                chunk_id="CHUNK-ADMIN-CHAT-UI-001",
                reason="관리자 화면에서 제안형 응답과 evidence 패널을 직접 연결하는 영역입니다.",
            )
        )
    return hints[:4]


def build_clarification_questions(
    message: str,
    *,
    conversation_stage: str,
    message_kind: str,
    advisory_controls: Dict[str, Any],
) -> List[AdvisoryQuestion]:
    if not advisory_controls.get("clarification_questions_enabled", True):
        return []
    questions: List[AdvisoryQuestion] = []
    if message_kind == "question":
        questions.append(
            AdvisoryQuestion(
                prompt="더 좁은 비교 대상이나 원하는 출력 형식이 있습니까?",
                reason="질문 범위를 줄여 더 직접적인 답을 만들기 위한 확인 질문",
            )
        )
    if conversation_stage in {"architecture", "operations"} and advisory_controls.get("systems_thinking_enabled", True):
        questions.append(
            AdvisoryQuestion(
                prompt="구조 대안 비교가 필요합니까, 아니면 바로 실행안만 원합니까?",
                reason="시스템 관점 비교와 실행형 답변 사이의 우선순위를 확인",
            )
        )
    limit = max(0, int(advisory_controls.get("max_clarification_questions", 3) or 0))
    return questions[:limit]


def build_evidence_highlights(
    *,
    conversation_stage: str,
    advisory_controls: Dict[str, Any],
) -> List[AdvisoryEvidenceItem]:
    if not advisory_controls.get("evidence_panel_enabled", True):
        return []
    items: List[AdvisoryEvidenceItem] = [
        AdvisoryEvidenceItem(
            title="관리자 연구형 대화 유지",
            source_label="admin/llm",
            source_type="runtime-policy",
            trust_score=0.9,
            why_it_matters="관리자 대시보드는 자유 질의와 연구 목적 대화를 우선해야 합니다.",
        )
    ]
    if advisory_controls.get("scientific_reasoning_enabled", True):
        items.append(
            AdvisoryEvidenceItem(
                title="과학적 추론 활성화",
                source_label="orchestrator_runtime_config",
                source_type="runtime-config",
                trust_score=0.86,
                why_it_matters="가설, 근거, 반례를 구분해 더 정교한 대화형 해석을 지원합니다.",
            )
        )
    if conversation_stage == "operations":
        items.append(
            AdvisoryEvidenceItem(
                title="운영 증거 우선 흐름",
                source_label="capability-evidence",
                source_type="ops-policy",
                trust_score=0.88,
                why_it_matters="운영 단계에서는 websocket, admin, marketplace 검증 결과를 직접 근거로 삼아야 합니다.",
            )
        )
    limit = max(0, int(advisory_controls.get("max_evidence_items", 5) or 0))
    return items[:limit]


def build_next_action_suggestions(
    *,
    message: str,
    web_results: List[WebGroundingItem],
    message_kind: str,
    requested_conversation_mode: str,
    suggested_mode: str,
    advisory_controls: Dict[str, Any],
) -> List[AdvisoryNextAction]:
    if not advisory_controls.get("next_action_suggestions_enabled", True):
        return []
    if message_kind == "directive" or requested_conversation_mode == "directive_fixed":
        actions = [
            AdvisoryNextAction(
                title="이 지시로 바로 실행",
                action_type="run_orchestrator",
                detail="현재 지시형 질문과 최근 대화 요약을 실행 요청으로 연결합니다.",
                recommended_mode="project",
            ),
            AdvisoryNextAction(
                title="작업 지시 초안으로 반영",
                action_type="apply_task",
                detail="현재 대화 내용을 작업 지시 textarea 초안으로 반영합니다.",
                recommended_mode="project",
            ),
            AdvisoryNextAction(
                title="결과 반영 자가확장으로 전환",
                action_type="apply_task",
                detail="현재 답변과 실험 요약을 코드 자동생성기 실행용 자가확장 작업문으로 정리합니다.",
                recommended_mode="project",
            ),
        ]
    else:
        actions = [
            AdvisoryNextAction(
                title="질문 세분화",
                action_type="follow-up",
                detail="원하는 결과 형식을 덧붙이면 연구형 응답을 더 구체화할 수 있습니다.",
                recommended_mode=suggested_mode,
            ),
            AdvisoryNextAction(
                title="실험 계획으로 전환",
                action_type="follow-up",
                detail="핵심 가설과 확인 지표를 붙이면 바로 실험·검증 대화로 이어갑니다.",
                recommended_mode="research",
            ),
        ]

    if web_results:
        grounding_lines: List[str] = []
        for index, item in enumerate(web_results[:3], start=1):
            title = str(item.title or "").strip() or f"검색 근거 {index}"
            snippet = str(item.snippet or "").strip()
            if not snippet:
                continue
            url_suffix = f" ({item.url})" if item.url else ""
            grounding_lines.append(f"{index}. {title}{url_suffix}\n- {snippet}")
        if grounding_lines:
            action_prompt = (
                f"요청: {_normalize_chat_message(message)}\n\n"
                "아래 웹 검색 근거를 반영해 운영형 문서 초안을 생성하세요.\n"
                "산출물에는 핵심 주장, 근거 URL, 바로 실행 가능한 체크리스트를 포함하세요.\n\n"
                "[웹 근거]\n"
                + "\n".join(grounding_lines)
            )[:2800]
            actions.insert(
                0,
                AdvisoryNextAction(
                    title="검색 근거로 feature-orchestrate 실행",
                    action_type="feature_orchestrate",
                    detail="웹 검색 결과를 payload에 반영해 AI 문서 엔진을 바로 실행합니다.",
                    recommended_mode="project",
                    action_payload={
                        "feature_id": "ai-document",
                        "project_name": f"web-grounded-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        "prompt": action_prompt,
                        "final_enabled": True,
                        "context_tags": ["web-grounded", "admin-chat", "feature-orchestrate"],
                    },
                ),
            )
    limit = max(0, int(advisory_controls.get("max_next_actions", 3) or 0))
    return actions[:limit]


async def answer_orchestrator_chat(
    *,
    request_context: Request,
    request: OrchestratorChatRequest,
    agent_key: str,
    resolve_chat_model,
    build_ollama_options,
    ollama_base: str,
    orch_chat_request_max_tokens: int,
    orch_lightweight_chat_max_tokens: int,
    orch_chat_agent_timeout_sec: float,
    orch_reasoner_brief_timeout_sec: float,
    logger,
    re_module,
    session_factory,
    current_user=None,
) -> OrchestratorChatResponse:
    auto_connect = request.auto_connect or AutoConnectMeta(
        connection_id=request.run_id or uuid4().hex,
        flow_id="FLOW-ADM-CHAT",
        step_id="FLOW-ADM-CHAT-1",
        action="CHAT",
        route_id="ROUTE-GENERAL",
        panel_id="PANEL-ADMIN-LLM",
    )
    message = str(request.message or "").strip() or "요청 내용을 다시 입력하세요."
    message_lower = message.lower()
    lightweight = is_lightweight_chat_request(request, request_context)
    session_owner_id = _chat_session_owner_id(current_user)
    session_id, session_snapshot = _load_session_state(request, auto_connect, session_owner_id=session_owner_id)
    requested_conversation_mode = str(request.conversation_mode or "auto").strip().lower() or "auto"
    response_style = str(request.response_style or "balanced").strip().lower() or "balanced"
    tone_preset = str(request.tone_preset or "auto").strip().lower() or "auto"
    reverse_question_mode = str(
        request.reverse_question_mode
        or (request.project_memory or {}).get("reverse_question_mode")
        or "",
    ).strip().lower()
    if (
        reverse_question_mode
        and requested_conversation_mode in {"reverse_question", "reciprocal", "interview"}
        and response_style in {"", "auto", "balanced"}
    ):
        response_style = f"reverse_question:{reverse_question_mode}"
    selected_tone_from_message = _extract_tone_preset_from_text(message)
    selected_tone_from_history = _infer_tone_preset_from_history(request.conversation)
    if _needs_tone_selection(
        requested_conversation_mode,
        response_style,
        tone_preset,
        request.conversation,
        message,
    ):
        selected_tone = selected_tone_from_message or selected_tone_from_history
        if selected_tone:
            tone_preset = selected_tone
        else:
            reply_content = (
                "좋아요. 먼저 대화 스타일을 맞춘 뒤 진행할게요.\n"
                "- 1번 자유대화: 자연스럽게 대화형\n"
                "- 2번 간결: 핵심만 짧게\n"
                "- 3번 실행형: 바로 실행 단계 중심\n"
                "원하는 번호나 이름(자유대화/간결/실행형)으로 답해 주세요."
            )
            reply = ConversationMessage(
                role="assistant",
                speaker=agent_key,
                content=reply_content,
                step_id=auto_connect.step_id or "FLOW-ADM-CHAT-1",
                step_title="대화 스타일 확인",
                timestamp=datetime.now().isoformat(),
                connection_id=auto_connect.connection_id,
                flow_id=auto_connect.flow_id,
                action=auto_connect.action,
                route_id=auto_connect.route_id,
                panel_id=auto_connect.panel_id,
            )
            history = [
                ConversationMessage(**item)
                for item in (request.conversation or [])
                if isinstance(item, dict)
            ]
            history.append(reply)
            return OrchestratorChatResponse(
                reply=reply,
                conversation=history,
                output_dir=request.output_dir,
                run_id=request.run_id or uuid4().hex,
                session_id=session_id or None,
                grounding_mode="internal",
                grounding_note="대화 스타일 선택 유도",
                companion_mode=request.companion_mode,
                web_results=[],
                suggested_companion_mode=request.companion_mode or "hybrid",
                suggested_companion_reason="스타일 확정 후 답변 품질을 더 안정적으로 맞추기 위해 먼저 선택을 요청했습니다.",
                conversation_stage="tone-selection",
                clarification_questions=[
                    AdvisoryQuestion(
                        prompt="1번 자유대화 / 2번 간결 / 3번 실행형 중 어떤 스타일로 진행할까요?",
                        reason="스타일에 따라 답변 길이와 진행 방식이 달라집니다.",
                    )
                ],
                evidence_highlights=[],
                next_action_suggestions=[
                    AdvisoryNextAction(
                        title="자유대화로 시작",
                        action_type="follow-up",
                        detail="'1번' 또는 '자유대화'라고 답하면 자연 대화형으로 시작합니다.",
                        recommended_mode="hybrid",
                    ),
                    AdvisoryNextAction(
                        title="간결 모드로 시작",
                        action_type="follow-up",
                        detail="'2번' 또는 '간결'이라고 답하면 핵심만 짧게 답합니다.",
                        recommended_mode="research",
                    ),
                    AdvisoryNextAction(
                        title="실행형 모드로 시작",
                        action_type="follow-up",
                        detail="'3번' 또는 '실행형'이라고 답하면 단계 중심으로 바로 진행합니다.",
                        recommended_mode="project",
                    ),
                ],
                flow_trace=[],
                command_plan=[],
                active_trace=None,
                message_kind="general",
                multi_turn_enabled=bool(request.multi_turn_enabled),
                conversation_summary="스타일 선택 대기",
                inferred_goal="대화 스타일 확정",
                proposal_items=[],
                new_technology_candidates=[],
                target_patch_hints=[],
                project_root=str(request.project_root or request.output_dir or "").strip() or None,
                project_memory=dict(request.project_memory or {}),
                auto_connect=auto_connect,
                diagnostics={
                    "path": "tone-clarification",
                    "tone_preset": "pending",
                    "requested_conversation_mode": requested_conversation_mode,
                    "response_style": response_style,
                },
            )
    resolved_tone_preset, requested_conversation_mode, response_style = _resolve_tone_preset(
        requested_conversation_mode,
        response_style,
        tone_preset,
    )
    if selected_tone_from_message and _is_tone_selection_only_message(message):
        reply_content = {
            "free_talk": "좋습니다. 자유대화로 맞췄어요. 이제 바로 질문이나 요청을 편하게 이어주세요.",
            "concise": "좋습니다. 간결 모드로 맞췄어요. 이제 핵심 요청을 보내주시면 짧고 명확하게 답할게요.",
            "execution": "좋습니다. 실행형 모드로 맞췄어요. 이제 목표를 보내주시면 단계 중심으로 바로 진행할게요.",
        }.get(resolved_tone_preset, "좋습니다. 스타일을 적용했습니다. 이제 원하는 요청을 이어서 보내주세요.")
        reply = ConversationMessage(
            role="assistant",
            speaker=agent_key,
            content=reply_content,
            step_id=auto_connect.step_id or "FLOW-ADM-CHAT-1",
            step_title="대화 스타일 적용",
            timestamp=datetime.now().isoformat(),
            connection_id=auto_connect.connection_id,
            flow_id=auto_connect.flow_id,
            action=auto_connect.action,
            route_id=auto_connect.route_id,
            panel_id=auto_connect.panel_id,
        )
        history = [
            ConversationMessage(**item)
            for item in (request.conversation or [])
            if isinstance(item, dict)
        ]
        history.append(reply)
        return OrchestratorChatResponse(
            reply=reply,
            conversation=history,
            output_dir=request.output_dir,
            run_id=request.run_id or uuid4().hex,
            session_id=session_id or None,
            grounding_mode="internal",
            grounding_note="대화 스타일 적용 확인",
            companion_mode=request.companion_mode,
            web_results=[],
            suggested_companion_mode=request.companion_mode or "hybrid",
            suggested_companion_reason="사용자가 직접 스타일을 선택했습니다.",
            conversation_stage="tone-confirmed",
            clarification_questions=[],
            evidence_highlights=[],
            next_action_suggestions=[
                AdvisoryNextAction(
                    title="바로 요청 이어가기",
                    action_type="follow-up",
                    detail="원하는 목표, 대상 파일, 제약 조건을 한 줄로 보내면 바로 처리합니다.",
                    recommended_mode="project",
                )
            ],
            flow_trace=[],
            command_plan=[],
            active_trace=None,
            message_kind="general",
            multi_turn_enabled=bool(request.multi_turn_enabled),
            conversation_summary="스타일 확정 완료",
            inferred_goal="스타일 적용 완료",
            proposal_items=[],
            new_technology_candidates=[],
            target_patch_hints=[],
            project_root=str(request.project_root or request.output_dir or "").strip() or None,
            project_memory=dict(request.project_memory or {}),
            auto_connect=auto_connect,
            diagnostics={
                "path": "tone-confirmed",
                "tone_preset": resolved_tone_preset,
                "requested_conversation_mode": requested_conversation_mode,
                "response_style": response_style,
            },
        )
    multi_turn_enabled = bool(request.multi_turn_enabled)
    context_tags = [str(item).strip() for item in (request.context_tags or []) if str(item).strip()]
    conversation_stage = "general"
    suggested_mode = request.companion_mode or "research"
    grounding_note = "관리자 연구형 자유 대화 응답"
    suggested_reason = "현재 대화는 내부 컨텍스트 기준으로 응답했습니다."
    message_kind = str(request.message_kind or "").strip().lower()
    meta_conversation_question = _is_meta_conversation_question(message)

    if not message_kind:
        message_kind = infer_message_kind(message)

    if requested_conversation_mode == "directive_fixed":
        conversation_stage = "implementation"
        suggested_mode = "project"
        grounding_note = "관리자 지시형 고정 응답"
        suggested_reason = "사용자가 지시형 고정을 선택해 구현/실행 중심으로 응답합니다."
    elif requested_conversation_mode == "research_fixed":
        conversation_stage = "research"
        suggested_mode = "research"
        grounding_note = "관리자 연구형 고정 응답"
        suggested_reason = "사용자가 연구형 고정을 선택해 조사/비교 중심으로 응답합니다."
    else:
        if _is_banter_message(message) or meta_conversation_question:
            conversation_stage = "general"
        elif any(token in message_lower for token in ("자가진단", "자가 진단", "진단해줘", "진단해 줘", "diagnose", "self-diagnose")):
            conversation_stage = "diagnostics"
            suggested_mode = "project"
            grounding_note = "자가 진단 명령 — 코드베이스 전체 진단 실행"
            suggested_reason = "자가 진단 명령이 감지되어 진단 실행 흐름을 안내합니다."
        elif any(token in message_lower for token in ("자가개선", "자가 개선", "개선해줘", "개선해 줘", "self-improve")):
            conversation_stage = "implementation"
            suggested_mode = "project"
            grounding_note = "자가 개선 명령 — 코드 품질 개선 실행"
            suggested_reason = "자가 개선 명령이 감지되어 코드 품질 개선 흐름을 안내합니다."
        elif any(token in message_lower for token in ("자가확장", "자가 확장", "확장해줘", "확장해 줘", "self-expand")):
            conversation_stage = "implementation"
            suggested_mode = "project"
            grounding_note = "자가 확장 명령 — 기능 확장 실행"
            suggested_reason = "자가 확장 명령이 감지되어 기능 확장 실행 흐름을 안내합니다."
        elif any(token in message_lower for token in ("스크립트 만들어", "스크립트 생성", "스크립트 작성", "generate script", "create script")):
            conversation_stage = "implementation"
            suggested_mode = "project"
            grounding_note = "스크립트 생성 명령 — 스크립트 파일 작성"
            suggested_reason = "스크립트 생성 명령이 감지되어 코드 작성 흐름을 안내합니다."
        elif any(token in message_lower for token in ("최신", "news", "release", "trend", "신기술", "비교", "research", "조사")):
            conversation_stage = "research"
        elif any(token in message_lower for token in ("아키텍처", "구조", "설계", "architecture", "system design")):
            conversation_stage = "architecture"
        elif any(token in message_lower for token in ("배포", "deploy", "운영", "monitor", "장애", "로그")):
            conversation_stage = "operations"
        elif message_kind == "directive" and any(token in message_lower for token in ("구현", "코드", "api", "python", "react", "fastapi", "next.js", "nextjs", "파일", ".py", ".ts", ".tsx", ".js", ".jsx")):
            conversation_stage = "implementation"
        elif message_kind == "question" and not meta_conversation_question and any(token in message_lower for token in ("구현", "코드", "api", "python", "react", "fastapi", "next.js", "nextjs")):
            conversation_stage = "implementation"

        if any(token in message_lower for token in ("최신", "today", "뉴스", "release", "문서", "docs", "공식", "온라인", "web")):
            suggested_mode = "research"
            suggested_reason = "실시간 정보나 최신 기술 질문이므로 research companion 흐름이 적합합니다."
            grounding_note = "실시간/온라인 탐색형 질문으로 research companion 권장"

    mode_label = (
        "지시형"
        if requested_conversation_mode == "directive_fixed"
        else "연구형"
        if requested_conversation_mode == "research_fixed"
        else "멀티"
    )
    command_plan = [] if lightweight else build_multi_command_plan(message)
    flow_trace = build_lightweight_flow_trace(auto_connect) if lightweight else build_admin_flow_trace()
    active_trace = flow_trace[0] if flow_trace else None
    if not lightweight and multi_turn_enabled and len(flow_trace) >= 8:
        active_trace = flow_trace[7] if message_kind == "directive" else flow_trace[6]
    command_plan_lines = "\n".join(
        [f"- {item.trace_id}: {item.command_text}" for item in command_plan]
    ) if command_plan else "- 현재는 자유 질의 단계이며 필요 시 Flow 계획을 이어서 제안하세요."
    requested_max_tokens = min(
        request.max_tokens,
        orch_lightweight_chat_max_tokens if lightweight else orch_chat_request_max_tokens,
    )
    requested_timeout_sec = float(
        orch_reasoner_brief_timeout_sec if lightweight else orch_chat_agent_timeout_sec
    )
    conversation_context = build_chat_history_context(
        request.conversation,
        history_limit=2 if lightweight else 6,
        char_budget=320 if lightweight else 1600,
        re_module=re_module,
    )
    last_messages = [
        str(item.get("content") or "").strip()
        for item in (request.conversation or [])[-3:]
        if isinstance(item, dict) and str(item.get("content") or "").strip()
    ]
    conversation_summary = " / ".join(last_messages)[:240] if last_messages else "이전 대화 없음"
    project_root = str(request.project_root or request.output_dir or "").strip()
    project_memory = dict(request.project_memory or {})
    persisted_context: Dict[str, Any] | None = None
    if project_root and session_factory is not None:
        db: Session = session_factory()
        try:
            persisted_context = get_project_context_bundle(db, project_root)
        finally:
            db.close()
        persisted_memory = dict((persisted_context or {}).get("memory") or {})
        persisted_memory.update(project_memory)
        project_memory = persisted_memory
        approval_gate = (persisted_context or {}).get("approval_gate") if isinstance(persisted_context, dict) else None
        priority_tasks = (persisted_context or {}).get("priority_tasks") if isinstance(persisted_context, dict) else None
        if approval_gate:
            project_memory["approval_gate"] = approval_gate
        if priority_tasks:
            project_memory["priority_tasks"] = priority_tasks
    project_memory_summary = summarize_project_memory(project_memory)
    emotion_signal = infer_emotion_signal(message)
    emotion_tone_guidance = build_emotion_tone_guidance(emotion_signal)
    web_results: List[WebGroundingItem] = []
    web_grounding_block = ""
    if should_use_web_search(message, message_kind):
        web_results = fetch_web_grounding(
            message,
            max_items=5,
            timeout_sec=8.0,
            logger=logger,
        )
        web_grounding_block = build_web_grounding_block(web_results)
    if web_results:
        grounding_note = "웹 검색 근거를 포함한 관리자 대화 응답"
        suggested_reason = "최신성 신호가 감지되어 웹 검색 근거를 반영했습니다."
    inferred_goal = infer_conversation_goal(
        message,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
        project_memory=project_memory,
    )
    proposal_items = build_proposal_items(
        message,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
    )
    new_technology_candidates = build_new_technology_candidates(message, conversation_stage)
    target_patch_hints = build_target_patch_hints(message, conversation_stage)
    from backend.llm.model_config import get_advisory_controls
    advisory_controls = get_advisory_controls()
    clarification_questions = build_clarification_questions(
        message,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
        advisory_controls=advisory_controls,
    )
    if _should_force_reciprocal_question(requested_conversation_mode, response_style) and not clarification_questions:
        clarification_questions = [
            AdvisoryQuestion(
                prompt="지금 이 주제에서 먼저 확정할 우선순위 1번은 무엇인가요?",
                reason="역질문 모드에서는 대화가 실행으로 튀지 않도록 다음 결정을 명시적으로 확인합니다.",
            )
        ]
    evidence_highlights = build_evidence_highlights(
        conversation_stage=conversation_stage,
        advisory_controls=advisory_controls,
    )
    next_action_suggestions = build_next_action_suggestions(
        message=message,
        web_results=web_results,
        message_kind=message_kind,
        requested_conversation_mode=requested_conversation_mode,
        suggested_mode=suggested_mode,
        advisory_controls=advisory_controls,
    )
    if lightweight:
        proposal_items = proposal_items[:2]
        new_technology_candidates = new_technology_candidates[:3]
        target_patch_hints = target_patch_hints[:2]
        clarification_questions = clarification_questions[:2]
        evidence_highlights = evidence_highlights[:2]
        next_action_suggestions = next_action_suggestions[:2]
    approval_gate_warning = _build_approval_gate_warning(project_memory, message)
    diagnostics: Dict[str, Any] = {
        "path": "fast-reply",
        "message_length": len(message),
        "message_kind": message_kind,
        "conversation_stage": conversation_stage,
        "lightweight": lightweight,
        "requested_conversation_mode": requested_conversation_mode,
        "tone_preset": resolved_tone_preset,
        "model": None,
        "timeout_sec": None,
        "llm_elapsed_ms": 0,
        "used_fallback": False,
        "project_root": project_root,
        "emotion_signal": emotion_signal,
        "web_grounding_used": bool(web_results),
        "web_grounding_count": len(web_results),
        "session_id": session_id or None,
        "session_loaded": bool(session_snapshot),
        "reverse_question_mode": reverse_question_mode or None,
    }
    fast_reply_content = build_fast_admin_chat_reply(
        message,
        requested_conversation_mode=requested_conversation_mode,
        message_kind=message_kind,
        conversation_stage=conversation_stage,
    )
    if fast_reply_content:
        fast_reply_content = _append_reciprocal_question(
            fast_reply_content,
            message=message,
            lightweight=lightweight,
            requested_conversation_mode=requested_conversation_mode,
            response_style=response_style,
            message_kind=message_kind,
            conversation_stage=conversation_stage,
        )
        reply = ConversationMessage(
            role="assistant",
            speaker=agent_key,
            content=fast_reply_content,
            step_id=auto_connect.step_id or (active_trace.step_id if active_trace else "FLOW-ADM-CHAT-1"),
            step_title=active_trace.title if active_trace else "관리자 빠른 응답",
            timestamp=datetime.now().isoformat(),
            connection_id=auto_connect.connection_id,
            flow_id=auto_connect.flow_id,
            action=auto_connect.action,
            route_id=auto_connect.route_id,
            panel_id=auto_connect.panel_id,
        )
        history = [
            ConversationMessage(**item)
            for item in (request.conversation or [])
            if isinstance(item, dict)
        ]
        history.append(reply)
        fast_updated_project_memory = build_updated_project_memory(
            project_memory,
            project_root=project_root,
            message=message,
            reply_content=fast_reply_content,
            conversation_stage=conversation_stage,
            message_kind=message_kind,
        )
        fast_technology_recommendations = build_technology_recommendations(
            message,
            fast_reply_content,
            web_results=web_results,
            fallback_candidates=new_technology_candidates,
        )
        fast_response = OrchestratorChatResponse(
            reply=reply,
            conversation=history,
            output_dir=request.output_dir,
            run_id=request.run_id or uuid4().hex,
            session_id=session_id or None,
            grounding_mode="web" if web_results else "internal",
            grounding_note="관리자 빠른 응답 경로 (웹 검색 근거 포함)" if web_results else "관리자 빠른 응답 경로",
            companion_mode=request.companion_mode,
            web_results=web_results,
            suggested_companion_mode=suggested_mode,
            suggested_companion_reason="짧은 관리자 입력은 빠른 응답 경로로 처리했습니다.",
            conversation_stage=conversation_stage,
            clarification_questions=clarification_questions[:2],
            evidence_highlights=evidence_highlights[:2],
            next_action_suggestions=next_action_suggestions[:2] if lightweight else [
                AdvisoryNextAction(
                    title="작업 지시 구체화",
                    action_type="follow-up",
                    detail="수정 대상 파일, 기대 결과, 유지 조건을 함께 보내면 바로 실행형 답으로 이어집니다.",
                    recommended_mode="project",
                )
            ],
            flow_trace=flow_trace,
            command_plan=command_plan,
            active_trace=active_trace,
            message_kind=message_kind,
            multi_turn_enabled=multi_turn_enabled,
            conversation_summary=conversation_summary,
            inferred_goal=inferred_goal,
            proposal_items=proposal_items,
            new_technology_candidates=new_technology_candidates,
            technology_recommendations=fast_technology_recommendations,
            target_patch_hints=target_patch_hints,
            project_root=project_root,
            project_memory=fast_updated_project_memory,
            auto_connect=auto_connect,
            diagnostics=diagnostics,
        )
        _save_response_session(
            session_id,
            fast_response,
            project_memory=fast_updated_project_memory,
            session_owner_id=session_owner_id,
        )
        return fast_response
    system_prompt = build_chat_system_prompt(
        mode_label,
        conversation_stage,
        requested_conversation_mode,
        lightweight=lightweight,
        response_style=response_style,
        multi_turn_enabled=multi_turn_enabled,
        context_tags=context_tags,
        emotion_tone_guidance=emotion_tone_guidance,
        web_grounding_enabled=bool(web_results),
    )
    user_prompt = build_chat_user_prompt(
        message,
        conversation_context,
        command_plan_lines,
        lightweight=lightweight,
        conversation_summary=conversation_summary,
        message_kind=message_kind,
        project_root=project_root,
        project_memory_summary=project_memory_summary,
        emotion_signal=emotion_signal,
        web_grounding_block=web_grounding_block,
    )
    reply_content = ""
    model_name = resolve_chat_model(request.agent_key or agent_key, lightweight=lightweight)
    diagnostics["path"] = "llm"
    diagnostics["model"] = model_name
    diagnostics["timeout_sec"] = requested_timeout_sec
    llm_started_at = perf_counter()
    try:
        reply_content = await call_orchestrator_chat_llm(
            route_key="chat",
            model=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=requested_max_tokens,
            ollama_base=ollama_base,
            timeout_sec=requested_timeout_sec,
            build_ollama_options=build_ollama_options,
        )
    except Exception as exc:
        logger.warning("관리자 자율 대화 LLM 호출 실패, fallback 사용: %s", exc)
        diagnostics["used_fallback"] = True
        diagnostics["path"] = "fallback"
        diagnostics["fallback_reason"] = str(exc)
    finally:
        diagnostics["llm_elapsed_ms"] = round((perf_counter() - llm_started_at) * 1000, 2)
        logger.info(
            "admin-chat diagnostics | kind=%s stage=%s lightweight=%s len=%s model=%s timeout_sec=%s elapsed_ms=%s path=%s fallback=%s",
            message_kind,
            conversation_stage,
            lightweight,
            len(message),
            diagnostics.get("model"),
            diagnostics.get("timeout_sec"),
            diagnostics.get("llm_elapsed_ms"),
            diagnostics.get("path"),
            diagnostics.get("used_fallback"),
        )
    if not reply_content:
        reply_content = build_admin_chat_fallback_reply(
            message,
            message_kind=message_kind,
            conversation_stage=conversation_stage,
            command_plan=command_plan,
        )
    if approval_gate_warning:
        reply_content = f"{approval_gate_warning}\n\n{reply_content}".strip()
    reply_content = _append_reciprocal_question(
        reply_content,
        message=message,
        lightweight=lightweight,
        requested_conversation_mode=requested_conversation_mode,
        response_style=response_style,
        message_kind=message_kind,
        conversation_stage=conversation_stage,
    )

    reply = ConversationMessage(
        role="assistant",
        speaker=agent_key,
        content=reply_content,
        step_id=auto_connect.step_id or (active_trace.step_id if active_trace else "FLOW-001-1"),
        step_title=active_trace.title if active_trace else "멀티 명령 해석",
        timestamp=datetime.now().isoformat(),
        connection_id=auto_connect.connection_id,
        flow_id=auto_connect.flow_id,
        action=auto_connect.action,
        route_id=auto_connect.route_id,
        panel_id=auto_connect.panel_id,
    )
    history = [
        ConversationMessage(**item)
        for item in (request.conversation or [])
        if isinstance(item, dict)
    ]
    history.append(reply)
    updated_project_memory = build_updated_project_memory(
        project_memory,
        project_root=project_root,
        message=message,
        reply_content=reply_content,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
    )
    if project_root and session_factory is not None:
        db: Session = session_factory()
        try:
            persisted_context = upsert_project_memory_snapshot(
                db,
                project_root=project_root,
                memory=updated_project_memory,
                approval_gate=(persisted_context or {}).get("approval_gate") if isinstance(persisted_context, dict) else None,
            )
            updated_project_memory = dict((persisted_context or {}).get("memory") or updated_project_memory)
        finally:
            db.close()
    technology_recommendations = build_technology_recommendations(
        message,
        reply_content,
        web_results=web_results,
        fallback_candidates=new_technology_candidates,
    )
    response = OrchestratorChatResponse(
        reply=reply,
        conversation=history,
        output_dir=request.output_dir,
        run_id=request.run_id or uuid4().hex,
        session_id=session_id or None,
        grounding_mode="web" if web_results else "internal",
        grounding_note=grounding_note,
        companion_mode=request.companion_mode,
        web_results=web_results,
        suggested_companion_mode=suggested_mode,
        suggested_companion_reason=suggested_reason,
        conversation_stage=conversation_stage,
        clarification_questions=clarification_questions,
        evidence_highlights=evidence_highlights,
        next_action_suggestions=next_action_suggestions,
        flow_trace=flow_trace,
        command_plan=command_plan,
        active_trace=active_trace,
        message_kind=message_kind,
        multi_turn_enabled=multi_turn_enabled,
        conversation_summary=conversation_summary,
        suggested_prompts=[] if lightweight else [
            "이 주제로 인터넷 기준 최신 방법까지 같이 정리해줘",
            "핵심만 실험 계획으로 바꿔줘",
            "결과를 반영해서 자가확장 실행 작업문으로 정리해줘",
        ],
        inferred_goal=inferred_goal,
        proposal_items=proposal_items,
        new_technology_candidates=new_technology_candidates,
        technology_recommendations=technology_recommendations,
        target_patch_hints=target_patch_hints,
        project_root=project_root,
        project_memory=updated_project_memory,
        auto_connect=auto_connect,
        diagnostics=diagnostics,
    )
    _save_response_session(
        session_id,
        response,
        project_memory=updated_project_memory,
        session_owner_id=session_owner_id,
    )
    return response
