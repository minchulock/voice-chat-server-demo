from app.services.common import extract_text, find_nested, split_voice_reply


def test_extracts_agent_text_and_context_id():
    response = {"result": {"message": {"contextId": "ctx-1", "parts": [{"kind": "text", "text": "법령 답변"}]}}}
    assert extract_text(response) == "법령 답변"
    assert find_nested(response, "contextId") == "ctx-1"


def test_split_voice_reply_parses_json_and_code_fence():
    raw = '```json\n{"display_text":"상세 안내","speech_text":"짧은 안내"}\n```'
    assert split_voice_reply(raw) == ("상세 안내", "짧은 안내")


def test_split_voice_reply_keeps_legacy_text_compatible():
    assert split_voice_reply("기존 일반 답변") == ("기존 일반 답변", "기존 일반 답변")
