from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=100)
    message: str = Field(min_length=1, max_length=4000)
    provider: Literal["agent", "model"] = "agent"
    use_context: bool = True
    agent_slug: str | None = Field(default=None, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")
    model_name: str | None = Field(default=None, max_length=200, pattern=r"^[A-Za-z0-9._:/-]+$")
    system_prompt: str | None = Field(default=None, max_length=8000)


class TtsRequest(BaseModel):
    input: str = Field(min_length=1, max_length=4096)
    model: str = Field(default="melo-tts-ko", min_length=1, max_length=200)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    stream_format: Literal["audio", "sse"] = "sse"
