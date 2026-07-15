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

:: Auto-launch laptop companion client if RENDER_URL is set in .env
:: This bridges your laptop desktop actions to your Render cloud server.
for /f "tokens=2 delims==" %%v in ('findstr /i "^RENDER_URL=" .env 2^>nul') do set RENDER_URL_VAL=%%v
if defined RENDER_URL_VAL (
    if not "%RENDER_URL_VAL%"=="" (
        echo.
        echo [INFO] RENDER_URL detected — launching Laptop Companion Client...
        echo [INFO] Your laptop will bridge desktop commands to Render.
        start "JARVIS Laptop Client" %PYTHON_EXE% -m jarvis_desktop.laptop_client
        echo.
    )
)

:: Start the main backend
echo [INFO] Starting JARVIS backend server...
%PYTHON_EXE% run.py
pause
