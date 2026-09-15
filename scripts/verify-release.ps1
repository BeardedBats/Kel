# Verifies a Kel release directory against a SHA-256 sums file.
# The V1.2 sums file lists three hashes in this order (no filenames):
#   Kel.exe, resources/app.asar, resources/kel-engine/KelEngine.exe
# Usage: powershell -ExecutionPolicy Bypass -File scripts/verify-release.ps1 -ReleaseDir <dir> [-Manifest <file>]
param(
    [Parameter(Mandatory=$true)][string]$ReleaseDir,
    [string]$Manifest = ""
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
if ([string]::IsNullOrEmpty($Manifest)) { $Manifest = Join-Path $repo "docs/v1.2/SHA256Sums.txt.txt" }
$expected = @((Get-Content $Manifest) | Where-Object { $_.Trim() -ne "" })
$files = @("Kel.exe", "resources/app.asar", "resources/kel-engine/KelEngine.exe")
if ($expected.Count -lt $files.Count) { throw "Manifest has fewer entries than expected ($($expected.Count))." }
$ok = $true
for ($i = 0; $i -lt $files.Count; $i++) {
    $p = Join-Path $ReleaseDir $files[$i]
    if (-not (Test-Path $p)) { Write-Host "MISSING $($files[$i])"; $ok = $false; continue }
    $h = (Get-FileHash -Algorithm SHA256 $p).Hash
    if ($h -ieq $expected[$i]) {
        Write-Host "OK    $($files[$i])"
    } else {
        Write-Host "FAIL  $($files[$i])"
        Write-Host "      expected $($expected[$i])"
        Write-Host "      actual   $h"
        $ok = $false
    }
}
if ($ok) { Write-Host "Release verification passed." } else { Write-Host "Release verification FAILED."; exit 1 }
