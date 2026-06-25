"""Ops — 라이브 상시운영 + 재학습 오케스트레이션(설계서 §6/§7/§10-5).

- `LiveRunner`: 자동재연결·heartbeat·일일리포트 슈퍼바이저.
- `RetrainOrchestrator`: TradeStore/감사로그 트리거 → 데이터셋→재학습→워크포워드→ONNX 핫스왑.
"""
from .runner import DailyReport, LiveRunner, RunnerConfig
from .retrain import (
    AcceptanceConfig,
    RetrainOrchestrator,
    RetrainReport,
    TriggerConfig,
    TriggerDecision,
    evaluate_trigger,
)
from .scheduler import Job, Scheduler
from .registry import (
    CurrentModel,
    add_blacklist,
    append_history,
    apply_signal_overrides,
    auto_rollback,
    current_path,
    history_path,
    is_signature_blacklisted,
    load_current,
    load_history,
    model_signature,
    record_rollback,
    retrain_paused_until,
    rollback_current,
    signature_params,
)

__all__ = [
    "LiveRunner",
    "RunnerConfig",
    "DailyReport",
    "CurrentModel",
    "load_current",
    "load_history",
    "current_path",
    "history_path",
    "append_history",
    "rollback_current",
    "auto_rollback",
    "add_blacklist",
    "is_signature_blacklisted",
    "model_signature",
    "signature_params",
    "record_rollback",
    "retrain_paused_until",
    "apply_signal_overrides",
    "RetrainOrchestrator",
    "RetrainReport",
    "TriggerConfig",
    "TriggerDecision",
    "AcceptanceConfig",
    "evaluate_trigger",
    "Scheduler",
    "Job",
]
