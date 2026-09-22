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
    assert "provider:'agent_v1'" in script
    assert "settingsRevision:4" in script
    assert "saved.settingsRevision!==DEFAULTS.settingsRevision" in script
    assert "agentV1Slug:'woLbP7utQsqiUIQtP0DMtQ'" in script
    assert "agentV2Slug:'lK5muLmzRZ2bOC9jx4JDQg'" in script
    assert "saved.provider==='agent'" in script
    assert "'w4r7BhFhTTueoOCISFRFPg','3p-wwnDkTfO4RuC-GQp_6g'" in script
    assert "agent_v1_slug:settings.agentV1Slug" in script
    assert "modelName:'google/gemma-4-31B-it'" in script
    assert "ttsSpeed:1.6" in script
    assert "voiceChatSettingsV2" in script


def test_answer_api_settings_have_strict_hidden_rule():
    stylesheet = (ROOT / "static" / "settings-fix.css").read_text(encoding="utf-8")
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    page = (ROOT / "static" / "voice.html").read_text(encoding="utf-8")
    assert "display: none !important" in stylesheet
    assert "classList.toggle('selected',input.checked)" in script
    assert 'value="agent_v1"' in page
    assert 'id="agent-v1-row"' in page
    assert 'value="agent_v2"' in page


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
    assert "copy.append(document.createTextNode(role==='assistant'?formatAssistantText(text):text))" in script
    assert "innerHTML=formatAssistantText" not in script
    assert "white-space: pre-wrap" in stylesheet
    assert 'href="/static/chat-format.css"' in page


def test_display_and_speech_channels_are_used_separately():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    assert "displayText=result.display_text||result.answer" in script
    assert "speechText=result.speech_text||displayText" in script
    assert "answerBubble=bubble('assistant',displayText)" in script
    assert "speak(speechText" in script


def test_full_answer_can_be_played_on_demand():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "static" / "chat-format.css").read_text(encoding="utf-8")
    assert "className='full-speech-button'" in script
    assert "답변 전문 듣기" in script
    assert "playFullAnswer(text,button)" in script
    assert "fullTextForSpeech(text)" in script
    assert "splitSentences(fullTextForSpeech(text))" in script
    assert "manualSpeechAbort" in script
    assert "mediaRecorder.onstop=null;await stopMedia()" in script
    assert ".full-speech-button" in stylesheet


def test_push_to_talk_and_continuous_mode_use_separate_controls():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    page = (ROOT / "static" / "voice.html").read_text(encoding="utf-8")
    assert "inputMode:'separate'" in script
    assert "PTT_HOLD_MS" not in script
    assert "beginHybridPress" not in script
    assert "endHybridPress" not in script
    assert "pressTimer" not in script
    assert "activeInputMode='auto'" in script
    assert "activeInputMode='ptt'" in script
    assert "createSession(true)" in script
    assert "addEventListener('pointerdown'" in script
    assert "addEventListener('pointerup'" in script
    assert "addEventListener('pointercancel'" in script
    assert "event.code==='Space'||event.key===' '||event.key==='Spacebar'" in script
    assert "window.addEventListener('keydown'" in script
    assert "window.addEventListener('keyup'" in script
    assert "finishOnSilence&&heardVoice" in script
    assert "monitorVad(performance.now(),true)" in script
    assert "prepareMicrophonePermission" in script
    mic_action = script.split("async function micAction", 1)[1].split("async function beginPtt", 1)[0]
    assert mic_action.index("await prepareMicrophonePermission()") < mic_action.index("await startListening(null,false,true)")
    assert "activeInputMode='idle'" in mic_action
    assert "연속 대화 버튼을 다시 누르면 시작됩니다" in mic_action
    assert "navigator.permissions" not in script
    assert "permissionStream.getTracks().forEach" in script
    assert "return false" in script
    assert "startListening(null,true,false)" in script
    assert "startListening(null,false,true)" in script
    assert 'id="input-mode"' in page
    assert 'value="separate">분리형 · 기본 PTT' in page
    assert 'id="continuous-mode"' in page
    assert 'id="end-session"' not in page
    assert 'id="voice-end"' not in page
    assert "$('#continuous-mode').addEventListener('click'" in script
    assert "toggleContinuousMode()" in script
    assert "if(sessionActive&&activeInputMode==='auto'){await endSession();return}" in script
    assert "autoActive?'대화 종료':'연속 대화'" in script
    assert "control.addEventListener('pointerdown',event=>handlePttDown(event)" in script
    assert 'class="input-guide"' not in page
    assert page.index('class="voice-dock"') < page.index('class="logs"')
    dock = page.split('class="voice-dock"', 1)[1].split('</div>', 1)[0]
    assert dock.index('id="mic"') < dock.index('id="continuous-mode"')
    assert dock.count('class="action-icon"') == 2
    assert '<svg viewBox="0 0 24 24"' in dock
    assert 'class="voice-mode-dock"' in page
    assert page.count('class="mode-icon"') == 2
    assert "syncInputGuides()" in script


def test_ptt_cancels_auto_mode_and_only_auto_mode_uses_voice_barge_in():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "static" / "chat-format.css").read_text(encoding="utf-8")
    select_ptt = script.split("function selectPttMode", 1)[1].split("async function handlePttDown", 1)[0]
    ptt_down = script.split("async function handlePttDown", 1)[1].split("async function beginPtt", 1)[0]
    play_blob = script.split("async function playBlob", 1)[1].split("async function speak", 1)[0]
    assert select_ptt.index("activeInputMode='ptt'") < select_ptt.index("clearTimeout(nextTurnTimer)")
    assert "nextTurnTimer=0" in select_ptt
    assert ptt_down.index("selectPttMode()") < ptt_down.index("if(ttsPlaying)") < ptt_down.index("if(busy||transitioning)")
    assert "stopPlayback()" in ptt_down
    assert "손을 뗀 뒤 다시 누르고 말씀하세요" in ptt_down
    assert "activeInputMode!=='auto'" in play_blob
    assert "if(!settings.bargeIn||activeInputMode!=='auto')" in play_blob
    assert ".voice-dock" in stylesheet
    assert ".voice-mode-dock" in stylesheet
    assert "box-shadow:0 9px" not in stylesheet


def test_question_guide_is_inside_empty_conversation_and_removed_on_first_message():
    script = (ROOT / "static" / "voice.js").read_text(encoding="utf-8")
    page = (ROOT / "static" / "voice.html").read_text(encoding="utf-8")
    conversation = page.split('id="conversation"', 1)[1].split('id="caption"', 1)[0]
    assert 'id="question-guide"' in conversation
    assert "function questionGuide()" in script
    assert "conversation.querySelector('.empty')?.remove()" in script
    assert "syncQuestionGuide()" in script
