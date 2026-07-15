@echo off
echo ===============================================
echo   J.A.R.V.I.S  Laptop Companion Client
echo   Connecting to Render cloud server...
echo ===============================================
echo.

:: Use the local virtual environment Python
set PYTHON_EXE=".\\.venv\\Scripts\\python.exe"
set PYTHONPATH=%cd%

%PYTHON_EXE% -m jarvis_desktop.laptop_client
pause
