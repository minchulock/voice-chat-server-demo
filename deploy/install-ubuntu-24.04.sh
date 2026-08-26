#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo ./deploy/install-ubuntu-24.04.sh" >&2
  exit 1
fi

APP_DIR="/opt/voice-chat-server-demo"
APP_USER="voicechat"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx ca-certificates curl

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}"
cp -a app static deploy requirements.txt pyproject.toml "${APP_DIR}/"
if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp .env.example "${APP_DIR}/.env.example"
fi

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

install -m 0644 deploy/voice-chat.service /etc/systemd/system/voice-chat.service
install -m 0644 deploy/nginx.conf /etc/nginx/sites-available/voice-chat
ln -sfn /etc/nginx/sites-available/voice-chat /etc/nginx/sites-enabled/voice-chat
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl daemon-reload
systemctl enable nginx voice-chat

echo
echo "설치 완료"
echo "1. ${APP_DIR}/.env.example을 ${APP_DIR}/.env로 복사하고 API 키를 입력하세요."
echo "2. deploy/nginx.conf의 server_name을 실제 도메인으로 변경하세요."
echo "3. sudo systemctl restart nginx voice-chat"
