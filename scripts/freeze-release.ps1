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
# V1.5: no runtime/debug leftovers in a frozen release (defensive; the package is built clean).
Get-ChildItem -File $out -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force
# Positional order matters: scripts/verify-release.ps1 reads the first three hashes in this order.
$targets = @("Kel.exe", "resources/app.asar", "resources/kel-engine/KelEngine.exe",
             "resources/bundled-aioncore/win32-x64/aioncore.exe")
$sums = @()
foreach ($t in $targets) { $sums += (Get-FileHash -Algorithm SHA256 (Join-Path $out $t)).Hash }
$sums | Set-Content -Encoding ascii (Join-Path $out "SHA256Sums.txt.txt")
# V1.5 addition: a sha256sum-compatible copy with explicit paths (the legacy positional file is
# unchanged so scripts/verify-release.ps1 and every frozen prior release keep working as-is).
$lines = @()
for ($i = 0; $i -lt $targets.Count; $i++) { $lines += "$($sums[$i])  $($targets[$i])" }
$lines | Set-Content -Encoding ascii (Join-Path $out "SHA256Sums.txt")
$manifest = @(
    "# Kel Release Manifest",
    "",
    "Assembled: $(Get-Date -Format o)",
    "Scope: release folder assembled from built artifacts by scripts/freeze-release.ps1.",
    "",
    "Key hashes (positional order matches SHA256Sums.txt.txt, the file scripts/verify-release.ps1 reads):",
    "- Kel.exe                                          $($sums[0].Substring(0,8))...",
    "- resources/app.asar                               $($sums[1].Substring(0,8))...",
    "- resources/kel-engine/KelEngine.exe                $($sums[2].Substring(0,8))...",
    "- resources/bundled-aioncore/win32-x64/aioncore.exe $($sums[3].Substring(0,8))...",
    "",
    "Also written: SHA256Sums.txt (V1.5) - the same hashes as 'HASH  path' lines for standard tooling.",
    ""
)
$manifest | Set-Content -Encoding utf8 (Join-Path $out "RELEASE_MANIFEST.md.txt")
Write-Host "Release assembled at $out"
Write-Host "Note: byte-identical rebuilds are not promised (timestamps, ordering, toolchain); verify with scripts/verify-release.ps1."
