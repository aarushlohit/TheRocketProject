@echo off
echo Starting Flutter Frontend...
echo.

cd /d "%~dp0\apps\mobile"

if not exist pubspec.yaml (
    echo ERROR: Flutter project not found in apps\mobile directory!
    pause
    exit /b 1
)

echo Installing Flutter dependencies...
call flutter pub get

echo.
echo Starting Flutter app...
echo Choose a device when prompted
echo.

call flutter run
