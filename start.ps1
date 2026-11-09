#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Join-Path $PSScriptRoot "coding"
Set-Location $Root

function Find-CommandPath {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

# Prefer a project-local portable Node.js runtime when present.
if (-not (Find-CommandPath "node")) {
    $portableRoots = @(
        (Join-Path $Root ".tools\node"),
        (Join-Path (Split-Path -Parent $Root) ".tools\node"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Root)) ".tools\node")
    )
    foreach ($portableRoot in $portableRoots) {
        if (-not (Test-Path $portableRoot)) {
            continue
        }
        $nodeExe = Get-ChildItem $portableRoot -Recurse -Filter "node.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($nodeExe) {
            $env:PATH = "$($nodeExe.DirectoryName);$env:PATH"
            break
        }
    }
}

if (-not (Find-CommandPath "node")) {
    throw "Node.js 18+ was not found. Install Node.js or add it to PATH."
}

$VenV = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenV)) {
    $bootstrap = $null
    $bootstrapCandidates = @(
        (Join-Path $Root ".tools\py\python\python.exe"),
        (Join-Path (Split-Path -Parent $Root) ".tools\py\python\python.exe"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Root)) ".tools\py\python\python.exe")
    )
    foreach ($candidate in $bootstrapCandidates) {
        if (Test-Path $candidate) {
            $bootstrap = @($candidate)
            break
        }
    }
    if (-not $bootstrap) {
        $bootstrap = Find-CommandPath "python"
        if (-not $bootstrap) {
            throw "Python 3.11+ was not found. Install Python or create .venv."
        }
        $bootstrap = @($bootstrap)
    }
    $bootstrapExe = $bootstrap[0]
    & $bootstrapExe -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv."
    }
}

& $VenV -c "import fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $VenV -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Python dependencies."
    }
}

if (-not (Test-Path (Join-Path $Root "node_modules"))) {
    & npm ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install npm dependencies."
    }
}

& npm run build
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build the frontend."
}

& $VenV -m skill_manager start --state-dir (Join-Path $Root ".artifacts\runtime") --open-browser
