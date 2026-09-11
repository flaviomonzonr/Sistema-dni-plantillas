@echo off
title EscanDNI Peru - Lanzador Completo
cd /d "%~dp0"
cls
echo =======================================================================
echo   SISTEMA ESCANDNI PERU - AGROINDUSTRIAS CHAVIN
echo =======================================================================
echo.
echo   [1/2] Iniciando Servidor Backend (Python / FastAPI)...
echo         Base de Datos y Plantillas en: http://127.0.0.1:8000
echo.
start "EscanDNI 1. Backend (NO CERRAR)" cmd /k "title EscanDNI - Backend (Python) && cd /d ""%~dp0"" && python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

echo   [2/2] Iniciando Servidor Frontend (Vite / React)...
echo         Interfaz grafica en: http://localhost:5173
echo.
start "EscanDNI 2. Frontend (NO CERRAR)" cmd /k "title EscanDNI - Frontend (React) && cd /d ""%~dp0frontend"" && npm run dev"

echo =======================================================================
echo   Ambos servidores se estan iniciando en ventanas independientes.
echo   IMPORTANTE: NO cierre las ventanas negras mientras use el sistema.
echo   Abriendo navegador en http://localhost:5173 ...
echo =======================================================================
timeout /t 5 >nul
start http://localhost:5173


