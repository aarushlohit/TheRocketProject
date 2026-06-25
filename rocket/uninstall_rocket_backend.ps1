param(
    [string]$InstallName = "Rocket Backend"
)

$ErrorActionPreference = "Stop"

$AppDir = Join-Path $env:LOCALAPPDATA "RocketBackend"
$Launcher = Join-Path $AppDir "RocketBackend.cmd"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Rocket"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$InstallName.lnk"
$StartMenuShortcut = Join-Path $StartMenuDir "$InstallName.lnk"

foreach ($Path in @($DesktopShortcut, $StartMenuShortcut, $Launcher)) {
    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force
        Write-Host "Removed $Path"
    }
}

if ((Test-Path $AppDir) -and -not (Get-ChildItem -LiteralPath $AppDir -Force)) {
    Remove-Item -LiteralPath $AppDir -Force
}

Write-Host "Rocket Backend shortcut wrapper removed."
Write-Host "Project files and virtual environment were not deleted."
