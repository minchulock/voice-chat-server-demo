# VOICE24 AI — Server–Client Voice Chat Demo

CLOVA Studio GOV의 STT API, Agent v2 API(A2A 1.0) 또는 Model API, Streaming TTS API를 연결한 브라우저 음성 챗봇 데모입니다.

이 저장소에는 로컬 AI 모델, 모델 가중치, MLX, Ollama, Whisper 서버, 로컬 TTS 서버가 포함되지 않습니다. 브라우저는 마이크·VAD·오디오 재생을 담당하고 API 키가 필요한 모든 요청은 FastAPI 서버가 처리합니다.

## 아키텍처

```text
Browser
  Mic → VAD → in-memory audio
                    │ HTTPS
                    ▼
Nginx → FastAPI/Uvicorn
          ├─ STT API /v1/audio/transcriptions
          ├─ Agent A2A 또는 Model Chat Completions
          └─ TTS API /v1/audio/speech
                    │
                    ▼
Browser ← sentence prefetch audio/SSE ← Speaker
```

원격 서버에서 마이크를 사용하려면 HTTPS가 필요합니다. `localhost`는 브라우저가 예외적으로 안전한 컨텍스트로 취급하지만, IP 주소나 일반 HTTP 도메인에서는 마이크 권한이 차단될 수 있습니다.

## 주요 기능

- 브라우저 VAD 기반 자동 발화 종료
- WAV 파일을 디스크에 저장하지 않는 메모리 오디오 전송
- CLOVA STT API 동기 전사
- Agent v2 API(A2A 1.0)/Model API 선택
- Agent 응답 대기 애니메이션
- Session 기반 멀티턴 문맥
- Model API 시스템 프롬프트
- TTS API `audio`/`sse` 선택
- 답변 문장 분할과 한 문장 선행 합성
- TTS 재생 중 발화 인터럽트
- Turn 종료 후 자동 Listening
- 실시간 API·스트리밍 로그

## 로컬 개발

### 요구사항

- Python 3.11 이상
- HTTPS API에 연결 가능한 네트워크
- 마이크가 있는 최신 Safari, Chrome 또는 Edge

```bash
git clone https://github.com/minchulock/voice-chat-server-demo.git
cd voice-chat-server-demo

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
```

`.env`에서 실제 API 키와 필요한 URL을 설정합니다.

```dotenv
CLOVA_API_KEY=실제_API_KEY
STT_API_URL=https://gateway-api.clova-studio-gov.com/v1/audio/transcriptions
TTS_API_URL=https://gateway-api.clova-studio-gov.com/v1/audio/speech
AGENT_BASE_URL=https://gateway-api.clova-studio-gov.com
AGENT_SLUG=w4r7BhFhTTueoOCISFRFPg
MODEL_BASE_URL=https://gateway-api.clova-studio-gov.com/api/v1
MODEL_NAME=google/gemma-4-31B-it
```

서버를 실행합니다.

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

<http://localhost:8000/voice.html>을 열고 마이크 권한을 허용합니다.

## Ubuntu 24.04 서버 배포

### 1. 저장소 내려받기

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/minchulock/voice-chat-server-demo.git
cd voice-chat-server-demo
```

### 2. 애플리케이션 설치

```bash
chmod +x deploy/install-ubuntu-24.04.sh deploy/update.sh
sudo ./deploy/install-ubuntu-24.04.sh
```

설치 스크립트는 다음 항목을 구성합니다.

- `/opt/voice-chat-server-demo`
- 전용 시스템 계정 `voicechat`
- Python 가상환경과 의존성
- systemd `voice-chat.service`
- Nginx reverse proxy

### 3. 비밀 환경변수 설정

```bash
sudo cp /opt/voice-chat-server-demo/.env.example /opt/voice-chat-server-demo/.env
sudo chmod 600 /opt/voice-chat-server-demo/.env
sudo vi /opt/voice-chat-server-demo/.env
sudo chown voicechat:voicechat /opt/voice-chat-server-demo/.env
```

`.env`는 `.gitignore`에 포함되어 있습니다. 실제 API 키를 Git에 커밋하지 마세요.

### 4. Nginx 도메인 설정

```bash
sudo vi /etc/nginx/sites-available/voice-chat
```

`server_name voice.example.go.kr;`을 실제 도메인으로 변경합니다.

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 5. HTTPS 인증서

DNS가 서버를 가리킨 다음 Certbot을 설치합니다.

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d voice.example.go.kr
sudo certbot renew --dry-run
```

HTTPS 적용 전에는 원격 브라우저에서 마이크가 동작하지 않을 수 있습니다.

