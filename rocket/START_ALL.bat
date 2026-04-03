@echo off
echo ========================================
echo   Rocket - Starting Backend & Frontend
echo ========================================
echo.

cd /d "%~dp0"

echo Starting Backend Server in new window...
start "Rocket Backend" cmd /k start_backend.bat

timeout /t 3 /nobreak >nul

echo Starting Flutter Frontend in new window...
start "Rocket Frontend" cmd /k start_frontend.bat

echo.
echo ========================================
echo Both servers are starting!
echo ========================================
echo.
echo Backend: ws://0.0.0.0:8765
echo Frontend: Check the Flutter window
echo.
echo Close this window if both servers started successfully.
pause
