@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Checking Python...
where %PYTHON% >nul 2>nul
if errorlevel 1 (
    echo Python not found.
    echo Please install Python or recreate the .venv first.
    pause
    exit /b 1
)

echo Starting weather collector...
start "Weather Collector" cmd /k ""%PYTHON%" collector.py --loop"

echo Waiting a few seconds for the collector to start...
timeout /t 5 /nobreak >nul

echo Running analysis...
"%PYTHON%" analyze.py

echo Starting dashboard server...
start "Weather Dashboard" cmd /k ""%PYTHON%" dashboard_server.py"

echo.
echo Open your browser to:
echo http://127.0.0.1:8000/
echo.
echo The collector and dashboard are running in separate windows.
echo Press any key to close this launcher.
pause >nul