### 6. WAS 실행

```bash
sudo systemctl start voice-chat
sudo systemctl status voice-chat
curl http://127.0.0.1:8000/api/health
```

외부에서는 다음 주소를 확인합니다.

```bash
curl https://voice.example.go.kr/api/health
```

## 업데이트

저장소에서 최신 코드를 받은 뒤 배포 파일을 반영합니다.

```bash
cd voice-chat-server-demo
git pull --ff-only
sudo ./deploy/update.sh
```

기존 서버의 `.env` 값은 코드 기본값보다 우선합니다. 이번 기본 설정을 기존 배포에도 적용하려면 다음 값을 수정하고, `MODEL_SYSTEM_PROMPT`를 제거하거나 새 프롬프트로 교체하세요.

```dotenv
AGENT_SLUG=w4r7BhFhTTueoOCISFRFPg
MODEL_NAME=google/gemma-4-31B-it
```

```bash
sudo systemctl restart voice-chat
```

## NCP VPC 최소 방화벽 규칙

아래 규칙은 NAVER Cloud Platform VPC에서 Public IP가 할당된 Ubuntu 서버가 Nginx로 `80/443` 요청을 직접 받고, Uvicorn은 `127.0.0.1:8000`에서만 실행되는 구성을 기준으로 합니다. Load Balancer를 사용하는 경우에는 서버의 접근 소스를 `0.0.0.0/0` 대신 Load Balancer 대역 또는 ACG로 제한해야 합니다.

### 1. ACG 최소 규칙

ACG는 서버 단위의 stateful 방화벽입니다. 허용된 연결의 응답 트래픽은 자동 허용되므로 응답용 ephemeral port 규칙은 필요하지 않습니다. 다만 서버가 CLOVA API 등에 새 요청을 보내려면 Outbound 규칙이 있어야 합니다.

#### Inbound

| Protocol | 접근 소스 | 허용 포트 | 용도 |
|---|---|---:|---|
| TCP | `0.0.0.0/0` | `443` | 음성 챗봇 HTTPS 접속 |
| TCP | `0.0.0.0/0` | `80` | HTTPS redirect 및 인증서 발급·갱신 |
| TCP | `관리자_공인_IP/32` | `22` | SSH 관리 |

`22`번 포트는 반드시 관리자의 고정 공인 IP로 제한합니다. HTTP를 사용하지 않고 인증서를 DNS 방식으로 관리한다면 `80`번 규칙은 제거할 수 있습니다.

#### Outbound

| Protocol | 목적지 | 허용 포트 | 용도 |
|---|---|---:|---|
| TCP | `0.0.0.0/0` | `443` | CLOVA API, GitHub 및 HTTPS 저장소 |
| TCP | `0.0.0.0/0` | `80` | Ubuntu 패키지 및 일부 HTTP 저장소 |
| UDP | `169.254.169.53/32` | `53` | NCP VPC DNS |
| UDP | `169.254.169.54/32` | `53` | NCP VPC 보조 DNS |
| TCP | `169.254.169.53/32` | `53` | DNS TCP fallback |
| TCP | `169.254.169.54/32` | `53` | DNS TCP fallback |

