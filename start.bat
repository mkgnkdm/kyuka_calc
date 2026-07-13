@echo off
rem Start kyuka_calc locally (port 5011) and open the browser.
rem NOTE: Keep this file ASCII-only (see _framework\learn.md).
cd /d %~dp0
netstat -ano | findstr /C:":5011 " | findstr LISTENING >nul
if %errorlevel%==0 (
    echo ERROR: Port 5011 is already in use. Run stop.bat first.
    pause
    exit /b 1
)
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start "" http://127.0.0.1:5011"
venv\Scripts\python.exe app.py
pause
