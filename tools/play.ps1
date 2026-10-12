# SPDX-License-Identifier: GPL-3.0-or-later
# Manual play in a window, with a profile separate from the automated probes.
# A fresh profile has no input INI, so Dolphin applies its keyboard/mouse defaults
# with the Nunchuk attached (WiimoteEmu.cpp / Nunchuk.cpp LoadDefaults).
param([ValidateSet('llvm', 'clang')][string]$Module = 'llvm',
      [switch]$DualCore,
      [switch]$Match,
      [switch]$Pad,
      [string]$LoadState = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$runner = Join-Path $root 'local/build/moderngekko/Release/moderngekko-run.exe'
$dll = Join-Path $root $(if ($Module -eq 'llvm') { 'local/build/runtime-module-llvm-fixed/gRL8E54_recomp.dll' }
                         else { 'local/build/runtime-module-rel-clang/gRL8E54_recomp.dll' })
foreach ($path in @($runner, $dll, (Join-Path $root 'local/disc/DATA'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Falta: $path" }
}
if ($Match) { $LoadState = 'local/analysis/boot-probe-20261008-205240-719/control/artifacts/pitch-result-state.sav' }

$profile = Join-Path $root 'local/play-user'
$config = Join-Path $profile 'Config'
New-Item -ItemType Directory -Force -Path $config | Out-Null
foreach ($name in 'WiimoteNew.ini', 'GCPadNew.ini') {
    $ini = Join-Path $config $name
    if ((Test-Path -LiteralPath $ini) -and (Get-Content -LiteralPath $ini -Raw) -match 'CodexAutomation') {
        throw "$ini es un perfil de automatización sin controles; bórralo para usar los predeterminados."
    }
}
# -Pad: XInput gamepad (DS4Windows exposes a DualSense/DualShock as an Xbox 360 pad).
# Without -Pad, a previous pad mapping is removed so Dolphin's keyboard defaults return.
$wiimoteIni = Join-Path $config 'WiimoteNew.ini'
if ($Pad) {
    @('[Wiimote1]', 'Device = XInput/0/Gamepad', 'Source = 1',
      'Buttons/A = `Button A`', 'Buttons/B = `Trigger R`', 'Buttons/1 = `Button X`', 'Buttons/2 = `Button Y`',
      'Buttons/- = Back', 'Buttons/+ = Start', 'Buttons/Home = `Thumb R`',
      'D-Pad/Up = `Pad N`', 'D-Pad/Down = `Pad S`', 'D-Pad/Left = `Pad W`', 'D-Pad/Right = `Pad E`',
      'IR/Up = `Right Y+`', 'IR/Down = `Right Y-`', 'IR/Left = `Right X-`', 'IR/Right = `Right X+`',
      'Shake/X = `Button B`', 'Shake/Y = `Button B`', 'Shake/Z = `Button B`',
      'Extension = Nunchuk',
      'Nunchuk/Buttons/C = `Shoulder L`', 'Nunchuk/Buttons/Z = `Trigger L`',
      'Nunchuk/Stick/Up = `Left Y+`', 'Nunchuk/Stick/Down = `Left Y-`',
      'Nunchuk/Stick/Left = `Left X-`', 'Nunchuk/Stick/Right = `Left X+`',
      'Nunchuk/Shake/X = `Shoulder R`', 'Nunchuk/Shake/Y = `Shoulder R`', 'Nunchuk/Shake/Z = `Shoulder R`') |
        Set-Content -LiteralPath $wiimoteIni -Encoding ascii
} elseif ((Test-Path -LiteralPath $wiimoteIni) -and (Get-Content -LiteralPath $wiimoteIni -Raw) -match 'XInput/0/Gamepad') {
    Remove-Item -LiteralPath $wiimoteIni
}
# [Core] CPUThread: dual core (separate GPU thread) is faster but not deterministic.
$dolphinIni = Join-Path $config 'Dolphin.ini'
$lines = [System.Collections.Generic.List[string]]@(if (Test-Path -LiteralPath $dolphinIni) { Get-Content -LiteralPath $dolphinIni } else { @() })
$lines.RemoveAll({ param($line) $line -match '^CPUThread\s*=' }) | Out-Null
$core = $lines.IndexOf('[Core]')
if ($core -lt 0) { $lines.Insert(0, '[Core]'); $core = 0 }
$lines.Insert($core + 1, "CPUThread = $(if ($DualCore) { 'True' } else { 'False' })")
Set-Content -LiteralPath $dolphinIni -Value $lines -Encoding ascii

$env:STATICRECOMP_POWERPROS_SCHEDULER_IDLE = '1'
$env:STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS = '1'
$arguments = @('--game', (Join-Path $root 'local/disc/DATA'), '--module', $dll, '--user-dir', $profile,
               '--graphics', 'Vulkan', '--no-mods')
if ($LoadState) { $arguments += @('--load-state', (Resolve-Path -LiteralPath $LoadState).Path) }

Write-Host "Módulo: $Module  Dual core: $([bool]$DualCore)  Perfil: $profile"
if ($Pad) {
    Write-Host 'Mando (PS5 vía DS4Windows): A = Cruz  B = R2  1 = Cuadrado  2 = Triángulo  - = Share/Create  + = Options  Home = R3'
    Write-Host '         Cruceta = cruceta  Puntero = stick derecho  Agitar Wiimote = Círculo'
    Write-Host 'Nunchuk: Stick = stick izquierdo  C = L1  Z = L2  Agitar Nunchuk = R1'
} else {
    Write-Host 'Wiimote: A = clic izq.  B = clic der.  1/2 = teclas 1/2  - = Q  + = E  Home = Enter'
    Write-Host '         Cruceta = flechas  Puntero = ratón  Agitar = clic central'
    Write-Host 'Nunchuk: Stick = W/A/S/D  C = Ctrl izq.  Z = Shift izq.'
}
# Runner diagnostics go to stderr; keep them in a per-session log for bug reports.
$log = Join-Path $root ('local/analysis/play-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$quoted = $arguments | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }
$process = Start-Process -FilePath $runner -ArgumentList $quoted -NoNewWindow -PassThru `
    -RedirectStandardOutput "$log.out.log" -RedirectStandardError "$log.err.log"
$null = $process.Handle
Write-Host "Juego abierto (PID $($process.Id)). Log: $log.err.log"
$process.WaitForExit()
Write-Host "Cerrado con código $($process.ExitCode)."
