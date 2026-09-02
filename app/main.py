from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_settings
from app.schemas import ChatRequest, TtsRequest
from app.services.chat import call_agent_v1, call_agent_v2, call_model
from app.services.stt import transcribe
from app.services.tts import iter_and_close, open_tts_stream
from app.sessions import SessionStore

load_dotenv()
settings = load_settings()
sessions = SessionStore(settings.session_ttl_seconds)
STATIC = Path(__file__).resolve().parents[1] / "static"

app = FastAPI(title="Voice Chat Server Demo", version="1.0.0", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def same_origin_and_security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"error": "교차 출처 API 요청은 허용되지 않습니다."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob: data:; connect-src 'self'; img-src 'self' data:"
    return response


@app.exception_handler(httpx.HTTPError)
async def upstream_error(_: Request, exc: httpx.HTTPError):
    from fastapi.responses import JSONResponse
    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 502
    return JSONResponse(status_code=502, content={"error": "외부 API 요청에 실패했습니다.", "upstreamStatus": status, "detail": str(exc)[:1000]})


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "voice.html")


@app.get("/voice.html", include_in_schema=False)
async def voice_page():
    return FileResponse(STATIC / "voice.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "stt": "api", "tts": "api", "activeSessions": sessions.count()}


@app.post("/api/sessions", status_code=201)
async def create_session():
    session = sessions.create()
    return {"sessionId": session.id, "turn": 0, "createdAt": session.created_at}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    session = sessions.delete(session_id)
    return {"sessionId": session_id, "ended": True, "turn": len(session.turns) // 2 if session else 0}


@app.post("/api/stt")
async def speech_to_text(
    request: Request,
    model: str = Query("whisper-large-v3", min_length=1, max_length=200),
    language: str = Query("ko", pattern="^(auto|ko|en|ja|zh)$"),
    response_format: str = Query("json", pattern="^(json|text|verbose_json)$"),
    prompt: str = Query("", max_length=1000),
):
    audio = await request.body()
    if len(audio) < 32 or len(audio) > settings.max_audio_bytes:
        raise HTTPException(400, "오디오 크기가 올바르지 않습니다.")
    started = time.perf_counter()
    try:
        result = await transcribe(settings, audio, request.headers.get("content-type", "audio/webm"), model, language, response_format, prompt)
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    result["processingMs"] = round((time.perf_counter() - started) * 1000)
    return result


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    session = sessions.get(payload.session_id)
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다. 새 세션을 시작하세요.")
    started = time.perf_counter()
    try:
        if payload.provider == "agent_v1":
            answer, chat_session_id = await call_agent_v1(
                settings, session, payload.message, payload.agent_v1_slug or settings.agent_v1_slug, payload.use_context
            )
            if chat_session_id is not None:
                session.agent_v1_chat_session_id = chat_session_id
        elif payload.provider == "agent_v2":
            answer, context_id = await call_agent_v2(
                settings, session, payload.message, payload.agent_v2_slug or settings.agent_v2_slug, payload.use_context
            )
            if context_id:
                session.agent_v2_context_id = context_id
        else:
            answer = await call_model(
                settings, session, payload.message, payload.model_name or settings.model_name,
                settings.model_system_prompt if payload.system_prompt is None else payload.system_prompt,
                payload.use_context,
            )
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    session = sessions.append_turn(session.id, payload.message, answer)
    return {"answer": answer, "turn": len(session.turns) // 2, "provider": payload.provider, "processingMs": round((time.perf_counter() - started) * 1000)}


@app.post("/api/tts")
async def text_to_speech(payload: TtsRequest = Body(...)):
    client, response = await open_tts_stream(settings, payload)
    media_type = response.headers.get("content-type", "text/event-stream" if payload.stream_format == "sse" else "audio/wav")
    headers = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
    return StreamingResponse(iter_and_close(client, response), status_code=response.status_code, media_type=media_type, headers=headers)
