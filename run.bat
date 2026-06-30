@echo off
title C2 System - Starting...
cd /d D:\C2

echo [1/3] Starting C2 Server...
start "C2 Server" cmd /c "cd /d D:\C2\server && .\venv\Scripts\activate && python main.py"

timeout /t 4 /nobreak >nul

echo [2/3] Starting Agent...
start "C2 Agent" cmd /c "cd /d D:\C2\agent && .\venv\Scripts\activate && python agent_portable.py"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Dashboard...
start "C2 Dashboard" cmd /c "cd /d D:\C2\dashboard && npm start"

echo.
echo =====================================
echo   All services started!
echo   Dashboard: http://localhost:3000
echo   Login: admin / admin123
echo =====================================
pause
