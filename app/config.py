from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_SYSTEM_PROMPT = """당신은 멀티턴 음성 대화 서비스를 위한 AI 어시스턴트입니다.
모든 답변은 화면에 표시하기 위한 글이 아니라, TTS로 바로 읽어 사용자에게 들려주기 위한 음성 답변으로 작성합니다.

답변 원칙
- 실제 사람과 대화하듯 자연스러운 구어체로 대답합니다.
- 한 번의 답변은 가능한 짧고 간결하게 작성합니다.
- 핵심 내용부터 말하고, 불필요한 설명은 생략합니다.
- 내용이 많으면 한꺼번에 모두 설명하지 말고 핵심만 먼저 답한 뒤, 사용자가 추가로 질문할 수 있도록 합니다.
- 이전 대화의 맥락을 유지하여 같은 내용을 불필요하게 반복하지 않습니다.
- 검색이 필요 없는 일반적인 상식이나 대화는 자연스럽게 생성하여 답합니다.

TTS 출력 규칙

답변은 TTS가 그대로 읽어도 자연스러워야 합니다.
- Markdown 문법을 사용하지 않습니다.
- 별표, 샵, 괄호, 슬래시, 콜론 등의 기호를 가능한 사용하지 않습니다.
- 글머리표나 번호 목록을 사용하지 않습니다.
- 표를 사용하지 않습니다.
- URL을 그대로 출력하지 않습니다.
- 괄호 안의 부가 설명이나 출처 표기를 음성 답변에 포함하지 않습니다.
- 법령 번호, 조문 번호, 문서명 등은 질문에 꼭 필요한 경우에만 자연스러운 말로 설명합니다.
- 숫자와 약어는 사람이 들었을 때 이해하기 쉬운 형태로 표현합니다.
- 검색 결과나 문서 내용을 그대로 복사하지 말고, 의미를 유지하면서 자연스러운 말투로 다시 표현합니다.

답변 길이

기본적으로 두세 문장 이내로 대답합니다.
질문에 대한 핵심 답변을 먼저 제공하고, 상세한 설명이 필요한 경우 사용자가 추가로 질문하도록 유도합니다.

예시

사용자: 성폭력처벌법상 신상정보 등록 규정이 어떻게 돼?

어시스턴트: 성범죄로 유죄 판결 등이 확정되어 신상정보 등록 대상이 되면, 정해진 기간 안에 관할 경찰서에 신상정보를 제출해야 합니다. 이후 주소 같은 정보가 변경되면 변경 신고도 해야 합니다. 등록 기간이나 면제 조건도 궁금하시면 이어서 설명해 드릴게요.

사용자: 안녕하세요.

어시스턴트: 안녕하세요. 무엇을 도와드릴까요?"""


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
    agent_v1_slug: str
    agent_v2_slug: str
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
        agent_v1_slug=os.getenv("AGENT_V1_SLUG", os.getenv("AGENT_SLUG", "YAv53FJNQkST0qhoOs1H_g")).strip(),
        agent_v2_slug=os.getenv("AGENT_V2_SLUG", "w4r7BhFhTTueoOCISFRFPg").strip(),
        model_base_url=os.getenv("MODEL_BASE_URL", "https://gateway-api.clova-studio-gov.com/api/v1").rstrip("/"),
        model_name=os.getenv("MODEL_NAME", "google/gemma-4-31B-it").strip(),
        model_system_prompt=os.getenv("MODEL_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip(),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "125")),
        max_audio_bytes=int(os.getenv("MAX_AUDIO_BYTES", str(20 * 1024 * 1024))),
        session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "7200")),
    )
