from __future__ import annotations

import httpx

from app.config import Settings
from app.services.common import extract_text


EXTENSIONS = {"audio/wav": "wav", "audio/webm": "webm", "audio/mp4": "m4a", "audio/mpeg": "mp3", "audio/ogg": "ogg"}


async def transcribe(
    settings: Settings,
    audio: bytes,
    content_type: str,
    model: str,
    language: str,
    response_format: str,
    prompt: str,
) -> dict[str, object]:
    mime = content_type.split(";", 1)[0].lower()
    extension = EXTENSIONS.get(mime, "wav")
    data = {"model": model, "response_format": response_format}
    if language and language != "auto":
        data["language"] = language
    if prompt:
        data["prompt"] = prompt
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            settings.stt_url,
            headers={"Authorization": settings.authorization},
            data=data,
            files={"file": (f"speech.{extension}", audio, mime)},
        )
        response.raise_for_status()
    result: object = response.text if response_format == "text" else response.json()
    transcript = extract_text(result)
    if not transcript:
        raise ValueError("STT API 응답에서 전사문을 찾지 못했습니다.")
    result_model = result.get("model", model) if isinstance(result, dict) else model
    return {"transcript": transcript, "model": result_model}
