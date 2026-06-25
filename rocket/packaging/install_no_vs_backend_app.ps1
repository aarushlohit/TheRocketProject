param(
    [string]$PackageDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "dist\RocketBackendApp-NoVS"),
    [string]$InstallName = "Rocket Backend"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PackageDir)) {
    throw "Package folder not found: $PackageDir. Run packaging\build_no_vs_backend_app.ps1 first."
}

$InstallDir = Join-Path $env:LOCALAPPDATA "RocketBackend\App"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Rocket"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$InstallName.lnk"
$StartMenuShortcut = Join-Path $StartMenuDir "$InstallName.lnk"
$Launcher = Join-Path $InstallDir "RocketBackendApp.cmd"

Write-Host "Installing $InstallName to $InstallDir"
if (Test-Path $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path (Join-Path $PackageDir "*") -Destination $InstallDir -Recurse -Force
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null

function New-RocketShortcut {
    param([Parameter(Mandatory=$true)][string]$Path)
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $Launcher
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.WindowStyle = 1
    $Shortcut.Description = "Start $InstallName"
    $Shortcut.Save()
}

New-RocketShortcut -Path $DesktopShortcut
New-RocketShortcut -Path $StartMenuShortcut

Write-Host ""
Write-Host "$InstallName installed."
Write-Host "Start Menu shortcut: $StartMenuShortcut"
Write-Host "Desktop shortcut: $DesktopShortcut"
