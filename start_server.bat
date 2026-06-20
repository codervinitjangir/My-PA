@echo off
echo Starting J.A.R.V.I.S Backend Server...

:: Start the desktop companion in the background
set PYTHONPATH=%cd%
start /B "" ".venv\Scripts\python.exe" -m jarvis_desktop.main

:: Start the main backend
".venv\Scripts\python.exe" run.py
pause
