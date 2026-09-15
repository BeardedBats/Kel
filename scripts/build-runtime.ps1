# Builds the Kel Runtime (KelEngine) with PyInstaller from this repository.
# Requirements: Python 3.12+ with PyInstaller installed (pip install pyinstaller).
# Usage (from repo root): powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1
param(
    [string]$Python = "python",
    [string]$OutDir = "dist/runtime"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$out = Join-Path $repo $OutDir
New-Item -ItemType Directory -Force -Path $out | Out-Null
Push-Location (Join-Path $repo "runtime")
try {
    & $Python -m PyInstaller --noconfirm --clean --distpath $out --workpath (Join-Path $repo "dist/pyinstaller-work") KelEngine.spec
    Write-Host "KelEngine built at $(Join-Path $out 'KelEngine/KelEngine.exe')"
} finally {
    Pop-Location
}
