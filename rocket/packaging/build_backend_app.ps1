param(
    [string]$PowersSourceDir = $env:ROCKET_POWERS_SOURCE_DIR,
    [switch]$SkipFlutterBuild
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendApp = Join-Path $Root "apps\desktop"
$Spec = Join-Path $Root "packaging\RocketBackend.spec"
$BackendDist = Join-Path $Root "dist\RocketBackend"
$FlutterRelease = Join-Path $BackendApp "build\windows\x64\runner\Release"
$BundleBackend = Join-Path $FlutterRelease "data\backend"
$BundlePowers = Join-Path $FlutterRelease "data\opencode-powers"
$BundleTools = Join-Path $FlutterRelease "data\tools"
$BundleOpenCode = Join-Path $BundleTools "opencode"

if ([string]::IsNullOrWhiteSpace($PowersSourceDir)) {
    $PowersSourceDir = "C:\Users\Aarush\shokunin-opencode-powers"
}

Write-Host "Building bundled Rocket backend executable..."
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

if (-not $SkipFlutterBuild) {
    Write-Host "Building Flutter Windows backend app..."
    Push-Location $BackendApp
    try {
        flutter pub get
        flutter build windows --release
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $FlutterRelease)) {
    throw "Flutter release output missing: $FlutterRelease"
}
if (-not (Test-Path $BackendDist)) {
    throw "Backend executable output missing: $BackendDist"
}

Write-Host "Embedding backend executable into Flutter app bundle..."
if (Test-Path $BundleBackend) {
    Remove-Item -LiteralPath $BundleBackend -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $BundleBackend | Out-Null
Copy-Item -Path (Join-Path $BackendDist "*") -Destination $BundleBackend -Recurse -Force

if (Test-Path $PowersSourceDir) {
    Write-Host "Embedding OpenCode powers from $PowersSourceDir"
    if (Test-Path $BundlePowers) {
        Remove-Item -LiteralPath $BundlePowers -Recurse -Force
    }
    Copy-Item -LiteralPath $PowersSourceDir -Destination $BundlePowers -Recurse -Force
} else {
    Write-Warning "OpenCode powers source missing: $PowersSourceDir"
}

$OpenCodeCommand = Get-Command "opencode.cmd" -ErrorAction SilentlyContinue
if ($OpenCodeCommand) {
    $OpenCodeCmdPath = $OpenCodeCommand.Source
    $OpenCodeNpmRoot = Split-Path -Parent $OpenCodeCmdPath
    $OpenCodePackage = Join-Path $OpenCodeNpmRoot "node_modules\opencode-ai"
    Write-Host "Embedding OpenCode CLI from $OpenCodeCmdPath"
    if (Test-Path $BundleOpenCode) {
        Remove-Item -LiteralPath $BundleOpenCode -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $BundleOpenCode | Out-Null
    Copy-Item -LiteralPath $OpenCodeCmdPath -Destination (Join-Path $BundleOpenCode "opencode.cmd") -Force
    if (Test-Path $OpenCodePackage) {
        New-Item -ItemType Directory -Force -Path (Join-Path $BundleOpenCode "node_modules") | Out-Null
        Copy-Item -LiteralPath $OpenCodePackage -Destination (Join-Path $BundleOpenCode "node_modules\opencode-ai") -Recurse -Force
    } else {
        Write-Warning "OpenCode package directory missing: $OpenCodePackage"
    }
} else {
    Write-Warning "opencode.cmd not found. Bundle will require OpenCode CLI to be installed separately."
}

Write-Host ""
Write-Host "Rocket Backend app bundle ready:"
Write-Host $FlutterRelease
Write-Host ""
Write-Host "Run:"
Write-Host (Join-Path $FlutterRelease "rocket_backend_app.exe")