ACG에서 link-local DNS 주소를 목적지로 입력할 수 없다면 DNS 규칙에 한해 `0.0.0.0/0`의 TCP/UDP `53`을 허용합니다. 자세한 동작은 [NCP ACG 가이드](https://guide.ncloud-docs.com/docs/server-acg-vpc)와 [NCP DNS 점검 가이드](https://guide.ncloud-docs.com/docs/server-ts-dns-vpc)를 참고하세요.

### 2. Network ACL 최소 규칙

Network ACL은 Subnet 단위의 stateless 방화벽이므로 요청과 응답을 양방향으로 각각 허용해야 합니다. 아래 ALLOW 규칙은 전체 차단 규칙보다 높은 우선순위에 배치합니다.

#### Inbound ALLOW

| 우선순위 예시 | Protocol | 접근 소스 | 허용 포트 | 용도 |
|---:|---|---|---:|---|
| `10` | TCP | `0.0.0.0/0` | `443` | HTTPS 요청 |
| `20` | TCP | `0.0.0.0/0` | `80` | HTTP 요청 |
| `30` | TCP | `관리자_공인_IP/32` | `22` | SSH 요청 |
| `40` | TCP | `0.0.0.0/0` | `32768-65535` | 서버가 외부로 시작한 연결의 응답 |

#### Outbound ALLOW

| 우선순위 예시 | Protocol | 목적지 | 허용 포트 | 용도 |
|---:|---|---|---:|---|
| `10` | TCP | `0.0.0.0/0` | `443` | CLOVA API, GitHub 및 HTTPS 저장소 |
| `20` | TCP | `0.0.0.0/0` | `80` | Ubuntu 패키지 및 HTTP 저장소 |
| `30` | TCP | `0.0.0.0/0` | `32768-65535` | 웹·SSH 클라이언트에 대한 응답 |
| `40` | UDP | NCP DNS IP | `53` | DNS 질의 |
| `50` | TCP | NCP DNS IP | `53` | DNS TCP fallback |

필요한 ALLOW 규칙 뒤에는 다음과 같이 나머지 트래픽을 차단할 수 있습니다.

| 우선순위 예시 | Protocol | 접근 소스/목적지 | 포트 | 동작 |
|---:|---|---|---:|---|
| `197` | TCP | `0.0.0.0/0` | `1-65535` | DENY |
| `198` | UDP | `0.0.0.0/0` | `1-65535` | DENY |
| `199` | ICMP | `0.0.0.0/0` | 전체 | DENY |

Nginx와 Uvicorn 사이의 `127.0.0.1:8000` 통신은 서버 내부 loopback이므로 ACG 및 Network ACL에 `8000`번 포트를 열지 않습니다. 자세한 차이는 [NCP Network ACL 가이드](https://guide.ncloud-docs.com/docs/en/vpc-nacl-vpc)를 참고하세요.

## 로그와 장애 진단

```bash
sudo journalctl -u voice-chat -f
sudo journalctl -u nginx -f
sudo nginx -t
sudo systemctl status voice-chat nginx
```

브라우저 마이크가 열리지 않는 경우:

1. 접속 주소가 HTTPS인지 확인합니다.
2. 브라우저 사이트 설정에서 마이크 권한을 확인합니다.
3. 다른 앱이 마이크를 독점하고 있지 않은지 확인합니다.

API 요청이 실패하는 경우:

1. `/opt/voice-chat-server-demo/.env`의 키와 URL을 확인합니다.
2. 서버에서 외부 API 도메인의 443 포트로 연결 가능한지 확인합니다.
3. `journalctl -u voice-chat`에서 upstream 상태 코드를 확인합니다.

## API

Java/Spring Boot로 동일 구조를 재구현하려면 [Spring Boot 음성 대화 서비스 구현 가이드](docs/spring-boot-voice-chat-guide.html)를 참고하세요. 브라우저 VAD, 메모리 오디오 전송, WebFlux 스트림 프록시, 문장 단위 TTS 선행 합성, SSE 및 발화 인터럽트 예제를 포함합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/health` | 서버 상태 |
| POST | `/api/sessions` | Session 생성 |
| DELETE | `/api/sessions/{id}` | Session 종료 |
| POST | `/api/stt` | 오디오 바이너리 전사 |
| POST | `/api/chat` | Agent/Model 답변 생성 |
| POST | `/api/tts` | TTS 스트림 프록시 |

## 세션 운영 주의사항

데모는 Session을 프로세스 메모리에 보관하므로 Uvicorn worker를 1개로 실행합니다. 서버 재시작 시 Session은 초기화됩니다. 다중 worker나 여러 서버 인스턴스가 필요한 운영 환경에서는 `app/sessions.py`를 Redis 저장소로 교체하세요.

## 보안

- API 키는 `.env`에서만 읽고 브라우저에 전달하지 않습니다.
- `.env`와 로그 파일은 Git에서 제외됩니다.
- STT 업로드 크기는 기본 20MB로 제한됩니다.
- API 입력 길이와 모델·slug 값을 검증합니다.
- 브라우저 API 요청은 same-origin으로 제한하고 Nginx에서 IP별 속도를 제한합니다.
- Nginx와 Uvicorn은 외부 스트리밍을 위해 buffering을 비활성화합니다.
- 공개 저장소 커밋 전에 다음 검사를 권장합니다.

```bash
git grep -nE '(Bearer [A-Za-z0-9._-]{16,}|CLOVA_API_KEY=.+)' -- ':!README.md' ':!.env.example'
git status --short
```

## 테스트

```bash
source .venv/bin/activate
pytest -q
python -m compileall -q app
```

실제 API를 호출하는 종단 테스트는 비용과 음성 전송이 발생하므로 기본 테스트에는 포함하지 않습니다.

## 지원 OS

기본 배포 대상은 Ubuntu 24.04 LTS입니다. Rocky Linux 9.8도 FastAPI 애플리케이션 자체는 실행할 수 있지만, 제공되는 자동 설치 스크립트와 Nginx 경로는 Ubuntu 기준입니다.
