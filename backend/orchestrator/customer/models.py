from __future__ import annotations

from typing import Any, Callable, Optional


ProgressCallback = Optional[Callable[[str, str], None]]
RunOrchestrationFunc = Callable[..., Any]
EmitProgressFunc = Callable[[ProgressCallback, str, str], None]
