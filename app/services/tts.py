from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.config import Settings
from app.schemas import TtsRequest


async def open_tts_stream(settings: Settings, payload: TtsRequest) -> tuple[httpx.AsyncClient, httpx.Response]:
    client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    request = client.build_request(
        "POST",
        settings.tts_url,
        headers={"Authorization": settings.authorization, "Content-Type": "application/json"},
        json=payload.model_dump(),
    )
    response = await client.send(request, stream=True)
    if response.is_error:
        detail = (await response.aread()).decode(errors="replace")[:1000]
        await response.aclose()
        await client.aclose()
        raise httpx.HTTPStatusError(detail, request=request, response=response)
    return client, response


async def iter_and_close(client: httpx.AsyncClient, response: httpx.Response) -> AsyncIterator[bytes]:
    try:
        async for chunk in response.aiter_bytes():
            if chunk:
                yield chunk
    finally:
        await response.aclose()
        await client.aclose()
