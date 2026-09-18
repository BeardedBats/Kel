# REL-01 validation fixture: exercises the identical staging/hash/load logic as a release freeze
# WITHOUT producing a release. Positive path: freeze + verify agree on the load path. Negative path:
# a package that bundles a different engine than the frozen runtime is refused (non-zero exit).
param()
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$stub = Join-Path $repo "dist/validation-package"
$runtime = Join-Path $repo "dist/runtime/KelEngine"
$out = Join-Path $repo "dist/validation-freeze"
$freeze = Join-Path $PSScriptRoot "freeze-release.ps1"
$verify = Join-Path $PSScriptRoot "verify-release.ps1"
if (-not (Test-Path (Join-Path $runtime "KelEngine.exe"))) {
    throw "Build the runtime first: powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1"
}
if (Test-Path $stub) { Remove-Item -Recurse -Force $stub }
New-Item -ItemType Directory -Force -Path (Join-Path $stub "resources/kel-engine") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stub "resources/bundled-aioncore/win32-x64") | Out-Null
Set-Content -Path (Join-Path $stub "Kel.exe") -Value "synthetic"
Set-Content -Path (Join-Path $stub "resources/app.asar") -Value "synthetic"
Set-Content -Path (Join-Path $stub "resources/bundled-aioncore/win32-x64/aioncore.exe") -Value "synthetic"
Copy-Item -Recurse -Force $runtime (Join-Path $stub "resources/kel-engine")
Write-Host "-- positive: freeze"
& powershell -ExecutionPolicy Bypass -File $freeze -PackageDir $stub -AppAsar (Join-Path $stub "resources/app.asar") -RuntimeDir $runtime -OutDir "dist/validation-freeze"
if ($LASTEXITCODE -ne 0) { throw "freeze-release.ps1 failed on the positive path (exit $LASTEXITCODE)" }
Write-Host "-- positive: verify"
& powershell -ExecutionPolicy Bypass -File $verify -ReleaseDir $out -Manifest (Join-Path $out "SHA256Sums.txt.txt")
if ($LASTEXITCODE -ne 0) { throw "verify-release.ps1 failed on the positive path (exit $LASTEXITCODE)" }
Write-Host "-- negative: a package bundling a different engine must be refused"
Add-Content -Path (Join-Path $stub "resources/kel-engine/KelEngine.exe") -Value "tampered"
& powershell -ExecutionPolicy Bypass -File $freeze -PackageDir $stub -AppAsar (Join-Path $stub "resources/app.asar") -RuntimeDir $runtime -OutDir "dist/validation-freeze"
if ($LASTEXITCODE -eq 0) { throw "REL-01 validation FAILED: the freeze accepted a package bundling a different engine." }
Write-Host "REL-01 validation passed: load-path hash == staged runtime hash; divergence refused (exit $LASTEXITCODE)."
