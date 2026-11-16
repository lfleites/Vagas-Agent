#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================"
echo "  Agente de Vagas (Gupy + Telegram)"
echo "============================================"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado. Instale o Docker antes de continuar."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose não encontrado. Use uma versão do Docker que tenha 'docker compose'."
  exit 1
fi

mkdir -p data

if [[ -f .env ]]; then
  read -r -p "Já existe um .env. Substituir token e chat ID? [s/N]: " REPLACE
  REPLACE="${REPLACE:-N}"
else
  REPLACE="s"
fi

if [[ "${REPLACE,,}" == "s" || "${REPLACE,,}" == "sim" ]]; then
  echo
  echo "1. Fale com @BotFather no Telegram e crie um bot (/newbot)"
  echo "2. Copie o token"
  echo "3. Envie qualquer mensagem para o bot"
  echo "4. Abra https://api.telegram.org/bot<SEU_TOKEN>/getUpdates"
  echo "   e copie o número em \"chat\":{\"id\":...}"
  echo
  read -r -p "Token do Telegram: " TELEGRAM_TOKEN
  read -r -p "Chat ID: " TELEGRAM_CHAT_ID

  if [[ -z "${TELEGRAM_TOKEN}" || -z "${TELEGRAM_CHAT_ID}" ]]; then
    echo "Token e chat ID são obrigatórios."
    exit 1
  fi

  umask 077
  cat > .env << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
EOF
  chmod 600 .env
  echo ".env gravado. Ele não vai para o GitHub."
fi

echo
echo "Os filtros de título ficam em filtros.txt. Edite esse arquivo para a sua área."
echo "A busca da Gupy está em app.py: termo Suporte, só vagas remotas."
echo
echo "Construindo a imagem Docker. A primeira vez demora alguns minutos."
docker compose build

echo
read -r -p "Executar uma busca agora? [s/N]: " RUN_NOW
RUN_NOW="${RUN_NOW:-N}"
if [[ "${RUN_NOW,,}" == "s" || "${RUN_NOW,,}" == "sim" ]]; then
  docker compose run --rm vagas-agent
fi

echo
read -r -p "Agendar a cada 5 horas e na inicialização? [s/N]: " SETUP_CRON
SETUP_CRON="${SETUP_CRON:-N}"
if [[ "${SETUP_CRON,,}" == "s" || "${SETUP_CRON,,}" == "sim" ]]; then
  DOCKER="$(command -v docker)"
  INSTALL_DIR="$(pwd)"
  CRON_LINE="0 */5 * * * cd ${INSTALL_DIR} && ${DOCKER} compose run --rm vagas-agent >> ${INSTALL_DIR}/data/cron.log 2>&1"
  REBOOT_LINE="@reboot sleep 90 && cd ${INSTALL_DIR} && ${DOCKER} compose run --rm vagas-agent >> ${INSTALL_DIR}/data/cron.log 2>&1"
  (
    crontab -l 2>/dev/null | grep -v "vagas-agent" || true
    echo "$CRON_LINE"
    echo "$REBOOT_LINE"
  ) | crontab -
  echo "Cron configurado."
fi

echo
echo "============================================"
echo "Pasta: $(pwd)"
echo "Buscar agora:  docker compose run --rm vagas-agent"
echo "Ver agenda:    crontab -l"
echo "Ver log:       tail -f data/cron.log"
echo "============================================"
