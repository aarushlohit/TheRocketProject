@echo off
echo ========================================
echo   Rocket - Starting Backend & Flutter App
echo ========================================
echo.

cd /d "%~dp0"

echo Starting RocketTerminal in new window...
start "RocketTerminal" cmd /k start_backend.bat

timeout /t 3 /nobreak >nul

echo Starting Flutter app in new window...
start "Rocket Flutter" cmd /k start_frontend.bat

echo.
echo ========================================
echo Rocket is starting.
echo ========================================
echo.
echo Backend: ws://0.0.0.0:8765
echo Flutter: Check the Flutter window
echo.
echo Close this window if both servers started successfully.
pause
