"""LLM 스마트 라우터 — A브레인(계획) → B브레인(실행) 파이프라인"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
import re
from typing import Dict, Optional

from .model_config import (
    build_ollama_options,
    get_smart_designer_model,
    get_smart_executor_model,
    get_smart_planner_model,
)

router = APIRouter(prefix="/api/llm", tags=["llm-smart"])

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1")

PLANNER_SYSTEM = """당신은 시니어 소프트웨어 아키텍트입니다.
사용자의 코드 요청을 받아 구현 계획을 수립합니다.
규칙: 반드시 한국어로 답변. 최대 6단계 계획. 코드 작성 금지."""

EXECUTOR_SYSTEM = """당신은 전문 Python/TypeScript 개발자입니다.
A브레인이 작성한 계획을 바탕으로 실제 코드를 생성합니다.
규칙: 반드시 한국어 주석. 프로덕션 수준 코드. 에러 핸들링 포함."""

DESIGN_SYSTEM = """반드시 한국어로만 답변하세요. You must reply in Korean only.
당신은 UI/UX 전문 디자이너입니다. Tailwind CSS와 React/Next.js 기준으로 설계합니다.
컴포넌트 구조, 색상, 레이아웃, 코드 예시를 제공하세요."""

DESIGN_KEYWORDS = re.compile(
    r"(디자인|UI|UX|레이아웃|layout|컴포넌트|component|색상|color|스타일|style|"
    r"화면|페이지|page|카드|card|버튼|button|폼|form|헤더|header|푸터|footer|"
    r"반응형|responsive|모바일|mobile|아이콘|icon|애니메이션|animation)",
    re.IGNORECASE,
)


class SmartRequest(BaseModel):
    prompt: str
    mode: Optional[str] = "auto"
    max_tokens: int = 4096


class SmartResponse(BaseModel):
    mode: str
    engine: str
    result: str
    plan: Optional[str] = None


def _current_engines() -> Dict[str, str]:
    return {
        "coder_planner": get_smart_planner_model(),
        "coder_executor": get_smart_executor_model(),
        "designer": get_smart_designer_model(),
    }


def detect_mode(prompt: str) -> str:
    return "design" if DESIGN_KEYWORDS.search(prompt) else "code"


async def call_ollama(
    route_key: str,
    model: str,
    prompt: str,
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    """코딩봇용 — OpenAI 호환 규격(/v1/chat/completions)"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{OLLAMA_BASE}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


async def call_ollama_chat(
    route_key: str,
    model: str,
    user_prompt: str,
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    """디자이너용 — OpenAI 호환 규격(/v1/chat/completions)"""
    combined = f"{system}\n\n{user_prompt}" if system else user_prompt
    messages = [{"role": "user", "content": combined}]
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "top_p": 0.9,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{OLLAMA_BASE}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


@router.post("/smart", response_model=SmartResponse)
async def smart_generate(request: SmartRequest):
    """스마트 라우터: 요청 유형에 따라 최적 엔진으로 라우팅"""
    mode = (
        request.mode if request.mode != "auto" else detect_mode(request.prompt)
    )
    engines = _current_engines()

    try:
        if mode == "design":
            # 디자이너: /api/chat 방식 (system/user 분리)
            result = await call_ollama_chat(
                "designer",
                engines["designer"],
                request.prompt,
                system=DESIGN_SYSTEM,
                max_tokens=request.max_tokens,
            )
            return SmartResponse(
                mode="design",
                engine=engines["designer"],
                result=result,
            )
        else:
            # A브레인: 계획 수립
            plan_prompt = f"다음 요청의 구현 계획을 수립해주세요:\n\n{request.prompt}"
            plan = await call_ollama(
                "smart_planner",
                engines["coder_planner"],
                plan_prompt,
                system=PLANNER_SYSTEM,
                max_tokens=512,
            )
            # B브레인: 코드 생성
            exec_prompt = (
                f"다음 계획을 바탕으로 코드를 작성해주세요.\n\n"
                f"=== 원래 요청 ===\n{request.prompt}\n\n"
                f"=== A브레인 계획 ===\n{plan}\n\n"
                f"위 계획을 완전히 구현하는 코드를 작성하세요."
            )
            code = await call_ollama(
                "smart_executor",
                engines["coder_executor"],
                exec_prompt,
                system=EXECUTOR_SYSTEM,
                max_tokens=request.max_tokens,
            )
            return SmartResponse(
                mode="code",
                engine=(
                    f"{engines['coder_planner']} → "
                    f"{engines['coder_executor']}"
                ),
                result=code,
                plan=plan,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스마트 라우터 오류: {str(e)}")


@router.get("/engines")
async def get_engines():
    """현재 설정된 엔진 목록"""
    engines = _current_engines()
    return {
        "engines": engines,
        "ollama_url": OLLAMA_BASE,
        "routing": {
            "code": (
                f"{engines['coder_planner']} (계획) → "
                f"{engines['coder_executor']} (코드)"
            ),
            "design": engines["designer"],
        },
    }
