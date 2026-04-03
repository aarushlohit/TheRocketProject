@echo off
echo Starting Rocket Backend Server...
echo.

cd /d "%~dp0"

set PYTHONPATH=%CD%

if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat





if not exist .env (
    echo ERROR: .env file not found!
    echo Please create .env with POLLINATIONS_API_KEY
    pause
    exit /b 1
)

echo Verifying Python dependencies...
.\.venv\Scripts\python.exe -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo Installing requirements into .venv...
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install Python requirements.
        pause
        exit /b 1
    )
)

echo Starting backend on ws://0.0.0.0:8765
echo Press Ctrl+C to stop
echo.

.\.venv\Scripts\python.exe -m agent.main --host 0.0.0.0 --port 8765
