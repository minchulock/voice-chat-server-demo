from app.config import load_settings


def test_bearer_prefix_is_normalized(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "Bearer test-key")
    assert load_settings().authorization == "Bearer test-key"


def test_default_urls_are_remote_api_urls(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "test-key")
    settings = load_settings()
    assert settings.stt_url.startswith("https://")
    assert settings.tts_url.startswith("https://")
    assert "127.0.0.1" not in settings.stt_url + settings.tts_url
