@echo off
echo Starting J.A.R.V.I.S Backend Server...

:: Kill any old lingering desktop widget processes so the UI updates
taskkill /F /IM python.exe /FI "WINDOWTITLE eq JARVIS ACTIVE" >nul 2>&1

:: Force use of the local virtual environment Python
set PYTHON_EXE=".\.venv\Scripts\python.exe"

:: Start the desktop companion in the background
set PYTHONPATH=%cd%
start /B "" %PYTHON_EXE% -m jarvis_desktop.main

:: Start the main backend
%PYTHON_EXE% run.py
pause
