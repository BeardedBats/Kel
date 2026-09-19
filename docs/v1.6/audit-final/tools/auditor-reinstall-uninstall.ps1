$ErrorActionPreference = 'Continue'
$installer = 'C:/Users/Nick/Desktop/Kel/kel-v16-final-audit/build-output/package-audit/Kel-1.6.0-win-x64.exe'
$target = 'C:\Users\Nick\KelAuditInstall'
$out = 'C:\Users\Nick\Desktop\Kel\kel-v16-final-audit\docs\v1.6\audit-final\evidence\auditor-reinstall-uninstall.log'

$lines = New-Object System.Collections.ArrayList
function Log([string]$s) { [void]$lines.Add($s); Write-Output $s }

Log '== kel processes before =='
$procs = Get-Process -Name 'Kel' -ErrorAction SilentlyContinue
if ($procs) {
  $procs | ForEach-Object { Log ("  pid=" + $_.Id + " path=" + $_.Path) }
  $procs | Where-Object { $_.Path -like '*KelAuditInstall*' } | ForEach-Object { Log ("  stopping audit instance pid=" + $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
} else { Log '  none' }

Log '== reinstall over existing (no pre-delete) =='
$p = Start-Process -FilePath $installer -ArgumentList '/S', '/D=C:\Users\Nick\KelAuditInstall' -Wait -PassThru
Log ("reinstall exit: " + $p.ExitCode)
Start-Sleep -Seconds 2
Log ("Kel.exe present after reinstall: " + (Test-Path (Join-Path $target 'Kel.exe')))

Log '== uninstall =='
$u = Start-Process -FilePath (Join-Path $target 'Uninstall Kel.exe') -ArgumentList '/S' -Wait -PassThru
Log ("uninstall exit: " + $u.ExitCode)
Start-Sleep -Seconds 5
Log ("target dir present after uninstall: " + (Test-Path $target))
Log ("desktop shortcut remaining: " + (Test-Path (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Kel.lnk')))
Log ("start menu link remaining: " + (Test-Path (Join-Path ([Environment]::GetFolderPath('Programs')) 'Kel.lnk')))
$arp = Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue | ForEach-Object {
  $q = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
  if ($q.DisplayName -match '^Kel$') { $_.PSChildName }
}
Log ("ARP entries remaining: " + (($arp | Measure-Object).Count))
Log ("isolated audit data root kept (auditor-provided KEL_DATA_DIR): " + (Test-Path 'C:\Users\Nick\kel-audit-root'))

$lines | Set-Content -Path $out -Encoding UTF8
Write-Output ('log written: ' + $out)
