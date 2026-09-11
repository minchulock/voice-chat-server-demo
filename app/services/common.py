from __future__ import annotations

import json
from typing import Any


def extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(filter(None, (extract_text(item) for item in value)))
    if not isinstance(value, dict):
        return ""
    for key in ("text", "content", "outputText"):
        text = extract_text(value.get(key))
        if text:
            return text
    for key in ("parts", "message", "messages", "artifacts", "result", "data", "choices"):
        text = extract_text(value.get(key))
        if text:
            return text
    return ""


def find_nested(value: Any, key: str) -> Any | None:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = find_nested(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_nested(child, key)
            if found is not None:
                return found
    return None


def split_voice_reply(raw: str) -> tuple[str, str]:
    """Normalize dual-channel JSON, with compatibility for legacy plain text."""
    value = raw.strip()
    candidates = [value]
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[-1].strip() == "```":
            candidates.insert(0, "\n".join(lines[1:-1]).strip())
    first, last = value.find("{"), value.rfind("}")
    if first >= 0 and last > first:
        candidates.append(value[first:last + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, str):
                payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        display = payload.get("display_text")
        speech = payload.get("speech_text")
        display_text = display.strip() if isinstance(display, str) else ""
        speech_text = speech.strip() if isinstance(speech, str) else ""
        if display_text or speech_text:
            return display_text or speech_text, speech_text or display_text
    return value, value
