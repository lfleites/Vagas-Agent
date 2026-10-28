#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  Agente de Vagas (Gupy + Telegram)"
echo "============================================"
echo

if [[ -f "./app.py" && -f "./Dockerfile" ]]; then
  INSTALL_DIR="$(pwd)"
else
  INSTALL_DIR="${INSTALL_DIR:-$HOME/vagas-agent}"
  mkdir -p "$INSTALL_DIR"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ "$SCRIPT_DIR" != "$INSTALL_DIR" ]]; then
    cp -f "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR/docker-compose.yml" "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/" 2>/dev/null || true
  fi
fi

cd "$INSTALL_DIR"
mkdir -p data

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado. Instale o Docker antes de continuar."
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Configure o bot do Telegram:"
echo "1. Fale com @BotFather no Telegram e crie um bot (/newbot)"
echo "2. Copie o token"
echo "3. Envie qualquer mensagem para o bot"
echo "4. Acesse https://api.telegram.org/bot<SEU_TOKEN>/getUpdates e pegue o chat.id"
echo

read -r -p "Token do Telegram Bot: " TELEGRAM_TOKEN
read -r -p "Chat ID: " TELEGRAM_CHAT_ID
read -r -p "Termo de busca na Gupy [Suporte]: " SEARCH_TERM
SEARCH_TERM=${SEARCH_TERM:-Suporte}
read -r -p "Modelo de trabalho (remote/hybrid/on-site) [remote]: " WORKPLACE
WORKPLACE=${WORKPLACE:-remote}

echo
echo "Filtros (deixe em branco para não usar):"
read -r -p "Termos obrigatórios no título (separados por vírgula): " REQUIRED_TERMS
read -r -p "Termos para descartar (separados por vírgula): " EXCLUDED_TERMS

cat > .env << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
SEARCH_TERM=${SEARCH_TERM}
WORKPLACE=${WORKPLACE}
REQUIRED_TERMS=${REQUIRED_TERMS}
EXCLUDED_TERMS=${EXCLUDED_TERMS}
MAX_ALERTS=10
EOF

chmod 600 .env

echo
echo "Construindo a imagem Docker (pode levar alguns minutos)..."
docker compose build

echo
read -r -p "Deseja configurar execução automática a cada 5 horas e no boot? (s/N): " SETUP_CRON
if [[ "${SETUP_CRON,,}" == "s" || "${SETUP_CRON,,}" == "sim" ]]; then
  CRON_LINE="0 */5 * * * cd ${INSTALL_DIR} && /usr/bin/docker compose run --rm vagas-agent >> ${INSTALL_DIR}/data/cron.log 2>&1"
  REBOOT_LINE="@reboot sleep 90 && cd ${INSTALL_DIR} && /usr/bin/docker compose run --rm vagas-agent >> ${INSTALL_DIR}/data/cron.log 2>&1"
  (crontab -l 2>/dev/null | grep -v "vagas-agent" || true; echo "$CRON_LINE"; echo "$REBOOT_LINE"; echo) | crontab -
  echo "Cron configurado (a cada 5 horas + no boot)."
fi

echo
echo "Teste inicial:"
docker compose run --rm vagas-agent || true

echo
echo "============================================"
echo "Instalação concluída em: $INSTALL_DIR"
echo
echo "Comandos úteis:"
echo "  cd $INSTALL_DIR"
echo "  docker compose run --rm vagas-agent    # executar agora"
echo "  crontab -l                             # ver agendamento"
echo "  tail -f data/cron.log                  # acompanhar logs"
echo "============================================"
