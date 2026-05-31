from __future__ import annotations

import json
import logging

import pytest
from starlette.requests import Request

from backend.orchestrator.chat import chat_service
from backend.orchestrator.chat.models import OrchestratorChatRequest
from backend.orchestrator.chat import session_store


def _request(path: str = "/api/llm/orchestrate/chat") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 1234),
        }
    )


async def _answer(request_model: OrchestratorChatRequest, *, current_user=None):
    return await chat_service.answer_orchestrator_chat(
        request_context=_request(),
        request=request_model,
        agent_key="chat",
        resolve_chat_model=lambda agent_key, lightweight=False: "test-model",
        build_ollama_options=lambda **kwargs: {},
        ollama_base="http://ollama.test",
        orch_chat_request_max_tokens=768,
        orch_lightweight_chat_max_tokens=256,
        orch_chat_agent_timeout_sec=1.0,
        orch_reasoner_brief_timeout_sec=1.0,
        logger=logging.getLogger("test"),
        re_module=__import__("re"),
        session_factory=None,
        current_user=current_user,
    )


class _User:
    def __init__(self, user_id: str):
        self.id = user_id


@pytest.mark.asyncio
async def test_reverse_question_mode_forces_reciprocal_question(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_CHAT_SESSION_DIR", str(tmp_path))

    async def fake_llm(**kwargs):
        return "핵심은 대화 상태를 먼저 저장하고 실행은 명시 승인 뒤에만 시작하는 것입니다."

    monkeypatch.setattr(chat_service, "call_orchestrator_chat_llm", fake_llm)

    response = await _answer(
        OrchestratorChatRequest(
            message="오케스트레이션 멀티 자율형 대화모드 구조를 설계하고 기술 후보를 비교해줘",
            conversation=[
                {
                    "role": "user",
                    "content": "오케스트레이션 멀티 자율형 대화모드 구조를 설계하고 기술 후보를 비교해줘",
                }
            ],
            session_id="dialogue-test-1",
            conversation_mode="auto",
            reverse_question_mode="implementation",
            project_memory={"reverse_question_mode": "implementation"},
        )
    )

    assert response.session_id == "dialogue-test-1"
    assert response.diagnostics["requested_conversation_mode"] == "reverse_question"
    assert "역질문" in response.reply.content or "?" in response.reply.content or "무엇인가요" in response.reply.content
    assert response.clarification_questions
    assert response.technology_recommendations


@pytest.mark.asyncio
async def test_session_id_restores_previous_conversation(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_CHAT_SESSION_DIR", str(tmp_path))

    async def fake_llm(**kwargs):
        return "세션 기준으로 이전 결정을 이어서 반영합니다."

    monkeypatch.setattr(chat_service, "call_orchestrator_chat_llm", fake_llm)

    await _answer(
        OrchestratorChatRequest(
            message="첫 결정은 실행을 /run으로만 제한하는 것입니다.",
            conversation=[{"role": "user", "content": "첫 결정은 실행을 /run으로만 제한하는 것입니다."}],
            session_id="dialogue-test-2",
            reverse_question_mode="implementation",
            project_memory={"reverse_question_mode": "implementation"},
        )
    )
    response = await _answer(
        OrchestratorChatRequest(
            message="이전 결정을 이어서 기술 후보를 정리해줘",
            conversation=[{"role": "user", "content": "이전 결정을 이어서 기술 후보를 정리해줘"}],
            session_id="dialogue-test-2",
            reverse_question_mode="implementation",
            project_memory={"reverse_question_mode": "implementation"},
        )
    )

    joined = "\n".join(item.content for item in response.conversation)
    assert "첫 결정은 실행을 /run으로만 제한" in joined
    assert "이전 결정을 이어서 기술 후보" in joined


def test_session_snapshot_owner_mismatch_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_CHAT_SESSION_DIR", str(tmp_path))
    session_store.save_chat_session_snapshot(
        "dialogue-owner-mismatch",
        {"session_id": "dialogue-owner-mismatch", "session_owner_id": "owner-a", "conversation": []},
        session_owner_id="owner-a",
    )
    path = session_store._session_path("dialogue-owner-mismatch", session_owner_id="owner-a")
    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["session_owner_id"] = "owner-b"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = session_store.load_chat_session_snapshot("dialogue-owner-mismatch", session_owner_id="owner-a")
    assert loaded == {}


@pytest.mark.asyncio
async def test_session_id_is_scoped_by_current_user(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_CHAT_SESSION_DIR", str(tmp_path))

    async def fake_llm(**kwargs):
        return "같은 session_id라도 사용자별로 분리됩니다."

    monkeypatch.setattr(chat_service, "call_orchestrator_chat_llm", fake_llm)

    await _answer(
        OrchestratorChatRequest(
            message="owner-a의 이전 결정입니다.",
            conversation=[{"role": "user", "content": "owner-a의 이전 결정입니다."}],
            session_id="dialogue-test-owner",
            reverse_question_mode="implementation",
            project_memory={"reverse_question_mode": "implementation"},
        ),
        current_user=_User("owner-a"),
    )
    response = await _answer(
        OrchestratorChatRequest(
            message="owner-b 기준으로 이어서 설명해줘",
            conversation=[{"role": "user", "content": "owner-b 기준으로 이어서 설명해줘"}],
            session_id="dialogue-test-owner",
            reverse_question_mode="implementation",
            project_memory={"reverse_question_mode": "implementation"},
        ),
        current_user=_User("owner-b"),
    )

    joined = "\n".join(item.content for item in response.conversation)
    assert "owner-a의 이전 결정입니다." not in joined
    assert "owner-b 기준으로 이어서 설명해줘" in joined
