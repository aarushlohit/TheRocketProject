param(
    [string]$InstallName = "Rocket Backend"
)

$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $env:LOCALAPPDATA "RocketBackend"
$InstallDir = Join-Path $InstallRoot "App"
$StartMenuShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Rocket\$InstallName.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$InstallName.lnk"

foreach ($Path in @($DesktopShortcut, $StartMenuShortcut)) {
    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force
        Write-Host "Removed $Path"
    }
}

if (Test-Path $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
    Write-Host "Removed $InstallDir"
}

Write-Host "$InstallName app removed."
Write-Host "Runtime data in $InstallRoot\data was preserved."
