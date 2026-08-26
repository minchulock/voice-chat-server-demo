from app.services.common import extract_text, find_nested


def test_extracts_agent_text_and_context_id():
    response = {"result": {"message": {"contextId": "ctx-1", "parts": [{"kind": "text", "text": "법령 답변"}]}}}
    assert extract_text(response) == "법령 답변"
    assert find_nested(response, "contextId") == "ctx-1"
