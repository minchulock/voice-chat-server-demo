#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/voice-chat-server-demo"
if [[ "${EUID}" -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo ./deploy/update.sh" >&2
  exit 1
fi

git pull --ff-only
cp -a app static deploy requirements.txt pyproject.toml "${APP_DIR}/"
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
chown -R voicechat:voicechat "${APP_DIR}"
systemctl restart voice-chat
systemctl --no-pager status voice-chat
