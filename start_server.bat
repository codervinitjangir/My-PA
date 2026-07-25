@echo off
echo ================================================
echo   J.A.R.V.I.S  Local Server
echo ================================================

:: Kill any old lingering desktop widget processes so the UI updates
taskkill /F /IM python.exe /FI "WINDOWTITLE eq JARVIS ACTIVE" >nul 2>&1

:: Force use of the local virtual environment Python
set PYTHON_EXE=".\.venv\Scripts\python.exe"
set PYTHONPATH=%cd%

:: Start the desktop companion widget in the background
start /B "" %PYTHON_EXE% -m jarvis_desktop.main

:: Launch Laptop Companion Client in a separate window if enabled
for /f "tokens=2 delims==" %%v in ('findstr /i "^RENDER_URL=" .env 2^>nul') do set RENDER_URL_VAL=%%v
echo [INFO] Launching JARVIS Laptop Client...
start "JARVIS Laptop Client" %PYTHON_EXE% -m jarvis_desktop.laptop_client

:: Start the main local backend server
echo [INFO] Starting JARVIS local backend server (http://127.0.0.1:8000)...
%PYTHON_EXE% run.py
pause
