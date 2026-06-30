@echo off
title C2 Agent Watchdog
echo C2 Agent Watchdog - Dam bao agent luon chay
echo ============================================
:loop
tasklist | find "python.exe" >nul
if errorlevel 1 (
    echo [%date% %time%] Agent NOT running. Starting...
    start "" "%~dp0agent_portable.py"
)
timeout /t 10 /nobreak >nul
goto loop
