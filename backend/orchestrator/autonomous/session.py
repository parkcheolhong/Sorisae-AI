"""자율대화 오케스트레이터 세션 상태 관리"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agents.base import AgentResult

logger = logging.getLogger(__name__)

AUTONOMOUS_SESSION_DIR = os.getenv(
    "AUTONOMOUS_SESSION_DIR",
    os.path.join(os.getenv("TEMP", "/tmp"), "codeai_autonomous_sessions"),
)

EXECUTION_MODES = {
    "advisory": "조언만 (실행 없음, 대화로 설계 논의)",
    "semi_auto": "반자동 (실행 전 사용자 승인 필요)",
    "full_auto": "완전자동 (위험도 낮은 작업은 자동 실행)",
}


@dataclass
class ConversationTurn:
    role: str  # user, agent, system
    agent_id: Optional[str]
    content: str
    timestamp: float = field(default_factory=time.time)
    artifacts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageState:
    stage_id: str
    stage_label: str
    status: str  # pending, in_progress, completed, failed, needs_revision
    agent_results: List[Dict[str, Any]] = field(default_factory=list)
    revision_count: int = 0


@dataclass
class AutonomousSession:
    session_id: str
    owner_id: str
    mode: str  # advisory, semi_auto, full_auto
    project_name: str = ""
    validation_profile: str = "python_fastapi"
    task: str = ""
    conversation: List[ConversationTurn] = field(default_factory=list)
    agent_results: List[AgentResult] = field(default_factory=list)
    stages: List[StageState] = field(default_factory=list)
    current_stage_index: int = 0
    execution_state: str = "idle"  # idle, planning, executing, reviewing, awaiting_approval, completed, failed
    approval_state: str = "none"  # none, pending, approved, rejected
    pending_approval_data: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    output_dir: Optional[str] = None
    model_routes: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        owner_id: str,
        mode: str = "semi_auto",
        project_name: str = "",
        validation_profile: str = "python_fastapi",
    ) -> "AutonomousSession":
        return cls(
            session_id=uuid.uuid4().hex[:16],
            owner_id=owner_id,
            mode=mode if mode in EXECUTION_MODES else "semi_auto",
            project_name=project_name,
            validation_profile=validation_profile,
        )

    def add_user_message(self, content: str) -> None:
        self.conversation.append(ConversationTurn(role="user", agent_id=None, content=content))
        self.updated_at = time.time()

    def add_agent_message(self, agent_id: str, content: str, artifacts: Optional[Dict] = None) -> None:
        self.conversation.append(ConversationTurn(
            role="agent",
            agent_id=agent_id,
            content=content,
            artifacts=artifacts or {},
        ))
        self.updated_at = time.time()

    def add_system_message(self, content: str) -> None:
        self.conversation.append(ConversationTurn(role="system", agent_id=None, content=content))
        self.updated_at = time.time()

    def get_current_stage(self) -> Optional[StageState]:
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    def advance_stage(self) -> Optional[StageState]:
        if self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
            return self.get_current_stage()
        return None

    def requires_approval(self) -> bool:
        if self.mode == "advisory":
            return False
        if self.mode == "full_auto":
            return False
        return True  # semi_auto

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "mode": self.mode,
            "project_name": self.project_name,
            "validation_profile": self.validation_profile,
            "task": self.task,
            "conversation": [asdict(t) for t in self.conversation[-30:]],
            "agent_results": [asdict(r) for r in self.agent_results[-20:]],
            "stages": [asdict(s) for s in self.stages],
            "current_stage_index": self.current_stage_index,
            "execution_state": self.execution_state,
            "approval_state": self.approval_state,
            "pending_approval_data": self.pending_approval_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "output_dir": self.output_dir,
            "model_routes": self.model_routes,
            "extra": self.extra,
        }

    def save(self) -> None:
        dir_path = Path(AUTONOMOUS_SESSION_DIR)
        dir_path.mkdir(parents=True, exist_ok=True)
        path = _session_file_path(self.session_id)
        if path is None:
            raise ValueError(f"Invalid autonomous session id: {self.session_id!r}")
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, session_id: str, owner_id: str) -> Optional["AutonomousSession"]:
        path = _session_file_path(session_id)
        if path is None:
            return None
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("owner_id") != owner_id:
                return None
            session = cls(
                session_id=data["session_id"],
                owner_id=data["owner_id"],
                mode=data.get("mode", "semi_auto"),
                project_name=data.get("project_name", ""),
                validation_profile=data.get("validation_profile", "python_fastapi"),
                task=data.get("task", ""),
                current_stage_index=data.get("current_stage_index", 0),
                execution_state=data.get("execution_state", "idle"),
                approval_state=data.get("approval_state", "none"),
                pending_approval_data=data.get("pending_approval_data"),
                created_at=data.get("created_at", time.time()),
                updated_at=data.get("updated_at", time.time()),
                output_dir=data.get("output_dir"),
                model_routes=data.get("model_routes", {}),
                extra=data.get("extra", {}),
            )
            for turn_data in data.get("conversation", []):
                session.conversation.append(ConversationTurn(**{
                    k: v for k, v in turn_data.items() if k in ConversationTurn.__dataclass_fields__
                }))
            for result_data in data.get("agent_results", []):
                session.agent_results.append(AgentResult(**{
                    k: v for k, v in result_data.items() if k in AgentResult.__dataclass_fields__
                }))
            for stage_data in data.get("stages", []):
                session.stages.append(StageState(**{
                    k: v for k, v in stage_data.items() if k in StageState.__dataclass_fields__
                }))
            return session
        except Exception as exc:
            logger.warning("Failed to load autonomous session %s: %s", session_id, exc)
            return None


def _session_file_path(session_id: str) -> Optional[Path]:
    if not session_id:
        return None
    try:
        base_dir = Path(AUTONOMOUS_SESSION_DIR).resolve()
        path = (base_dir / f"{session_id}.json").resolve()
    except (OSError, ValueError):
        return None
    if not path.is_relative_to(base_dir):
        return None
    return path
