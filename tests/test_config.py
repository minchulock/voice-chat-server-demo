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


def test_voice_service_defaults(monkeypatch):
    monkeypatch.setenv("CLOVA_API_KEY", "test-key")
    monkeypatch.delenv("AGENT_SLUG", raising=False)
    monkeypatch.delenv("AGENT_V1_SLUG", raising=False)
    monkeypatch.delenv("AGENT_V2_SLUG", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("MODEL_SYSTEM_PROMPT", raising=False)
    settings = load_settings()
    assert settings.agent_v1_slug == "YAv53FJNQkST0qhoOs1H_g"
    assert settings.agent_v2_slug == "w4r7BhFhTTueoOCISFRFPg"
    assert settings.model_name == "google/gemma-4-31B-it"
    assert settings.model_system_prompt.startswith("당신은 멀티턴 음성 대화 서비스를 위한 AI 어시스턴트입니다.")
    assert "Markdown 문법을 사용하지 않습니다." in settings.model_system_prompt
