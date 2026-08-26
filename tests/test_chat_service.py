import pytest

from app.config import load_settings
from app.services import chat
from app.sessions import SessionStore


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"result": {"message": {"contextId": "ctx-1", "parts": [{"kind": "text", "text": "법령 답변"}]}}}


class FakeClient:
    captured = None

    def __init__(self, **_):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, url, **kwargs):
        FakeClient.captured = (url, kwargs)
        return FakeResponse()


@pytest.mark.asyncio
async def test_agent_reuses_history_and_context(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "test-key")
    monkeypatch.setattr(chat.httpx, "AsyncClient", FakeClient)
    store = SessionStore()
    session = store.create()
    store.append_turn(session.id, "이전 질문", "이전 답변")
    session.agent_context_id = "ctx-old"
    answer, context_id = await chat.call_agent(load_settings(), session, "후속 질문", "agent-slug", True)
    message = FakeClient.captured[1]["json"]["params"]["message"]
    assert "이전 질문" in message["parts"][0]["text"]
    assert message["contextId"] == "ctx-old"
    assert answer == "법령 답변"
    assert context_id == "ctx-1"
