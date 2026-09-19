param(
  [Parameter(Mandatory = $true)][string]$Installer,
  [Parameter(Mandatory = $true)][string]$Target
)
$ErrorActionPreference = 'Continue'

$uninstallRoot = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
Write-Output "== cleaning stale ARP entries for DisplayName 'Kel' (from the mangled earlier attempt)"
Get-ChildItem $uninstallRoot -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
  if ($p.DisplayName -match '^Kel$') {
    Write-Output ("  removing key " + $_.PSChildName + " (InstallLocation='" + $p.InstallLocation + "')")
    Remove-Item $_.PSPath -Recurse -Force -ErrorAction SilentlyContinue
  }
}

if (Test-Path $Target) { Remove-Item -Recurse -Force $Target -ErrorAction SilentlyContinue }
Write-Output "== installer: $Installer"
Write-Output "== target:    $Target"
$proc = Start-Process -FilePath $Installer -ArgumentList '/S', "/D=$Target" -Wait -PassThru
Write-Output "installer exit: $($proc.ExitCode)"

$checks = [ordered]@{}
$checks['Kel.exe'] = Test-Path (Join-Path $Target 'Kel.exe')
$checks['Uninstall'] = (Get-ChildItem $Target -Filter 'Uninstall*.exe' -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
$checks['kel-engine'] = Test-Path (Join-Path $Target 'resources\kel-engine\KelEngine.exe')
$checks['app.asar'] = Test-Path (Join-Path $Target 'resources\app.asar')
$checks.GetEnumerator() | ForEach-Object { Write-Output ("check {0}: {1}" -f $_.Key, $_.Value) }

if (Test-Path (Join-Path $Target 'Kel.exe')) {
  $exe = Get-Item (Join-Path $Target 'Kel.exe')
  $v = $exe.VersionInfo
  Write-Output "ProductName:    $($v.ProductName)"
  Write-Output "CompanyName:    $($v.CompanyName)"
  Write-Output "FileVersion:    $($v.FileVersion)"
  Write-Output "ProductVersion: $($v.ProductVersion)"
  $engineHash = (Get-FileHash (Join-Path $Target 'resources\kel-engine\KelEngine.exe') -Algorithm SHA256).Hash
  Write-Output "engine sha256: $engineHash"
}

$desktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Kel.lnk'
$startLnk = Join-Path ([Environment]::GetFolderPath('Programs')) 'Kel.lnk'
Write-Output "desktop shortcut: $([bool](Test-Path $desktopLnk))"
Write-Output "start menu link:  $([bool](Test-Path $startLnk))"

Write-Output "== ARP after install:"
Get-ChildItem $uninstallRoot -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
  if ($p.DisplayName -match '^Kel$') {
    Write-Output ("  DisplayName={0} DisplayVersion={1} Publisher={2} InstallLocation={3}" -f $p.DisplayName, $p.DisplayVersion, $p.Publisher, $p.InstallLocation)
    Write-Output ("  UninstallString={0}" -f $p.UninstallString)
  }
}
Write-Output "== target dir listing (first 20):"
Get-ChildItem $Target -ErrorAction SilentlyContinue | Select-Object -First 20 -ExpandProperty Name
