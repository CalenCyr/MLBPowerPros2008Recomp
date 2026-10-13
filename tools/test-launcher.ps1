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
foreach ($pass in 1..2) {
  if ($pass -eq 2) { $info.Environment['WIICOMPILED_LAUNCHER_PROBE_RELOAD'] = '1' }
  $process = [System.Diagnostics.Process]::Start($info)
  $stdout = $process.StandardOutput.ReadToEndAsync()
  $stderr = $process.StandardError.ReadToEndAsync()
  try {
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Launcher integration test timed out.' }
    $out = $stdout.GetAwaiter().GetResult()
    $err = $stderr.GetAwaiter().GetResult()
    Set-Content -LiteralPath (Join-Path $probe "stdout-$pass.log") -Value $out
    Set-Content -LiteralPath (Join-Path $probe "stderr-$pass.log") -Value $err
    $err -split "`r?`n" | Where-Object { $_ -like 'launcher-probe*' } | Write-Output
    if ($process.ExitCode -ne 0 -or $err -notmatch 'launcher-probe COMPLETE') {
        throw "Launcher integration test failed (exit $($process.ExitCode)); logs: $probe"
    }
  } finally { $process.Dispose() }
}
Write-Output "Launcher integration and reload passed. Logs: $probe"
