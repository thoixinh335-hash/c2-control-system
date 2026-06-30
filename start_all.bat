@echo off
title C2 System - Starting...
cd /d D:\C2

echo [1/5] Starting C2 Server...
start "C2 Server" cmd /c "cd /d D:\C2\controller\api && ..\..\..\controller\api\venv\Scripts\activate && python main.py"

timeout /t 4 /nobreak >nul

echo [2/5] Starting Cloudflare Tunnel...
start "C2 Tunnel" cmd /c "cd /d D:\C2\controller\tunnel && cloudflared.exe tunnel run c2-tunnel"

timeout /t 4 /nobreak >nul

echo [3/5] Starting Local Agent...
start "C2 Agent Local" cmd /c "cd /d D:\C2\payload\agent_core && python agent.py"

timeout /t 2 /nobreak >nul

echo [4/5] Starting Dashboard...
start "C2 Dashboard" cmd /c "cd /d D:\C2\dashboard && npm start"

echo.
echo =====================================
echo   All services started!
echo   Dashboard: http://localhost:3000
echo   Login: admin / admin123
echo =====================================
pause
