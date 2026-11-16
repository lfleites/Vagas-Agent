@echo off
cd /d "%~dp0"
if not exist data mkdir data
docker compose run --rm vagas-agent >> "%~dp0data\cron.log" 2>&1
