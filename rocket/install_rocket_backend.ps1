param(
    [string]$InstallName = "Rocket Backend",
    [int]$Port = 8765,
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $env:LOCALAPPDATA "RocketBackend"
$Launcher = Join-Path $AppDir "RocketBackend.cmd"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Rocket"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$InstallName.lnk"
$StartMenuShortcut = Join-Path $StartMenuDir "$InstallName.lnk"

Write-Host "Installing Rocket Backend from $ProjectRoot"
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null

Push-Location $ProjectRoot
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "Creating Python virtual environment..."
        python -m venv .venv
    }

    Write-Host "Installing Python requirements..."
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
finally {
    Pop-Location
}

$LauncherContent = @"
@echo off
title Rocket Backend
cd /d "$ProjectRoot"
set PYTHONPATH=$ProjectRoot
echo Starting Rocket Backend on ws://0.0.0.0:$Port
echo.
".venv\Scripts\python.exe" -m agent.main --host 0.0.0.0 --port $Port
pause
"@

Set-Content -Path $Launcher -Value $LauncherContent -Encoding ASCII

function New-RocketShortcut {
    param(
        [Parameter(Mandatory=$true)][string]$Path
    )
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $Launcher
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.WindowStyle = 1
    $Shortcut.Description = "Start $InstallName"
    $Shortcut.Save()
}

New-RocketShortcut -Path $StartMenuShortcut
if (-not $NoDesktopShortcut) {
    New-RocketShortcut -Path $DesktopShortcut
}

Write-Host ""
Write-Host "Rocket Backend installed."
Write-Host "Launcher: $Launcher"
Write-Host "Start Menu shortcut: $StartMenuShortcut"
if (-not $NoDesktopShortcut) {
    Write-Host "Desktop shortcut: $DesktopShortcut"
}
Write-Host ""
Write-Host "Open '$InstallName' from the Start Menu or Desktop to start the backend."
