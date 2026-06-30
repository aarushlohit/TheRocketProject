# Rocket Desktop App

Flutter Windows application that embeds the Rocket Python backend and launches it as a bundled desktop process.

## Purpose

Provides a native Windows launcher for the Rocket backend service, managing the process lifecycle and surfacing status via a system tray icon. The bundled backend executable and OpenCode powers are embedded in `data/`.

## Development

```powershell
cd apps/desktop
flutter pub get
flutter run -d windows
```

## Build (bundled with backend)

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_backend_app.ps1
```

The output is at:

```
apps/desktop/build/windows/x64/runner/Release/rocket_backend_app.exe
```

To create a full Windows installer (requires Inno Setup 6):

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\make_windows_installer.ps1
```

## See Also

- [`../../RUNBOOK.md`](../../RUNBOOK.md) — operational commands
- [`../../packaging/`](../../packaging/) — all build and install scripts
