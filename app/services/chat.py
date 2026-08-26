from __future__ import annotations

import json
import uuid

import httpx

from app.config import Settings
from app.services.common import extract_text, find_nested
from app.sessions import Session


async def call_agent(settings: Settings, session: Session, message: str, slug: str, use_context: bool) -> tuple[str, str | None]:
    agent_message = message
    if use_context and session.turns:
        history = "\n".join(
            f"{'사용자' if item['role'] == 'user' else '어시스턴트'}: {item['content']}" for item in session.turns[-8:]
        )
        agent_message = f"이전 대화:\n{history}\n\n현재 사용자 질문: {message}"
    body = {
        "jsonrpc": "2.0",
        "id": f"request-{uuid.uuid4().hex[:8]}",
        "method": "message/send",
        "params": {"message": {"kind": "message", "messageId": f"msg-{uuid.uuid4().hex[:8]}", "role": "user", "parts": [{"kind": "text", "text": agent_message}] }},
    }
    if session.agent_context_id:
        body["params"]["message"]["contextId"] = session.agent_context_id
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            f"{settings.agent_base_url}/api/v1/external/agents/{slug}/a2a",
            headers={"Authorization": settings.authorization, "Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        result = response.json()
    answer = extract_text(result)
    if not answer:
        raise ValueError("Agent API 응답에서 답변을 찾지 못했습니다.")
    context_id = find_nested(result, "contextId")
    return answer, str(context_id) if context_id else None


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
