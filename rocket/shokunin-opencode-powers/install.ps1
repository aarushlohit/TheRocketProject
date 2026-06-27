# Shokunin OpenCode Powers - Installer
# Run: irm https://raw.githubusercontent.com/... | iex
# Or: .\install.ps1

$ErrorActionPreference = "Stop"
$OC_DIR = "$env:USERPROFILE\.config\opencode"
$PKG_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Shokunin OpenCode Powers Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Create directories
Write-Host "[1/7] Creating directories..." -ForegroundColor Yellow
@("$OC_DIR\plugins", "$OC_DIR\skills", "$env:USERPROFILE\.shokunin\memory\chroma_db", "$env:USERPROFILE\.shokunin\memory\sessions", "$env:USERPROFILE\.shokunin\scripts", "$env:USERPROFILE\.cache\chroma\onnx_models") | ForEach-Object {
    New-Item -ItemType Directory -Path $_ -Force | Out-Null
}

# 2. Install Python dependencies
Write-Host "[2/7] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install chromadb --quiet 2>&1 | Out-Null

# 3. Install npm MCP servers
Write-Host "[3/7] Installing npm MCP servers (this takes a while)..." -ForegroundColor Yellow
$npmPackages = @(
    "@modelcontextprotocol/server-github",
    "google-tools-mcp",
    "claude-screen-mcp",
    "@playwright/mcp",
    "@dangahagan/weather-mcp",
    "@topvisor/mcp-notifications",
    "mcp-personal-suite",
    "@darbotlabs/darbot-windows-mcp",
    "computer-use-mcp",
    "@bitbonsai/mcpvault",
    "neo-mcp",
    "@eat-pray-ai/yutu"
)
foreach ($pkg in $npmPackages) {
    Write-Host "  Installing $pkg..." -ForegroundColor DarkGray
    npm install -g $pkg --quiet 2>&1 | Out-Null
}

# 4. Copy shokunin-memory MCP server
Write-Host "[4/7] Installing shokunin-memory..." -ForegroundColor Yellow
Copy-Item "$PKG_DIR\mcp-servers\shokunin-memory\mcp-server.py" "$env:USERPROFILE\.shokunin\memory\mcp-server.py" -Force
Copy-Item "$PKG_DIR\mcp-servers\shokunin-memory\chroma-helper.py" "$env:USERPROFILE\.shokunin\scripts\chroma-helper.py" -Force

# 5. Install superpowers plugin
Write-Host "[5/7] Installing superpowers plugin..." -ForegroundColor Yellow
if (Test-Path "$OC_DIR\superpowers") {
    Push-Location "$OC_DIR\superpowers"; git pull; Pop-Location
} else {
    git clone https://github.com/obra/superpowers.git "$OC_DIR\superpowers" 2>&1 | Out-Null
}
Copy-Item "$OC_DIR\superpowers\.opencode\plugins\superpowers.js" "$OC_DIR\plugins\superpowers.js" -Force
Copy-Item "$OC_DIR\superpowers\skills" "$OC_DIR\skills\superpowers" -Recurse -Force

# 6. Merge opencode.json
Write-Host "[6/7] Merging opencode.json config..." -ForegroundColor Yellow
$existing = Get-Content "$OC_DIR\opencode.json" -Raw | ConvertFrom-Json
$new = Get-Content "$PKG_DIR\opencode.json" -Raw | ConvertFrom-Json

# Merge MCP entries
foreach ($prop in $new.mcp.PSObject.Properties) {
    if (-not $existing.mcp.PSObject.Properties[$prop.Name]) {
        $existing.mcp | Add-Member -NotePropertyName $prop.Name -NotePropertyValue $prop.Value
        Write-Host "  Added: $($prop.Name)" -ForegroundColor DarkGray
    } else {
        Write-Host "  Exists: $($prop.Name) (skipping)" -ForegroundColor DarkGray
    }
}

# Add superpowers plugin if not present
if ($existing.plugin -notcontains "superpowers@git+https://github.com/obra/superpowers.git") {
    $existing.plugin += "superpowers@git+https://github.com/obra/superpowers.git"
}

$existing | ConvertTo-Json -Depth 10 | Set-Content "$OC_DIR\opencode.json"

# 7. Download ONNX embeddings model
Write-Host "[7/7] Downloading ONNX embeddings model (79MB)..." -ForegroundColor Yellow
$onnxDir = "$env:USERPROFILE\.cache\chroma\onnx_models\all-MiniLM-L6-v2"
if (!(Test-Path "$onnxDir\model.onnx")) {
    New-Item -ItemType Directory -Path $onnxDir -Force | Out-Null
    $url = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx/model.onnx"
    Invoke-WebRequest -Uri $url -OutFile "$onnxDir\model.onnx" -UseBasicParsing
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Restart opencode to activate all powers." -ForegroundColor Cyan
Write-Host ""
Write-Host "MCP Servers (13):" -ForegroundColor White
Write-Host "  shokunin-memory  - Persistent memory (ChromaDB)" -ForegroundColor Gray
Write-Host "  github           - GitHub integration" -ForegroundColor Gray
Write-Host "  google-workspace - Google Docs/Sheets/Drive" -ForegroundColor Gray
Write-Host "  claude-screen    - Screen capture/OCR" -ForegroundColor Gray
Write-Host "  playwright       - Browser automation" -ForegroundColor Gray
Write-Host "  computer-use     - Mouse/keyboard control" -ForegroundColor Gray
Write-Host "  obsidian         - Vault management" -ForegroundColor Gray
Write-Host "  darbot-windows   - Windows automation" -ForegroundColor Gray
Write-Host "  weather          - Weather queries" -ForegroundColor Gray
Write-Host "  notifications    - Desktop notifications" -ForegroundColor Gray
Write-Host "  personal-suite   - Productivity tools" -ForegroundColor Gray
Write-Host "  neo-mcp          - AI tasks (needs key)" -ForegroundColor DarkGray
Write-Host "  youtube          - YouTube API (needs auth)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Skills (14 superpowers):" -ForegroundColor White
Write-Host "  brainstorming, test-driven-development, systematic-debugging," -ForegroundColor Gray
Write-Host "  executing-plans, verification-before-completion, and 10 more" -ForegroundColor Gray
Write-Host ""
Write-Host "Edit $OC_DIR\opencode.json to add your API keys." -ForegroundColor Yellow
