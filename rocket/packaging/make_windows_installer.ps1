param(
    [string]$PowersSourceDir = $env:ROCKET_POWERS_SOURCE_DIR
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildScript = Join-Path $Root "packaging\build_backend_app.ps1"
$InnoScript = Join-Path $Root "packaging\rocket_backend_app.iss"
$InnoCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"

& powershell -ExecutionPolicy Bypass -File $BuildScript -PowersSourceDir $PowersSourceDir

if (Test-Path $InnoCompiler) {
    Write-Host "Building RocketBackendSetup.exe with Inno Setup..."
    & $InnoCompiler $InnoScript
    Write-Host "Installer created in dist\installer"
} else {
    Write-Warning "Inno Setup compiler not found: $InnoCompiler"
    Write-Host "Install Inno Setup 6 to produce RocketBackendSetup.exe."
    Write-Host "The ready-to-run app bundle is still available at apps\desktop\build\windows\x64\runner\Release"
}
