from __future__ import annotations

import json
import logging
import time
import uuid

import httpx

from app.config import Settings
from app.services.common import extract_text, find_nested
from app.sessions import Session

logger = logging.getLogger("uvicorn.error")


def _agent_message(session: Session, message: str, use_context: bool) -> str:
    agent_message = message
    if use_context and session.turns:
        history = "\n".join(
            f"{'사용자' if item['role'] == 'user' else '어시스턴트'}: {item['content']}" for item in session.turns[-8:]
        )
        agent_message = f"이전 대화:\n{history}\n\n현재 사용자 질문: {message}"
    return agent_message


async def call_agent_v1(
    settings: Settings, session: Session, message: str, slug: str, use_context: bool
) -> tuple[str, int | None]:
    body = {
        "jsonrpc": "2.0",
        "id": f"request-{uuid.uuid4().hex[:8]}",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": f"msg-{uuid.uuid4().hex[:8]}",
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
            }
        },
    }
    if use_context and session.agent_v1_chat_session_id is not None:
        body["params"]["metadata"] = {"chat_session_id": session.agent_v1_chat_session_id}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            f"{settings.agent_base_url}/api/v1/external/agents/{slug}/a2a",
            headers={"Authorization": settings.authorization, "Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
    if error := data.get("error"):
        detail = error.get("message") or error.get("data", {}).get("detail") or "Agent v1 요청에 실패했습니다."
        raise ValueError(str(detail))
    result = data.get("result", {})
    answer = extract_text(result.get("message", {})).strip() if isinstance(result, dict) else ""
    if not answer:
        answer = extract_text(result).strip()
    if not answer:
        raise ValueError("Agent v1 응답에서 답변을 찾지 못했습니다.")
    chat_session_id = find_nested(data, "chat_session_id")
    try:
        parsed_session_id = int(chat_session_id) if chat_session_id is not None else None
    except (TypeError, ValueError):
        parsed_session_id = None
    return answer, parsed_session_id


async def call_agent_v2(settings: Settings, session: Session, message: str, slug: str, use_context: bool) -> tuple[str, str | None]:
    agent_message = _agent_message(session, message, use_context)
    request_id = f"request-{uuid.uuid4().hex[:8]}"
    body = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "SendStreamingMessage",
        "params": {"message": {"messageId": f"msg-{uuid.uuid4().hex[:8]}", "role": "user", "parts": [{"text": agent_message}] }},
    }
    answer = ""
    context_id: str | None = None
    started = time.perf_counter()
    first_event_ms: int | None = None
    first_text_ms: int | None = None
    last_chunk_ms: int | None = None
    completed_ms: int | None = None
    end_reason = "error"

    def elapsed_ms() -> int:
        return round((time.perf_counter() - started) * 1000)

    logger.info("AGENT_V2_SSE milestone=request_start elapsed_ms=0 request_id=%s", request_id)
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{settings.agent_base_url}/api/v1/external/agents/v2/{slug}/a2a",
                headers={
                    "Authorization": settings.authorization,
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=body,
            ) as response:
                response.raise_for_status()
                end_reason = "eof"
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    if first_event_ms is None:
                        first_event_ms = elapsed_ms()
                        logger.info(
                            "AGENT_V2_SSE milestone=first_event elapsed_ms=%d request_id=%s",
                            first_event_ms, request_id,
                        )
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if error := event.get("error"):
                        detail = error.get("message") or error.get("data", {}).get("detail") or "Agent v2 요청에 실패했습니다."
                        raise ValueError(str(detail))
                    result = event.get("result", {})
                    if found_context := find_nested(result, "contextId"):
                        context_id = str(found_context)
                    completed = find_nested(result, "state") == "TASK_STATE_COMPLETED"
                    update = result.get("artifactUpdate")
                    if isinstance(update, dict):
                        artifact = update.get("artifact", {})
                        parts = artifact.get("parts", []) if isinstance(artifact, dict) else []
                        text = "".join(
                            str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text")
                        ).strip()
                        if text:
                            answer = text
                            if first_text_ms is None:
                                first_text_ms = elapsed_ms()
                                logger.info(
                                    "AGENT_V2_SSE milestone=first_text elapsed_ms=%d request_id=%s",
                                    first_text_ms, request_id,
                                )
                        if update.get("lastChunk") is True:
                            last_chunk_ms = elapsed_ms()
                            logger.info(
                                "AGENT_V2_SSE milestone=last_chunk elapsed_ms=%d answer_found=%s request_id=%s",
                                last_chunk_ms, bool(answer), request_id,
                            )
                            if answer:
                                end_reason = "last_chunk"
                                break
                    if completed:
                        completed_ms = elapsed_ms()
                        logger.info(
                            "AGENT_V2_SSE milestone=completed elapsed_ms=%d answer_found=%s request_id=%s",
                            completed_ms, bool(answer), request_id,
                        )
                        end_reason = "completed"
                        break
    finally:
        logger.info(
            "AGENT_V2_SSE milestone=stream_end elapsed_ms=%d reason=%s answer_found=%s first_event_ms=%s first_text_ms=%s last_chunk_ms=%s completed_ms=%s request_id=%s",
            elapsed_ms(), end_reason, bool(answer), first_event_ms, first_text_ms, last_chunk_ms, completed_ms, request_id,
        )
    if not answer:
        raise ValueError("Agent v2 SSE 응답에서 최종 artifactUpdate 답변을 찾지 못했습니다.")
    return answer, context_id


async def call_model(
    settings: Settings,
    session: Session,
    message: str,
    model_name: str,
    system_prompt: str,
    use_context: bool,
) -> str:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if use_context:
        messages.extend(session.turns)
    messages.append({"role": "user", "content": message})
    payload = {"model": model_name, "messages": messages, "stream": True}
    parts: list[str] = []
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        async with client.stream(
            "POST",
            f"{settings.model_base_url}/chat/completions",
            headers={"Authorization": settings.authorization, "Content-Type": "application/json"},
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                    content = event["choices"][0]["delta"].get("content")
                    if content:
                        parts.append(content)
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
    answer = "".join(parts).strip()
    if not answer:
        raise ValueError("Model API 응답에서 답변을 찾지 못했습니다.")
    return answer
