import pytest

from app.config import load_settings
from app.services import stt


class FakeResponse:
    text = '{"model":"whisper-large-v3","text":"전사 결과"}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"model": "whisper-large-v3", "text": "전사 결과"}


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
async def test_stt_uses_bearer_and_multipart_file(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "test-key")
    monkeypatch.setattr(stt.httpx, "AsyncClient", FakeClient)
    result = await stt.transcribe(load_settings(), b"webm-audio", "audio/webm", "whisper-large-v3", "ko", "json", "정부24")
    url, request = FakeClient.captured
    assert url.endswith("/v1/audio/transcriptions")
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["files"]["file"][0] == "speech.webm"
    assert request["data"]["prompt"] == "정부24"
    assert result["transcript"] == "전사 결과"
