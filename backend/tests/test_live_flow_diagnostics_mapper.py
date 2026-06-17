"""G-0-1: autonomous diagnostics → live flow rail contract."""
from __future__ import annotations

import pytest

from backend.orchestrator.autonomous.stage_definitions import STAGE_DEFINITIONS


def test_live_flow_stage_defs_count():
    assert len(STAGE_DEFINITIONS) == 11


@pytest.mark.parametrize(
    "stages_completed, intent, requires_approval",
    [
        (0, "greeting", False),
        (1, "stage_design", True),
        (3, "stage_discuss", False),
    ],
)
def test_autonomous_diagnostics_fields_present_in_mapper(stages_completed, intent, requires_approval):
    from backend.orchestrator.autonomous.surface_adapter import _map_autonomous_to_chat_response

    payload = {
        "content": "ok",
        "session_id": "sess-1",
        "intent": intent,
        "requires_approval": requires_approval,
        "execution_state": "executing",
        "approval_state": "pending" if requires_approval else "none",
        "current_stage": "STAGE-04",
        "stages_completed": stages_completed,
        "stages_total": 11,
        "stage_command": "discuss" if intent == "stage_discuss" else "design",
        "stage_number": 4,
        "stage_command_hint": "hint",
        "agent_results": [{"agent": "reasoner", "status": "success"}],
    }
    response = _map_autonomous_to_chat_response(
        autonomous_payload=payload,
        request_message="test",
        prior_conversation=[],
        surface="admin",
        run_id=None,
        task="task",
    )
    diag = response.diagnostics
    assert diag["orchestrator_core"] == "autonomous_turn_controller"
    assert diag["autonomous_intent"] == intent
    assert diag["requires_approval"] is requires_approval
    assert diag["current_stage"] == "STAGE-04"
    assert diag["stages_completed"] == stages_completed
