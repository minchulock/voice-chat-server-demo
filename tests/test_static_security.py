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
    assert "agentV1Slug:'YAv53FJNQkST0qhoOs1H_g'" in script
    assert "agentV2Slug:'w4r7BhFhTTueoOCISFRFPg'" in script
    assert "if(saved.provider==='agent')saved.provider='agent_v1'" in script
    assert "if(saved.agentSlug&&!saved.agentV1Slug)saved.agentV1Slug=saved.agentSlug" in script
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
    assert "bargeRecorder.start(100);await recorderStarted" in play_blob
    assert "while(preRoll.length>6)preRoll.shift()" in play_blob
    assert "adoptBargeIn(monitorStream,ctx,probe,bargeRecorder,preRoll,myGeneration)" in play_blob


def test_listening_ui_waits_until_media_recorder_has_started():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    start_listening = script.split("async function startListening", 1)[1].split("function finishListening", 1)[0]
    assert start_listening.index("recorder.start(100);await started") < start_listening.index("title.textContent='듣고 있어요'")


def test_spring_guide_uses_csp_compatible_external_css_and_is_deployed():
    guide = (ROOT / "docs" / "spring-boot-voice-chat-guide.html").read_text(encoding="utf-8")
    stylesheet = ROOT / "docs" / "spring-boot-voice-chat-guide.css"
    install_script = (ROOT / "deploy" / "install-ubuntu-24.04.sh").read_text(encoding="utf-8")
    update_script = (ROOT / "deploy" / "update.sh").read_text(encoding="utf-8")
    assert 'href="spring-boot-voice-chat-guide.css"' in guide
    assert stylesheet.stat().st_size > 1_000
    assert "docs/spring-boot-voice-chat-guide.html" in install_script
    assert "docs/spring-boot-voice-chat-guide.css" in install_script
    assert "docs/spring-boot-voice-chat-guide.html" in update_script
    assert "docs/spring-boot-voice-chat-guide.css" in update_script


def test_stt_error_uses_friendly_ui_message_but_logs_original_error():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    assert "일시적 오류 또는 짧은 발화로 인식되지 않았습니다. 다시 시도 부탁드립니다." in script
    assert "log('ERROR',error.message,failedStage||'turn',true)" in script


def test_assistant_markdown_like_text_is_rendered_with_safe_line_breaks():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "static" / "chat-format.css").read_text(encoding="utf-8")
    page = (ROOT / "static" / "voice.html").read_text(encoding="utf-8")
    assert "function formatAssistantText" in script
    assert "document.createTextNode(role==='assistant'?formatAssistantText(text):text)" in script
    assert "innerHTML=formatAssistantText" not in script
    assert "white-space: pre-wrap" in stylesheet
    assert 'href="/static/chat-format.css"' in page
