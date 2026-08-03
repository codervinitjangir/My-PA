@echo off
echo ===============================================
echo   J.A.R.V.I.S  Unified Desktop Application
echo ===============================================
echo.
echo Checking dependencies (PySide6, qasync, etc)...
.\.venv\Scripts\pip install -q -r requirements.txt
.\.venv\Scripts\pip install -q PySide6 qasync

echo.
echo Launching GUI and Background Engines...
:: Using pythonw.exe to launch the GUI without leaving a black terminal window open
start "" ".\.venv\Scripts\pythonw.exe" -m jarvis_desktop.app
exit
