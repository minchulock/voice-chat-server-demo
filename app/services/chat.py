from __future__ import annotations

import json
import uuid

import httpx

from app.config import Settings
from app.services.common import extract_text, find_nested
from app.sessions import Session


def _agent_message(session: Session, message: str, use_context: bool) -> str:
    agent_message = message
    if use_context and session.turns:
        history = "\n".join(
            f"{'사용자' if item['role'] == 'user' else '어시스턴트'}: {item['content']}" for item in session.turns[-8:]
        )
        agent_message = f"이전 대화:\n{history}\n\n현재 사용자 질문: {message}"
    return agent_message


async def call_agent_v1(settings: Settings, session: Session, message: str, slug: str, use_context: bool) -> tuple[str, int | None]:
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
    body = {
        "jsonrpc": "2.0",
        "id": f"request-{uuid.uuid4().hex[:8]}",
        "method": "SendStreamingMessage",
        "params": {"message": {"messageId": f"msg-{uuid.uuid4().hex[:8]}", "role": "user", "parts": [{"text": agent_message}] }},
    }
    answer = ""
    context_id: str | None = None
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
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
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
                update = result.get("artifactUpdate")
                if not isinstance(update, dict):
                    continue
                artifact = update.get("artifact", {})
                parts = artifact.get("parts", []) if isinstance(artifact, dict) else []
                text = "".join(
                    str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text")
                ).strip()
                if text:
                    answer = text
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
