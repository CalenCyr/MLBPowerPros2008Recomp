# SPDX-License-Identifier: GPL-3.0-or-later
param([string]$BuildDirectory = (Join-Path $PSScriptRoot '..\local\wiicompiled-mlb\build'))
$ErrorActionPreference = 'Stop'
$build = (Resolve-Path -LiteralPath $BuildDirectory).Path
$root = Split-Path -Parent $PSScriptRoot
$probe = Join-Path $root ('local\analysis\launcher-tests\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Force (Join-Path $probe 'UserData') | Out-Null
Copy-Item -LiteralPath (Join-Path $build 'WiiCompiled.exe') -Destination $probe
Get-ChildItem -LiteralPath $build -Filter '*.dll' | Copy-Item -Destination $probe
if (Test-Path -LiteralPath (Join-Path $build 'launcher')) {
    Copy-Item -LiteralPath (Join-Path $build 'launcher') -Destination $probe -Recurse
}
Set-Content -LiteralPath (Join-Path $probe 'portable.txt') -Value 'Isolated launcher integration test'
@'
[video]
window_width = 1280
window_height = 720
graphics_api = 'd3d12'
resolution_multiplier = 1
[launcher]
show_on_startup = true
'@ | Set-Content -LiteralPath (Join-Path $probe 'UserData\Config.toml')
$info = [System.Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $probe 'WiiCompiled.exe'
$info.WorkingDirectory = $probe
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
foreach ($key in @('WIICOMPILED_SKIP_LAUNCHER','WIICOMPILED_BENCH','WIICOMPILED_MATCH_BENCH',
                   'WIICOMPILED_PAD_SCRIPT','WIICOMPILED_KPAD_SCRIPT','WIICOMPILED_LAUNCHER_SELECT',
                   'WIICOMPILED_LAUNCHER_PROBE_RELOAD','WIICOMPILED_LAUNCHER_CONTROL_SECTION',
                   'WIICOMPILED_LAUNCHER_ACTION','WIICOMPILED_LAUNCHER_ROW')) {
    $info.Environment.Remove($key) | Out-Null
}
$info.Environment['WIICOMPILED_LAUNCHER_PAGE'] = 'controls'
$info.Environment['WIICOMPILED_LAUNCHER_PROBE'] = '1'
# Passes: controls page, reload in a new process, then pad navigation of the settings list.
foreach ($pass in 1..3) {
  if ($pass -eq 2) { $info.Environment['WIICOMPILED_LAUNCHER_PROBE_RELOAD'] = '1' }
  if ($pass -eq 3) {
    $info.Environment.Remove('WIICOMPILED_LAUNCHER_PROBE_RELOAD') | Out-Null
    $info.Environment['WIICOMPILED_LAUNCHER_PAGE'] = 'settings'
    $info.Environment['WIICOMPILED_LAUNCHER_PROBE'] = 'nav'
  }
  $process = [System.Diagnostics.Process]::Start($info)
  $stdout = $process.StandardOutput.ReadToEndAsync()
  $stderr = $process.StandardError.ReadToEndAsync()
  try {
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Launcher integration test timed out.' }
    $out = $stdout.GetAwaiter().GetResult()
    $err = $stderr.GetAwaiter().GetResult()
    Set-Content -LiteralPath (Join-Path $probe "stdout-$pass.log") -Value $out
    Set-Content -LiteralPath (Join-Path $probe "stderr-$pass.log") -Value $err
    $err -split "`r?`n" | Where-Object { $_ -like 'launcher-probe*' -or $_ -like 'launcher-nav*' } | Write-Output
    if ($process.ExitCode -ne 0 -or $err -notmatch 'launcher-(probe|nav) COMPLETE') {
        throw "Launcher integration test failed (exit $($process.ExitCode)); logs: $probe"
    }
  } finally { $process.Dispose() }
}
# Passed: drop the ~130 MB copy of the game binaries, keep only the small logs and config.
Get-ChildItem -LiteralPath $probe -Force | Where-Object { $_.Name -notlike '*.log' -and $_.Name -ne 'UserData' } |
    Remove-Item -Recurse -Force
Write-Output "Launcher integration, reload and pad navigation passed. Logs: $probe"
