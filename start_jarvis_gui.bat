@echo off
echo ===============================================
echo   J.A.R.V.I.S  Unified Desktop Application
echo ===============================================
echo.

echo.
echo Launching Local Backend Server...
start /MIN "JARVIS Backend" ".\.venv\Scripts\python.exe" run.py

echo Launching GUI...
:: Add PySide6 to PATH so QtWebEngineProcess can find its DLLs
set PATH=%~dp0.venv\Lib\site-packages\PySide6;%PATH%
:: Using pythonw.exe to launch the GUI without leaving a black terminal window open
:: NOTE: Ultron Orb is NOT auto-started. Click "Orb" in the header to launch it on demand.
start "" ".\.venv\Scripts\pythonw.exe" -m jarvis_desktop.app
exit
