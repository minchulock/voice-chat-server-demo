from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_client_does_not_contain_authorization_or_env_key():
    client = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "static").glob("*.*"))
    assert "CLOVA_API_KEY" not in client
    assert "Authorization: Bearer" not in client


def test_no_local_model_runtime_is_shipped():
    names = {path.name for path in ROOT.rglob("*")}
    assert "setup_local_model.sh" not in names
    assert "start_local_model.sh" not in names
    assert "local_models" not in names


def test_browser_defaults_match_server_defaults():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    assert "agentSlug:'Dyyn7G5jTCapQqsXAIoVxg'" in script
    assert "modelName:'google/gemma-4-31B-it'" in script
    assert "ttsSpeed:1.6" in script
    assert "voiceChatSettingsV2" in script


def test_answer_api_settings_have_strict_hidden_rule():
    stylesheet = (ROOT / "static" / "settings-fix.css").read_text(encoding="utf-8")
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    assert "display: none !important" in stylesheet
    assert "classList.toggle('selected',input.checked)" in script


def test_barge_in_monitor_is_ready_before_tts_playback():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    play_blob = script.split("async function playBlob", 1)[1].split("async function speak", 1)[0]
    assert play_blob.index("getUserMedia") < play_blob.rindex("await audio.play()")
    assert "await ctx.resume()" in play_blob
    assert "settings.vadThreshold*.75" in play_blob
    assert "warming=now-began<=250" in play_blob
    assert "voiceSince&&now-voiceSince>160" in play_blob
