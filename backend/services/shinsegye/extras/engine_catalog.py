"""
소리새 엔진 통합 카탈로그

이 파일은 tmp/external_migrations의 모든 소리새 소스 파일을 분류하고
통합 상태를 기록하는 공식 레지스트리입니다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any
import json


TARGET_MARKETPLACE_SLOTS = 120

# ── 통합 완료된 엔진 목록 ──────────────────────────────────────────────
INTEGRATED_ENGINES: List[Dict[str, Any]] = [
    # 통역/언어 축 (addons/shinsegye_interpreter/src/)
    {"id": "INT-001", "file": "sorisae_interpreter.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "official", "market_status": "official", "display_name_ko": "나도 통역사 (정식본)"},
    {"id": "INT-002", "file": "hybrid_interpreter_system.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/health", "status": "integrated"},
    {"id": "INT-003", "file": "hybrid_conversation_translator.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-004", "file": "multilingual_system.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-005", "file": "sorisae_multilingual_support.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-006", "file": "sorisae_southeast_asia_translator.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    # 음악/오디오 축 (addons/shinsegye_music_system/src/)
    {"id": "MUS-001", "file": "ai_music_composer.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/compose/emotion", "status": "integrated"},
    {"id": "MUS-002", "file": "emotion_based_music_generator.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/compose/emotion", "status": "integrated"},
    {"id": "MUS-003", "file": "music_chat_friend_system.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/friends/demo", "status": "integrated"},
    # IoT 축 (addons/shinsegye_extras/src/)
    {"id": "IOT-001", "file": "hybrid_iot_controller.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/health", "status": "integrated"},
    {"id": "IOT-002", "file": "sorisae_iot_smarthome.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/devices", "status": "integrated"},
    {"id": "IOT-003", "file": "sorisae_iot_integration.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    {"id": "IOT-004", "file": "multi_ego_engine.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    {"id": "IOT-005", "file": "spatiotemporal_learning_system.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    # 게임 경제 축 (addons/shinsegye_extras/src/)
    {"id": "GAM-001", "file": "sorisae_game_economy_system.py", "category": "simulation", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/game/simulate", "status": "integrated"},
]

# ── 미통합 엔진 목록 (기타 243개 중 대표 목록) ──────────────────────
# 하드웨어 의존성으로 오프라인 전용 분류
OFFLINE_ENGINES: List[Dict[str, Any]] = [
    # 음성/TTS 카테고리 (speech_recognition, pyttsx3 요구)
    {"id": "VOI-001", "file": "sorisae_voice_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-002", "file": "hybrid_voice_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-003", "file": "voice_calling_system.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-004", "file": "voice_command_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-005", "file": "sorisae_iot_voice_control.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-006", "file": "voice_tuner.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-007", "file": "sorisae_voice_reactive.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    # 보안 카테고리
    {"id": "SEC-001", "file": "hybrid_cyber_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-002", "file": "advanced_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-003", "file": "biometric_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-004", "file": "cyber_detective_ai.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    # AI 브레인 카테고리
    {"id": "BRN-001", "file": "sorisae_master_hybrid_system.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-002", "file": "sorisae_ai_decision_engine.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-003", "file": "sorisae_enhanced_consciousness.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-004", "file": "sorisae_ethical_consciousness_engine.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    # 시뮬레이션 카테고리 (추가 통합 대상)
    {"id": "SIM-001", "file": "game_earning_analysis.py", "category": "simulation", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SIM-002", "file": "sorisae_fantasy_vr_infinite_universe_game.py", "category": "simulation", "deps": [], "status": "available", "reason": "pending-integration"},
    # 투자/금융 카테고리
    {"id": "FIN-001", "file": "sorisae_investment_advisor_200.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "FIN-002", "file": "stock_prediction_200_percent.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "FIN-003", "file": "sorisae_dual_brain_stock_system.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
]


def get_all_engines() -> List[Dict[str, Any]]:
    """전체 엔진 목록 반환"""
    return INTEGRATED_ENGINES + OFFLINE_ENGINES


def _resolve_source_base() -> Path:
    """원본 소리새 마이그레이션 소스 루트 경로를 계산한다."""
    here = Path(__file__).resolve()
    # 1순위: codeAI/tmp/external_migrations/run_all_shinsegye.py
    primary = here.parents[4] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
    if primary.exists():
        return primary
    # 2순위(레거시): backend/tmp/external_migrations/run_all_shinsegye.py
    legacy = here.parents[3] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
    if legacy.exists():
        return legacy
    # 3순위: 전체 합병본 디렉토리
    merged = here.parents[4] / "addons" / "shinsegye_extras" / "src" / "full_merge_all"
    if merged.exists():
        return merged
    return legacy


def _infer_priority(file_name: str) -> Dict[str, Any]:
    lowered = file_name.lower()
    if any(token in lowered for token in ("voice", "speech", "tts", "stt", "audio")):
        return {"priority": "P1", "category": "voice", "reason": "voice-marketplace-quick-win", "api_hint": "/api/marketplace/extras/voice"}
    if any(token in lowered for token in ("interpreter", "translate", "translator", "language", "multilingual")):
        return {"priority": "P1", "category": "interpreter", "reason": "language-engine-demand", "api_hint": "/api/marketplace/interpreter"}
    if any(token in lowered for token in ("music", "song", "composer", "lyric", "midi")):
        return {"priority": "P1", "category": "music", "reason": "content-engine-demand", "api_hint": "/api/marketplace/music"}
    if any(token in lowered for token in ("iot", "device", "sensor", "smarthome")):
        return {"priority": "P2", "category": "iot", "reason": "iot-expansion", "api_hint": "/api/marketplace/extras/iot"}
    if any(token in lowered for token in ("security", "cyber", "auth", "biometric")):
        return {"priority": "P2", "category": "security", "reason": "security-expansion", "api_hint": "/api/marketplace/extras/security"}
    if any(token in lowered for token in ("brain", "decision", "consciousness", "reasoning")):
        return {"priority": "P2", "category": "brain", "reason": "brain-engine-expansion", "api_hint": "/api/marketplace/extras/brain"}
    if any(token in lowered for token in ("stock", "invest", "finance", "trading", "portfolio")):
        return {"priority": "P3", "category": "finance", "reason": "finance-engine-expansion", "api_hint": "/api/marketplace/extras/finance"}
    if any(token in lowered for token in ("game", "simulation", "vr", "economy")):
        return {"priority": "P3", "category": "simulation", "reason": "simulation-expansion", "api_hint": "/api/marketplace/extras/game"}
    return {"priority": "P4", "category": "general", "reason": "backlog-candidate", "api_hint": "/api/marketplace/extras"}


def _priority_rank(priority: str) -> int:
    return {"P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 9)


def _category_name_ko(category: str) -> str:
    category_map = {
        "interpreter": "통역",
        "music": "음악",
        "iot": "IoT",
        "simulation": "시뮬레이션",
        "voice": "음성",
        "security": "보안",
        "brain": "AI 브레인",
        "finance": "금융",
        "general": "일반",
        "unassigned": "미배정",
    }
    return category_map.get(str(category or "").lower(), "일반")


def _build_engine_name_ko(slot: int, engine_id: str | None, category: str | None, source: str | None) -> str:
    source_name = str(source or "").strip().lower()

    if source_name == "empty":
        return f"미배정 엔진 #{slot:03d}"

    category_ko = _category_name_ko(str(category or ""))

    if source_name == "catalog_registered":
        return f"{category_ko} 운영 엔진 {str(engine_id or f'SLOT-{slot:03d}')}.".rstrip(".")
    if source_name == "engines120_bundle":
        return f"{category_ko} 실파일 엔진 #{slot:03d}"
    if source_name == "source_candidate_fixed":
        return f"{category_ko} 고정 실파일 엔진 #{slot:03d}"
    if source_name == "source_candidate":
        return f"{category_ko} 후보 엔진 #{slot:03d}"
    return f"{category_ko} 엔진 #{slot:03d}"


def _infer_priority_from_bundle_file(target_file: str, source_name: str | None) -> Dict[str, Any]:
    """engines120 실파일 내용을 기반으로 역할(category)을 재추론한다."""
    base = _infer_priority(str(source_name or target_file))
    file_path = Path(__file__).resolve().parents[1] / "engines120" / str(target_file)
    if not file_path.exists():
        return base

    try:
        text = file_path.read_text(encoding="utf-8-sig", errors="ignore")[:8000].lower()
    except Exception:
        return base

    name_signal = f"{str(target_file).lower()} {str(source_name or '').lower()}"
    content_signal = text
    lexicon = {
        "voice": ["voice", "speech", "stt", "tts", "audio", "microphone", "음성", "발화"],
        "interpreter": ["interpreter", "translate", "translator", "multilingual", "통역", "번역", "언어"],
        "music": ["music", "song", "melody", "composer", "lyric", "midi", "음악", "작곡"],
        "iot": ["iot", "device", "sensor", "smarthome", "thermostat", "home", "디바이스", "센서", "스마트홈"],
        "security": ["security", "cyber", "threat", "intrusion", "biometric", "investigator", "detective", "monitor", "보안", "침입", "위협"],
        "brain": ["brain", "consciousness", "ethical", "reasoning", "decision", "comparison", "의식", "추론", "판단"],
        "finance": ["stock", "invest", "finance", "trading", "portfolio", "주식", "투자", "금융"],
        "simulation": ["simulation", "game", "economy", "scenario", "simulator", "시뮬레이션", "게임", "경제"],
    }

    scores: Dict[str, int] = {}
    for category, keywords in lexicon.items():
        name_hits = 0
        content_hits = 0
        for kw in keywords:
            if kw in name_signal:
                name_hits += 1
            if kw in content_signal:
                content_hits += 1
        # 파일명/소스명 신호를 강하게 반영해 역할 오분류를 줄인다.
        scores[category] = (name_hits * 5) + content_hits

    best_category = max(scores, key=scores.get) # pyright: ignore[reportCallIssue, reportArgumentType]
    if scores.get(best_category, 0) <= 0:
        return base

    priority_by_category = {
        "voice": "P1",
        "interpreter": "P1",
        "music": "P1",
        "iot": "P2",
        "security": "P2",
        "brain": "P2",
        "finance": "P3",
        "simulation": "P3",
    }
    api_by_category = {
        "voice": "/api/marketplace/extras/voice",
        "interpreter": "/api/marketplace/interpreter",
        "music": "/api/marketplace/music",
        "iot": "/api/marketplace/extras/iot",
        "security": "/api/marketplace/extras/security",
        "brain": "/api/marketplace/extras/brain",
        "finance": "/api/marketplace/extras/finance",
        "simulation": "/api/marketplace/extras/game",
    }
    return {
        "priority": priority_by_category.get(best_category, "P4"),
        "category": best_category,
        "reason": f"bundle-content-inferred:{best_category}",
        "api_hint": api_by_category.get(best_category, "/api/marketplace/extras"),
    }


def _build_usage_description_ko(category: str | None, source: str | None, slot_status: str | None) -> str:
    category_usage = {
        "interpreter": "다국어 번역/통역과 언어 변환 흐름을 처리합니다.",
        "music": "감정 기반 음악 생성, 편곡, 오디오 결과물을 생성합니다.",
        "iot": "센서/디바이스 상태를 수집하고 스마트홈 제어를 수행합니다.",
        "simulation": "가상 시나리오와 경제/게임 시뮬레이션 분석에 사용됩니다.",
        "voice": "음성 입력 처리, 명령 인식, TTS/STT 파이프라인에 사용됩니다.",
        "security": "보안 이상징후 탐지, 인증/접근 통제 검증에 사용됩니다.",
        "brain": "의사결정 보조, 추론, 정책 판단 로직에 사용됩니다.",
        "finance": "투자/주가/리스크 분석 및 금융 의사결정 지원에 사용됩니다.",
        "general": "공통 백엔드 자동화 및 범용 처리 작업에 사용됩니다.",
        "unassigned": "아직 엔진이 배정되지 않아 우선순위에 따라 배정 예정입니다.",
    }
    source_name = str(source or "").strip().lower()
    status_name = str(slot_status or "").strip().lower()
    base = category_usage.get(str(category or "").lower(), category_usage["general"])
    if source_name == "engines120_bundle":
        return f"{base} 실파일 번들에서 로드된 후보로 즉시 테스트/연결이 가능합니다."
    if source_name == "source_candidate_fixed":
        return f"{base} 소리새 원본 실파일로 고정 등록된 엔진입니다."
    if source_name == "source_candidate":
        return f"{base} 원본 소스 후보군에서 수집된 엔진으로 통합 전 검증이 필요합니다."
    if source_name == "empty":
        return category_usage["unassigned"]
    if status_name == "completed":
        return f"{base} 현재 운영 경로에 통합 완료된 상태입니다."
    return base


def _build_experiment_template_ko(slot: int, category: str | None, source: str | None) -> str:
    cat = str(category or "general").lower()
    source_name = str(source or "").lower()

    if source_name == "empty":
        return "{\"todo\":\"엔진 미배정 슬롯\",\"요청\":\"해당 슬롯에 맞는 기능 엔진을 연결해 주세요.\"}"

    if cat == "interpreter":
        return "안녕하세요. 내일 오전 10시에 제품 데모 미팅이 있습니다. 영어로 번역해 주세요."
    if cat == "music":
        return "calm"
    if cat == "iot":
        return "{\"device_id\":\"living-room-light\",\"action\":\"status\",\"value\":null}"
    if cat == "simulation":
        return "{\"scenario\":\"weekend-promo\",\"users\":120}"
    if cat == "finance":
        return "{\"symbol\":\"005930\",\"horizon_days\":5,\"risk_tolerance\":\"medium\"}"
    if cat == "security":
        return "{\"event\":\"suspicious-login\",\"severity\":\"high\",\"ip\":\"203.0.113.10\"}"
    if cat == "voice":
        return "사용자 음성 명령: 거실 조명을 켜고 현재 온도를 알려줘"
    if cat == "brain":
        return "신규 기능 론칭 우선순위를 비용/효과/리스크 기준으로 3단계로 제안해 주세요."

    return f"슬롯 {slot:03d} 엔진 기능을 데모 입력으로 실행해 주세요. 결과를 JSON 요약으로 보여주세요."


def _discover_source_candidates(excluded_files: set[str], limit: int | None = None, min_size_bytes: int = 0) -> List[Dict[str, Any]]:
    src_base = _resolve_source_base()
    if not src_base.exists():
        return []

    candidates: List[Dict[str, Any]] = []
    for path in src_base.rglob("*.py"):
        path_text = str(path)
        if "__pycache__" in path_text:
            continue
        if path.stat().st_size <= max(0, int(min_size_bytes)):
            continue
        file_name = path.name
        if file_name in excluded_files:
            continue
        score = _infer_priority(file_name)
        candidates.append(
            {
                "file": file_name,
                "source_path": str(path.relative_to(src_base)).replace("\\", "/"),
                "bytes": int(path.stat().st_size),
                "priority": score["priority"],
                "category": score["category"],
                "reason": score["reason"],
                "api_hint": score["api_hint"],
                "status": "candidate",
            }
        )

    candidates.sort(key=lambda item: (_priority_rank(str(item.get("priority", "P9"))), -int(item.get("bytes", 0)), str(item.get("file", ""))))
    if isinstance(limit, int) and limit > 0:
        return candidates[:limit]
    return candidates


def build_remaining_source_fixed_registry() -> List[Dict[str, Any]]:
    """통합되지 않은 소리새 원본 파일을 고정 파일 레지스트리로 반환한다."""
    all_engines = get_all_engines()
    registered_files = {str(engine.get("file", "")) for engine in all_engines if engine.get("file")}
    candidates = _discover_source_candidates(registered_files, limit=None, min_size_bytes=0)

    fixed_rows: List[Dict[str, Any]] = []
    for idx, candidate in enumerate(candidates, start=1):
        fixed_rows.append(
            {
                "fixed_id": f"SRCFIX-{idx:03d}",
                "file": candidate.get("file"),
                "source_path": candidate.get("source_path"),
                "category": candidate.get("category"),
                "priority": candidate.get("priority"),
                "reason": candidate.get("reason") or "fixed-source-file",
                "api_hint": candidate.get("api_hint"),
                "source": "source_candidate_fixed",
                "engine_status": "fixed_file",
            }
        )
    return fixed_rows


def _load_generated_bundle_manifest() -> List[Dict[str, Any]]:
    """생성된 120엔진 실파일 매니페스트를 로드한다."""
    bundle_manifest = Path(__file__).resolve().parents[1] / "engines120" / "engines120_manifest.json"
    if not bundle_manifest.exists():
        return []
    try:
        raw = bundle_manifest.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _build_slot_rails(slot_rows: List[Dict[str, Any]], rail_size: int = 20) -> List[Dict[str, Any]]:
    """슬롯 목록을 20개 단위 레일로 묶는다."""
    if rail_size <= 0:
        rail_size = 20

    rails: List[Dict[str, Any]] = []
    for start in range(0, len(slot_rows), rail_size):
        chunk = slot_rows[start:start + rail_size]
        if not chunk:
            continue
        rail_index = len(rails) + 1
        completed = sum(1 for row in chunk if row.get("slot_status") == "completed")
        pending = len(chunk) - completed
        rails.append(
            {
                "rail_id": f"RAIL-{rail_index:02d}",
                "rail_index": rail_index,
                "slot_start": int(chunk[0].get("slot", 0)),
                "slot_end": int(chunk[-1].get("slot", 0)),
                "rail_size": len(chunk),
                "completed_slots": completed,
                "pending_slots": pending,
                "items": chunk,
            }
        )
    return rails


def build_marketplace_slot_checklist(target_slots: int = TARGET_MARKETPLACE_SLOTS) -> Dict[str, Any]:
    """120 슬롯 기준 실행 체크리스트(완료/미완료/우선순위)를 생성한다."""
    all_engines = get_all_engines()
    registered_files = {str(engine.get("file", "")) for engine in all_engines if engine.get("file")}

    slot_rows: List[Dict[str, Any]] = []
    slot = 1

    for engine in all_engines:
        if slot > target_slots:
            break
        engine_status = str(engine.get("status", "pending"))
        source = "catalog_registered"
        category = engine.get("category")
        engine_id = engine.get("id")
        is_completed = engine_status in {"integrated", "official"}
        slot_status = "completed" if is_completed else "pending"
        engine_name_ko = str(engine.get("display_name_ko") or "").strip() or _build_engine_name_ko(
            slot=slot,
            engine_id=str(engine_id or ""),
            category=str(category or ""),
            source=source,
        )
        slot_rows.append(
            {
                "slot": slot,
                "engine_id": engine_id,
                "engine_name_ko": engine_name_ko,
                "file": engine.get("file"),
                "category": category,
                "priority": "P0" if is_completed else "P1",
                "slot_status": slot_status,
                "engine_status": engine_status,
                "market_status": engine.get("market_status") or ("official" if engine_status == "official" else None),
                "is_official": bool(engine.get("market_status") == "official" or engine_status == "official"),
                "source": source,
                "api": engine.get("api"),
                "reason": engine.get("reason") or "registered-catalog-engine",
                "usage_description_ko": _build_usage_description_ko(category=str(category or ""), source=source, slot_status=slot_status),
                "experiment_template_ko": _build_experiment_template_ko(slot=slot, category=str(category or "general"), source=source),
            }
        )
        slot += 1

    needed = max(0, target_slots - len(slot_rows))
    bundle_manifest = _load_generated_bundle_manifest()
    bundle_index = 0
    while slot <= target_slots and bundle_index < len(bundle_manifest):
        item = bundle_manifest[bundle_index]
        bundle_index += 1
        target_file = str(item.get("target_file", "") or "").strip()
        if not target_file:
            continue
        bundle_priority = _infer_priority_from_bundle_file(
            target_file=target_file,
            source_name=str(item.get("source_name", "") or ""),
        )
        slot_rows.append(
            {
                "slot": slot,
                "engine_id": f"BUNDLE-{slot:03d}",
                "engine_name_ko": _build_engine_name_ko(
                    slot=slot,
                    engine_id=f"BUNDLE-{slot:03d}",
                    category=str(bundle_priority.get("category") or "general"),
                    source="engines120_bundle",
                ),
                "file": target_file,
                "source_file": item.get("source_name"),
                "category": bundle_priority.get("category"),
                "priority": str(bundle_priority.get("priority", item.get("priority", "P4"))),
                "slot_status": "pending",
                "engine_status": "bundle_ready",
                "source": "engines120_bundle",
                "source_path": item.get("source_rel"),
                "api": bundle_priority.get("api_hint"),
                "reason": bundle_priority.get("reason") or "real-file-bundle-ready",
                "usage_description_ko": _build_usage_description_ko(
                    category=str(bundle_priority.get("category") or "general"),
                    source="engines120_bundle",
                    slot_status="pending",
                ),
                "experiment_template_ko": _build_experiment_template_ko(
                    slot=slot,
                    category=str(bundle_priority.get("category") or "general"),
                    source="engines120_bundle",
                ),
            }
        )
        slot += 1

    candidates = build_remaining_source_fixed_registry()
    candidate_index = 0
    while slot <= target_slots:
        if candidate_index < len(candidates):
            candidate = candidates[candidate_index]
            candidate_index += 1
            slot_rows.append(
                {
                    "slot": slot,
                    "engine_id": f"CAND-{slot:03d}",
                    "engine_name_ko": _build_engine_name_ko(
                        slot=slot,
                        engine_id=str(candidate.get("fixed_id") or f"SRCFIX-{slot:03d}"),
                        category=str(candidate.get("category") or "general"),
                        source="source_candidate_fixed",
                    ),
                    "file": candidate.get("file"),
                    "category": candidate.get("category"),
                    "priority": candidate.get("priority"),
                    "slot_status": "pending",
                    "engine_status": "fixed_file",
                    "source": "source_candidate_fixed",
                    "source_path": candidate.get("source_path"),
                    "api": candidate.get("api_hint"),
                    "reason": candidate.get("reason") or "fixed-source-file",
                    "usage_description_ko": _build_usage_description_ko(
                        category=str(candidate.get("category") or "general"),
                        source="source_candidate_fixed",
                        slot_status="pending",
                    ),
                    "experiment_template_ko": _build_experiment_template_ko(
                        slot=slot,
                        category=str(candidate.get("category") or "general"),
                        source="source_candidate_fixed",
                    ),
                }
            )
        else:
            slot_rows.append(
                {
                    "slot": slot,
                    "engine_id": f"UNASSIGNED-{slot:03d}",
                    "engine_name_ko": _build_engine_name_ko(
                        slot=slot,
                        engine_id=f"UNASSIGNED-{slot:03d}",
                        category="unassigned",
                        source="empty",
                    ),
                    "file": None,
                    "category": "unassigned",
                    "priority": "P9",
                    "slot_status": "pending",
                    "engine_status": "unassigned",
                    "source": "empty",
                    "api": None,
                    "reason": "candidate-source-exhausted",
                    "usage_description_ko": _build_usage_description_ko(category="unassigned", source="empty", slot_status="pending"),
                    "experiment_template_ko": _build_experiment_template_ko(slot=slot, category="unassigned", source="empty"),
                }
            )
        slot += 1

    completed = sum(1 for row in slot_rows if row.get("slot_status") == "completed")
    pending = len(slot_rows) - completed
    slot_rails = _build_slot_rails(slot_rows, rail_size=20)

    return {
        "target_slots": target_slots,
        "rail_size": 20,
        "rail_count": len(slot_rails),
        "completed_slots": completed,
        "pending_slots": pending,
        "registered_engine_count": len(all_engines),
        "registered_integrated_count": len([e for e in all_engines if e.get("status") in {"integrated", "official"}]),
        "source_candidate_count": len(candidates),
        "fixed_source_file_count": len(candidates),
        "fixed_source_files": candidates,
        "slots": slot_rows,
        "slot_rails": slot_rails,
        "priority_plan_36_120": [row for row in slot_rows if 36 <= int(row.get("slot", 0)) <= 120],
    }


def get_integration_summary() -> Dict[str, Any]:
    """통합 현황 요약"""
    integrated = [e for e in INTEGRATED_ENGINES]
    offline = [e for e in OFFLINE_ENGINES if e["status"] == "offline"]
    available = [e for e in OFFLINE_ENGINES if e["status"] == "available"]

    # 실제 소스 파일 총수 (tmp 디렉토리 기반)
    src_base = _resolve_source_base()
    total_src_files = 0
    if src_base.exists():
        total_src_files = sum(1 for f in src_base.rglob("*.py")
                              if "__pycache__" not in str(f) and f.stat().st_size > 1000)

    fixed_rows = build_remaining_source_fixed_registry()

    return {
        "total_source_files": total_src_files,
        "integrated_count": len(integrated),
        "offline_count": len(offline),
        "available_for_integration": len(available),
        "remaining_fixed_file_count": len(fixed_rows),
        "integration_rate": round(len(integrated) / max(total_src_files, 1) * 100, 1),
        "categories": {
            "interpreter": len([e for e in integrated if e["category"] == "interpreter"]),
            "music": len([e for e in integrated if e["category"] == "music"]),
            "iot": len([e for e in integrated if e["category"] == "iot"]),
            "simulation": len([e for e in integrated if e["category"] == "simulation"]),
            "voice_offline": len(offline),
            "pending": len(available),
        }
    }
