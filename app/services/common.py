from __future__ import annotations

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
