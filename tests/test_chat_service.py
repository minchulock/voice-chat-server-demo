import pytest

from app.config import load_settings
from app.services import chat
from app.sessions import SessionStore


class FakeStreamResponse:
    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        yield 'data: {"jsonrpc":"2.0","id":"request-1","result":{"task":{"id":"task-1","contextId":"ctx-1","status":{"state":"TASK_STATE_SUBMITTED"}}}}'
        yield 'data: {"jsonrpc":"2.0","id":"request-1","result":{"statusUpdate":{"taskId":"task-1","contextId":"ctx-1","status":{"state":"TASK_STATE_WORKING"}}}}'
        yield 'data: {"jsonrpc":"2.0","id":"request-1","result":{"artifactUpdate":{"taskId":"task-1","contextId":"ctx-1","artifact":{"artifactId":"result","parts":[{"text":"법령 답변"}]},"lastChunk":true}}}'


class FakeStreamContext:
    async def __aenter__(self):
        return FakeStreamResponse()

    async def __aexit__(self, *_):
        return None


class FakeClient:
    captured = None

    def __init__(self, **_):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def stream(self, method, url, **kwargs):
        FakeClient.captured = (method, url, kwargs)
        return FakeStreamContext()


@pytest.mark.asyncio
async def test_agent_v2_stream_reuses_history_and_extracts_final_artifact(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "test-key")
    monkeypatch.setattr(chat.httpx, "AsyncClient", FakeClient)
    store = SessionStore()
    session = store.create()
    store.append_turn(session.id, "이전 질문", "이전 답변")
    session.agent_context_id = "ctx-old"
    answer, context_id = await chat.call_agent(load_settings(), session, "후속 질문", "agent-slug", True)
    method, url, options = FakeClient.captured
    message = options["json"]["params"]["message"]
    assert method == "POST"
    assert url.endswith("/api/v1/external/agents/v2/agent-slug/a2a")
    assert options["json"]["method"] == "SendStreamingMessage"
    assert options["headers"]["Accept"] == "text/event-stream"
    assert "이전 질문" in message["parts"][0]["text"]
    assert "contextId" not in message
    assert "kind" not in message
    assert "kind" not in message["parts"][0]
    assert answer == "법령 답변"
    assert context_id == "ctx-1"
