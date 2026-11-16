@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   Agente de Vagas (Gupy + Telegram)
echo ============================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker nao encontrado.
  echo Instale o Docker Desktop, abra ele e rode este script de novo.
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo Docker Compose nao encontrado.
  echo Atualize o Docker Desktop e deixe ele aberto.
  exit /b 1
)

if not exist data mkdir data

set "REPLACE=s"
if exist .env (
  set "REPLACE="
  set /p "REPLACE=Ja existe um .env. Substituir token e chat ID? [s/N]: "
)
if /I not "%REPLACE%"=="s" if /I not "%REPLACE%"=="sim" goto build

echo.
echo 1. Fale com @BotFather no Telegram e crie um bot (/newbot^)
echo 2. Copie o token
echo 3. Envie qualquer mensagem para o bot
echo 4. Abra https://api.telegram.org/botSEU_TOKEN/getUpdates
echo    e copie o numero em "chat":{"id":...}
echo.
set /p "TELEGRAM_TOKEN=Token do Telegram: "
set /p "TELEGRAM_CHAT_ID=Chat ID: "
if "%TELEGRAM_TOKEN%"=="" goto missing
if "%TELEGRAM_CHAT_ID%"=="" goto missing

> ".env" echo TELEGRAM_TOKEN=%TELEGRAM_TOKEN%
>> ".env" echo TELEGRAM_CHAT_ID=%TELEGRAM_CHAT_ID%
echo .env gravado. Ele nao vai para o GitHub.
echo.

:build
echo Os filtros de titulo ficam em filtros.txt. Edite esse arquivo para a sua area.
echo A busca da Gupy esta em app.py: termo Suporte, so vagas remotas.
echo.
echo Construindo a imagem Docker. A primeira vez demora alguns minutos.
docker compose build
if errorlevel 1 exit /b 1

echo.
set "RUN_NOW="
set /p "RUN_NOW=Executar uma busca agora? [s/N]: "
if /I "%RUN_NOW%"=="s" docker compose run --rm vagas-agent
if /I "%RUN_NOW%"=="sim" docker compose run --rm vagas-agent

echo.
set "SETUP_TASK="
set /p "SETUP_TASK=Agendar a cada 5 horas e ao entrar no Windows? [s/N]: "
if /I "%SETUP_TASK%"=="s" goto schedule
if /I "%SETUP_TASK%"=="sim" goto schedule
goto done

:schedule
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
schtasks /Create /F /TN "Vagas-Agent" /SC HOURLY /MO 5 /TR "\"%ROOT%\run.bat\""
if errorlevel 1 goto taskfail
schtasks /Create /F /TN "Vagas-Agent-Logon" /SC ONLOGON /DELAY 0001:30 /TR "\"%ROOT%\run.bat\""
if errorlevel 1 goto taskfail
echo Tarefas criadas: Vagas-Agent e Vagas-Agent-Logon.
goto done

:taskfail
echo Nao foi possivel criar a tarefa. Crie no Agendador de Tarefas chamando run.bat.
exit /b 1

:missing
echo Token e chat ID sao obrigatorios.
exit /b 1

:done
echo.
echo ============================================
echo Pasta: %cd%
echo Buscar agora: docker compose run --rm vagas-agent
echo Log:          data\cron.log
echo ============================================
exit /b 0
