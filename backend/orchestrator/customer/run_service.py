from __future__ import annotations

from .models import ProgressCallback


async def run_customer_orchestration(
    request,
    *,
    run_orchestration_impl,
    progress_callback: ProgressCallback = None,
):
    return await run_orchestration_impl(
        request,
        progress_callback=progress_callback,
    )
