@echo off
rem Stop kyuka_calc (port 5009) only. Details in stop.ps1.
rem NOTE: Keep this file ASCII-only. Japanese text in .bat files
rem can be misparsed by cmd.exe and execute garbage commands.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
pause
