"""단계별 자연어 명령 파서 — 설계 / 진행 / 협업."""
from __future__ import annotations

from backend.orchestrator.autonomous.session import AutonomousSession
from backend.orchestrator.autonomous.stage_commands import (
    parse_stage_command,
    stage_index_from_number,
)


def test_design_command_defaults_to_stage_one():
    cmd = parse_stage_command("설계해줘")
    assert cmd is not None
    assert cmd.action == "design"
    assert cmd.stage_index == 0
    assert cmd.stage_number == 1


def test_execute_command_parses_stage_number():
    cmd = parse_stage_command("2단계 진행해줘")
    assert cmd is not None
    assert cmd.action == "execute"
    assert cmd.stage_index == 1
    assert cmd.stage_number == 2


def test_execute_command_parses_stage_three():
    cmd = parse_stage_command("3단계 진행해줘")
    assert cmd is not None
    assert cmd.action == "execute"
    assert cmd.stage_index == 2


def test_discuss_command_at_stage_four():
    cmd = parse_stage_command("4단계 Redis 캐시 아이디어 제안해줘")
    assert cmd is not None
    assert cmd.action == "discuss"
    assert cmd.stage_index == 3
    assert cmd.stage_number == 4


def test_pending_approval_progress_maps_to_current_stage():
    session = AutonomousSession.create(owner_id="u1", mode="semi_auto")
    session.execution_state = "awaiting_approval"
    session.approval_state = "pending"
    session.current_stage_index = 0

    cmd = parse_stage_command("진행해", session)
    assert cmd is not None
    assert cmd.action == "execute"
    assert cmd.stage_index == 0


def test_collaboration_discuss_without_stage_number():
    session = AutonomousSession.create(owner_id="u1", mode="semi_auto")
    session.current_stage_index = 3  # 4단계

    cmd = parse_stage_command("신기술 검색해서 추천해줘", session)
    assert cmd is not None
    assert cmd.action == "discuss"
    assert cmd.stage_index == 3


def test_stage_index_from_number_supports_half_step():
    assert stage_index_from_number(4.5) == 4
