@echo off
echo Starting RocketTerminal...
echo.

cd /d "%~dp0"
set PYTHONPATH=%CD%

if not exist .venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing Python dependencies...
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python requirements.
    pause
    exit /b 1
)

echo.
echo NVIDIA_API_KEY enables Nemotron. Pollinations fallback is used when primary fails.
echo Starting RocketTerminal on ws://0.0.0.0:8765
echo.

.\.venv\Scripts\python.exe -m agent.main --host 0.0.0.0 --port 8765
