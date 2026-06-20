@echo off
echo Starting J.A.R.V.I.S Backend Server...

:: Kill any old lingering desktop widget processes so the UI updates
taskkill /F /IM python.exe /FI "WINDOWTITLE eq JARVIS ACTIVE" >nul 2>&1

:: Start the desktop companion in the background
set PYTHONPATH=%cd%
start /B "" python -m jarvis_desktop.main

:: Start the main backend
python run.py
pause
