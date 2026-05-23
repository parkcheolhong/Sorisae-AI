from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AdminRuntimeVerificationRequest(BaseModel):
    project_root: str = ""
    worker_log_path: str = ""
    mode: str = "full"


class AdminRuntimeVerificationItem(BaseModel):
    key: str
    label: str
    status: str
    detail: str
    checkedAt: str


class AdminRuntimeVerificationResponse(BaseModel):
    project_root: str
    verification_items: List[AdminRuntimeVerificationItem] = Field(default_factory=list)
    gate_policy: Dict[str, Any] = Field(default_factory=dict)
    gate_status: Dict[str, Any] = Field(default_factory=dict)
    operational_evidence: Dict[str, Any] = Field(default_factory=dict)
    operational_targets_by_id: Dict[str, Any] = Field(default_factory=dict)
    operational_evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
