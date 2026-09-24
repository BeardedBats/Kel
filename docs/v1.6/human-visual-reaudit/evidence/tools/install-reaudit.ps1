# Dedicated audit install step — Kel V1.6 human-visual delta re-audit.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File install-reaudit.ps1
# Purpose: stop any Kel instances, clear the install registration (backed up at
# C:\Users\Nick\KelVisualReauditRuns\registry-backup\), then silent-install the FRESH re-audit
# package into the dedicated audit location with no reuse of prior installs.

$ErrorActionPreference = 'Continue'
$installer = 'C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-reaudit\dist\package-r12\Kel-1.6.0-win-x64.exe'
$target = 'C:\Users\Nick\KelVisualReauditInstall'

Write-Output "== stop Kel processes =="
Get-Process -Name 'Kel', 'KelEngine' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Output "== clear registration keys (fresh path; backups already taken) =="
& reg.exe delete 'HKCU\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a' /f 2>$null | Out-Null
& reg.exe delete 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\9280710d-02b9-55d6-ba7a-2b7d6f91d60a' /f 2>$null | Out-Null

Write-Output "== silent install -> $target =="
$p = Start-Process -FilePath $installer -ArgumentList '/S', "/D=$target" -Wait -PassThru
Write-Output ("INSTALL_EXIT=" + $p.ExitCode)
Start-Sleep -Seconds 6

Write-Output "== installed files (top) =="
Get-ChildItem $target -ErrorAction SilentlyContinue | Select-Object -First 20 -ExpandProperty Name

Write-Output "== installed hashes =="
if (Test-Path "$target\Kel.exe") { (Get-FileHash "$target\Kel.exe" -Algorithm SHA256).Hash + '  Kel.exe' }
if (Test-Path "$target\resources\kel-engine\KelEngine.exe") { (Get-FileHash "$target\resources\kel-engine\KelEngine.exe" -Algorithm SHA256).Hash + '  kel-engine/KelEngine.exe' }

Write-Output "== version =="
(Get-Item "$target\Kel.exe").VersionInfo | Format-List ProductName, ProductVersion, FileVersion

Write-Output "== registry now =="
Get-ItemProperty 'HKCU:\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a' -ErrorAction SilentlyContinue | Format-List InstallLocation

Write-Output "== preserved installs (must match pre-install values) =="
(Get-FileHash 'C:\Users\Nick\KelV16ReviewInstall\Kel.exe' -Algorithm SHA256).Hash + '  KelV16ReviewInstall/Kel.exe'
(Get-FileHash 'C:\Users\Nick\KelV16ReviewInstall\resources\kel-engine\KelEngine.exe' -Algorithm SHA256).Hash + '  KelV16ReviewInstall/engine'
(Get-FileHash 'C:\Users\Nick\KelVisualFixInstall\Kel.exe' -Algorithm SHA256).Hash + '  KelVisualFixInstall/Kel.exe'
(Get-FileHash 'C:\Users\Nick\KelVisualFixInstall\resources\kel-engine\KelEngine.exe' -Algorithm SHA256).Hash + '  KelVisualFixInstall/engine'

Write-Output "== Kel shortcuts =="
$sh = New-Object -ComObject WScript.Shell
foreach ($p2 in @("$env:USERPROFILE\Desktop", "$env:PUBLIC\Desktop", "$env:APPDATA\Microsoft\Windows\Start Menu\Programs")) {
  Get-ChildItem "$p2\*.lnk" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'Kel*' } | ForEach-Object {
    $s = $sh.CreateShortcut($_.FullName)
    Write-Output ("{0} -> {1}" -f $_.FullName, $s.TargetPath)
  }
}
Write-Output "== done =="
