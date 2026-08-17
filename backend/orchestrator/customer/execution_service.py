from __future__ import annotations

from typing import Awaitable, Callable, Optional


async def execute_orchestration(
    request,
    *,
    run_orchestration_func: Callable[..., Awaitable[object]],
    emit_orchestration_progress_func: Callable[[Optional[Callable[[str, str], None]], str, str], None],
    progress_callback: Optional[Callable[[str, str], None]] = None,
):
    try:
        return await run_orchestration_func(
            request,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        emit_orchestration_progress_func(
            progress_callback,
            str(exc) or "오케스트레이터 실행 중 오류가 발생했습니다.",
            "error",
        )
        raise
