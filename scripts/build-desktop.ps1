# Builds the Aion Donor Shell (desktop) with electron-vite.
# Requirements: Node.js + bun (bun.lock is authoritative). Use -Install on first run.
# Usage (from repo root): powershell -ExecutionPolicy Bypass -File scripts/build-desktop.ps1 [-Install]
param(
    [string]$PackageManager = "bun",
    [switch]$Install
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location (Join-Path $repo "desktop")
try {
    if ($Install) { & $PackageManager install }
    & $PackageManager run build
    Write-Host "Desktop build complete: desktop/out (main, preload, renderer)."
} finally {
    Pop-Location
}
