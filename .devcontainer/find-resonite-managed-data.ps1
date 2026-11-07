<#
.SYNOPSIS
Find the folder of the running Resonite that holds FrooxEngine.dll, and print the
WSL command that copies its DLLs (copy-resonite-managed-data.bash). Issue #326.

.DESCRIPTION
Run it on Windows by hand, for the first setup and after Resonite updates.
It only reads: it does not change the Resonite install, Windows settings or the
execution policy. It never picks one of several candidates for you; pass
-InstallPath or -ManagedPath instead. The DLL file version it prints is for
reference only and is not the Resonite version. See .devcontainer/README.md.

Supported: Windows PowerShell 5.1 and PowerShell 7.
Exit codes: 0 found exactly one folder, 1 could not decide, 2 bad arguments.

.PARAMETER InstallPath
Resonite install folder to search instead of the running process's folder.

.PARAMETER ManagedPath
Folder that holds FrooxEngine.dll directly. Skips the search.

.PARAMETER ResoniteVersion
The Resonite version you confirmed, used in the printed WSL command.
#>
[CmdletBinding()]
param(
  [string]$InstallPath,
  [string]$ManagedPath,
  [string]$ResoniteVersion
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Find([string]$Message, [int]$Code) {
  [Console]::Error.WriteLine("find-resonite-managed-data: $Message")
  exit $Code
}

# Quote for a bash single-quoted string: ' becomes '\''
function ConvertTo-BashQuoted([string]$Text) {
  return "'" + $Text.Replace("'", "'\''") + "'"
}

if ($InstallPath -and $ManagedPath) {
  Stop-Find 'Pass -InstallPath or -ManagedPath, not both.' 2
}
if ($ResoniteVersion -and ($ResoniteVersion -cnotmatch '^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$')) {
  Stop-Find "Invalid -ResoniteVersion '$ResoniteVersion': use 1-64 letters, digits, '.', '_', '+' or '-', starting with a letter or digit." 2
}

if ($ManagedPath) {
  if (-not (Test-Path -LiteralPath $ManagedPath -PathType Container)) {
    Stop-Find "-ManagedPath is not a folder: $ManagedPath" 2
  }
  $managed = (Get-Item -LiteralPath $ManagedPath).FullName
  if (-not (Test-Path -LiteralPath (Join-Path $managed 'FrooxEngine.dll') -PathType Leaf)) {
    Stop-Find "FrooxEngine.dll is not directly under -ManagedPath: $managed" 1
  }
} else {
  if ($InstallPath) {
    if (-not (Test-Path -LiteralPath $InstallPath -PathType Container)) {
      Stop-Find "-InstallPath is not a folder: $InstallPath" 2
    }
    $install = (Get-Item -LiteralPath $InstallPath).FullName
  } else {
    $processes = @(Get-Process | Where-Object { $_.ProcessName -like 'Resonite*' })
    if ($processes.Count -eq 0) {
      Stop-Find 'Resonite is not running. Start Resonite, or pass -InstallPath <install folder>.' 1
    }
    $installs = @(
      $processes |
        ForEach-Object { try { $_.Path } catch { $null } } |
        Where-Object { $_ } |
        ForEach-Object { Split-Path -Parent $_ } |
        Sort-Object -Unique
    )
    if ($installs.Count -eq 0) {
      Stop-Find 'Found a Resonite process but could not read its path. Pass -InstallPath <install folder>.' 1
    }
    if ($installs.Count -gt 1) {
      $list = ($installs | ForEach-Object { "  $_" }) -join [Environment]::NewLine
      Stop-Find ("Resonite processes run from more than one folder. Pass -InstallPath with the one you use:" + [Environment]::NewLine + $list) 1
    }
    $install = $installs[0]
  }

  $walkErrors = $null
  $found = @(
    Get-ChildItem -LiteralPath $install -Filter 'FrooxEngine.dll' -File -Recurse -ErrorAction SilentlyContinue -ErrorVariable walkErrors |
      Where-Object { $_.Name -eq 'FrooxEngine.dll' }
  )
  $dirs = @($found | ForEach-Object { $_.DirectoryName } | Sort-Object -Unique)
  if ($dirs.Count -eq 0) {
    Stop-Find "No FrooxEngine.dll under $install. Pass -ManagedPath <folder that holds FrooxEngine.dll>." 1
  }
  if ($dirs.Count -gt 1) {
    $list = ($dirs | ForEach-Object { "  $_" }) -join [Environment]::NewLine
    Stop-Find ("More than one folder holds FrooxEngine.dll. Pass -ManagedPath with the one the running Resonite uses:" + [Environment]::NewLine + $list) 1
  }
  if ($walkErrors -and @($walkErrors).Count -gt 0) {
    Stop-Find ("Some folders under $install could not be read, so other candidates may exist. Check and pass -ManagedPath:" + [Environment]::NewLine + "  " + $dirs[0]) 1
  }
  $managed = $dirs[0]
}

$dllCount = @(Get-ChildItem -LiteralPath $managed -Filter '*.dll' -File | Where-Object { $_.Name -like '*.dll' }).Count
$fileVersion = (Get-Item -LiteralPath (Join-Path $managed 'FrooxEngine.dll')).VersionInfo.FileVersion
if (-not $fileVersion) { $fileVersion = '(none)' }
if ($ResoniteVersion) { $versionArg = ConvertTo-BashQuoted $ResoniteVersion } else { $versionArg = "'<Resonite version>'" }

Write-Output "Source folder: $managed"
Write-Output "DLL files directly under it: $dllCount"
Write-Output "FrooxEngine.dll file version (reference only, not the Resonite version): $fileVersion"
Write-Output ''
Write-Output 'Do not copy while Resonite is updating. In WSL (outside the Dev Container), run:'
Write-Output ''
Write-Output ('bash <checkout>/.devcontainer/copy-resonite-managed-data.bash --source "$(wslpath -u ' + (ConvertTo-BashQuoted $managed) + ')" --version ' + $versionArg)
Write-Output ''
Write-Output '<checkout> is the WSL path of create-reso-world. Use the Resonite version shown by Resonite or by resoloop status.'
exit 0
