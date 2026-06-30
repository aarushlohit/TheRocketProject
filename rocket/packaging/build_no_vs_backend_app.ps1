param(
    [string]$PowersSourceDir = $env:ROCKET_POWERS_SOURCE_DIR,
    [int]$WebSocketPort = 8765,
    [int]$DashboardPort = 8790
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$WebApp = Join-Path $Root "apps\web"
$Spec = Join-Path $Root "packaging\RocketBackend.spec"
$BackendDist = Join-Path $Root "dist\RocketBackend"
$PackageDir = Join-Path $Root "dist\RocketBackendApp-NoVS"
$DashboardBuild = Join-Path $WebApp "build\web"

if ([string]::IsNullOrWhiteSpace($PowersSourceDir)) {
    $PowersSourceDir = "C:\Users\Aarush\shokunin-opencode-powers"
}

Write-Host "Building Flutter web dashboard..."
Push-Location $WebApp
try {
    flutter pub get
    flutter build web --release
}
finally {
    Pop-Location
}

Write-Host "Building frozen Rocket backend executable..."
Push-Location $Root
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        python -m venv .venv
    }
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pip install pyinstaller
    .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if (Test-Path $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null

Write-Host "Copying backend executable..."
Copy-Item -Path (Join-Path $BackendDist "*") -Destination $PackageDir -Recurse -Force

Write-Host "Copying Flutter web dashboard..."
Copy-Item -LiteralPath $DashboardBuild -Destination (Join-Path $PackageDir "dashboard") -Recurse -Force

if (Test-Path $PowersSourceDir) {
    Write-Host "Copying OpenCode powers..."
    Copy-Item -LiteralPath $PowersSourceDir -Destination (Join-Path $PackageDir "opencode-powers") -Recurse -Force
} else {
    Write-Warning "OpenCode powers source missing: $PowersSourceDir"
}

$OpenCodeCommand = Get-Command "opencode.cmd" -ErrorAction SilentlyContinue
if ($OpenCodeCommand) {
    $OpenCodeCmdPath = $OpenCodeCommand.Source
    $OpenCodeNpmRoot = Split-Path -Parent $OpenCodeCmdPath
    $OpenCodePackage = Join-Path $OpenCodeNpmRoot "node_modules\opencode-ai"
    $BundleOpenCode = Join-Path $PackageDir "tools\opencode"
    Write-Host "Copying OpenCode CLI..."
    New-Item -ItemType Directory -Force -Path $BundleOpenCode | Out-Null
    Copy-Item -LiteralPath $OpenCodeCmdPath -Destination (Join-Path $BundleOpenCode "opencode.cmd") -Force
    if (Test-Path $OpenCodePackage) {
        New-Item -ItemType Directory -Force -Path (Join-Path $BundleOpenCode "node_modules") | Out-Null
        Copy-Item -LiteralPath $OpenCodePackage -Destination (Join-Path $BundleOpenCode "node_modules\opencode-ai") -Recurse -Force
    }
} else {
    Write-Warning "opencode.cmd not found. Packaged app will require global OpenCode."
}

$Launcher = Join-Path $PackageDir "RocketBackendApp.cmd"
$LauncherContent = @"
@echo off
title Rocket Backend
cd /d "%~dp0"
set ROCKET_APP_BUNDLE_DIR=%~dp0
set ROCKET_DATA_DIR=%LOCALAPPDATA%\RocketBackend\data
set ROCKET_POWERS_SOURCE_DIR=%~dp0opencode-powers
if exist "%~dp0tools\opencode\opencode.cmd" set ROCKET_OPENCODE_COMMAND=%~dp0tools\opencode\opencode.cmd
set ROCKET_OPEN_DASHBOARD=1
set PYTHONUTF8=1
RocketBackend.exe --host 0.0.0.0 --port $WebSocketPort --dashboard-port $DashboardPort --dashboard-root "%~dp0dashboard" --open-dashboard
pause
"@
Set-Content -Path $Launcher -Value $LauncherContent -Encoding ASCII

Write-Host ""
Write-Host "No-Visual-Studio Rocket Backend app package ready:"
Write-Host $PackageDir
Write-Host ""
Write-Host "Run:"
Write-Host $Launcher
