from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.core.url_security import parse_http_base_url
from backend.admin.orchestrator.path_utils import require_allowed_root_path
from backend.orchestrator.chat.flow_trace import split_multi_command_text


def test_parse_http_base_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError):
        parse_http_base_url("javascript:alert(1)")


def test_parse_http_base_url_rejects_private_host_when_policy_disabled() -> None:
    with pytest.raises(ValueError):
        parse_http_base_url("http://127.0.0.1:8000", allow_private_hosts=False)


def test_parse_http_base_url_marks_placeholder_domains() -> None:
    parsed = parse_http_base_url("https://payments.example.com")
    assert parsed.placeholder is True


def test_require_allowed_root_path_blocks_parent_traversal() -> None:
    traversal_path = Path("/tmp/../etc/passwd")
    with pytest.raises(Exception):
        require_allowed_root_path(traversal_path, detail="blocked")


def test_split_multi_command_text_handles_long_linear_input() -> None:
    source = ("1) alpha; 2) beta / 3) gamma\n" * 3000).strip()
    commands = split_multi_command_text(source)
    assert commands
    assert all(isinstance(item, str) and item for item in commands)
