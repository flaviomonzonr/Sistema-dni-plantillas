@echo off
title EscanDNI Peru - Backend FastAPI
cd /d "%~dp0"
echo ========================================================
echo Iniciando Backend FastAPI en http://127.0.0.1:8000 ...
echo ========================================================
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
