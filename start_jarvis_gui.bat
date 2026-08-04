@echo off
echo ===============================================
echo   J.A.R.V.I.S  Unified Desktop Application
echo ===============================================
echo.

echo.
echo Launching GUI and Background Engines...
:: Using pythonw.exe to launch the GUI without leaving a black terminal window open
start "" ".\.venv\Scripts\pythonw.exe" -m jarvis_desktop.app
exit
