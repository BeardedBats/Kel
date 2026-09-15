# Assembles a Kel release folder from built artifacts and writes the manifest + SHA-256 sums.
# It never modifies existing frozen release folders: output is always a fresh directory.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/freeze-release.ps1 -PackageDir <electron-builder dir> [-AppAsar <file>] [-RuntimeDir <dir>] [-OutDir dist/release]
param(
    [Parameter(Mandatory=$true)][string]$PackageDir,
    [string]$AppAsar = "",
    [string]$RuntimeDir = "",
    [string]$OutDir = "dist/release"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
if ([string]::IsNullOrEmpty($AppAsar)) { $AppAsar = Join-Path $repo "dist/app.asar" }
if ([string]::IsNullOrEmpty($RuntimeDir)) { $RuntimeDir = Join-Path $repo "dist/runtime/KelEngine" }
$out = Join-Path $repo $OutDir
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
Copy-Item -Recurse $PackageDir $out
Copy-Item -Force $AppAsar (Join-Path $out "resources/app.asar")
Copy-Item -Recurse -Force $RuntimeDir (Join-Path $out "resources/kel-engine")
$targets = @("Kel.exe", "resources/app.asar", "resources/kel-engine/KelEngine.exe")
$sums = @()
foreach ($t in $targets) { $sums += (Get-FileHash -Algorithm SHA256 (Join-Path $out $t)).Hash }
$sums | Set-Content -Encoding ascii (Join-Path $out "SHA256Sums.txt.txt")
$manifest = @(
    "# Kel Release Manifest",
    "",
    "Assembled: $(Get-Date -Format o)",
    "Scope: release folder assembled from built artifacts by scripts/freeze-release.ps1.",
    "",
    "Key hashes (see SHA256Sums.txt.txt, in order):",
    "- Kel.exe                                $($sums[0].Substring(0,8))...",
    "- resources/app.asar                     $($sums[1].Substring(0,8))...",
    "- resources/kel-engine/KelEngine.exe      $($sums[2].Substring(0,8))...",
    ""
)
$manifest | Set-Content -Encoding utf8 (Join-Path $out "RELEASE_MANIFEST.md.txt")
Write-Host "Release assembled at $out"
Write-Host "Note: byte-identical rebuilds are not promised (timestamps, ordering, toolchain); verify with scripts/verify-release.ps1."
