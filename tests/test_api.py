from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_static_page():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["stt"] == "api"
    page = client.get("/voice.html")
    assert page.status_code == 200
    assert "CLOVA_API_KEY" not in page.text
    assert "STT API" in page.text


def test_session_create_and_delete_cycle():
    created = client.post("/api/sessions")
    assert created.status_code == 201
    session_id = created.json()["sessionId"]
    ended = client.delete(f"/api/sessions/{session_id}")
    assert ended.status_code == 200
    assert ended.json()["ended"] is True
    recreated = client.post("/api/sessions")
    assert recreated.json()["sessionId"] != session_id


def test_stt_rejects_empty_audio_before_upstream_call():
    response = client.post("/api/stt", content=b"short", headers={"Content-Type": "audio/webm"})
    assert response.status_code == 400


def test_cross_origin_api_request_is_rejected():
    response = client.get("/api/health", headers={"Origin": "https://attacker.example"})
    assert response.status_code == 403


def test_security_headers_are_present():
    response = client.get("/voice.html")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "microphone=(self)" in response.headers["permissions-policy"]
