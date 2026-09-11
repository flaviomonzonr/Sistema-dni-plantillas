@echo off
title EscanDNI Peru - Frontend React
cd /d "%~dp0"
echo ========================================================
echo Iniciando Frontend React (Vite) en http://localhost:5173 ...
echo ========================================================
cd frontend
npm run dev
pause

