from __future__ import annotations

import os
from dataclasses import dataclass


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value == "YOUR_API_KEY_HERE":
        raise RuntimeError(f"필수 환경변수 {name}가 설정되지 않았습니다.")
    return value


@dataclass(frozen=True)
class Settings:
    api_key: str
    stt_url: str
    tts_url: str
    agent_base_url: str
    agent_slug: str
    model_base_url: str
    model_name: str
    model_system_prompt: str
    request_timeout_seconds: float
    max_audio_bytes: int
    session_ttl_seconds: int

    @property
    def authorization(self) -> str:
        key = self.api_key[7:].strip() if self.api_key.lower().startswith("bearer ") else self.api_key
        return f"Bearer {key}"


def load_settings() -> Settings:
    return Settings(
        api_key=_required("CLOVA_API_KEY"),
        stt_url=os.getenv("STT_API_URL", "https://gateway-api.clova-studio-gov.com/v1/audio/transcriptions").strip(),
        tts_url=os.getenv("TTS_API_URL", "https://gateway-api.clova-studio-gov.com/v1/audio/speech").strip(),
        agent_base_url=os.getenv("AGENT_BASE_URL", "https://gateway-api.clova-studio-gov.com").rstrip("/"),
        agent_slug=os.getenv("AGENT_SLUG", "vcNrFIgDTM6Sala0kkwkfg").strip(),
        model_base_url=os.getenv("MODEL_BASE_URL", "https://gateway-api.clova-studio-gov.com/api/v1").rstrip("/"),
        model_name=os.getenv("MODEL_NAME", "HCX-GOV-THINK").strip(),
        model_system_prompt=os.getenv("MODEL_SYSTEM_PROMPT", "당신은 친절한 AI 어시스턴트입니다.").strip(),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "125")),
        max_audio_bytes=int(os.getenv("MAX_AUDIO_BYTES", str(20 * 1024 * 1024))),
        session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "7200")),
    )
