# SPDX-License-Identifier: GPL-3.0-or-later
param([int]$Seconds = 10, [Alias('SnapshotMEM1')][switch]$SnapshotMemory,
      [ValidateSet('Null', 'Vulkan')][string]$Graphics = 'Null', [switch]$Screenshot,
      [switch]$RelModule, [int]$CaptureIntervalSeconds = 0, [string]$LoadState = '',
      [switch]$OptimizedModule, [switch]$ProfileFallback, [switch]$SchedulerIdleSkip,
      [switch]$ProfileDispatchTiming,
      [switch]$CacheBatch,
      [switch]$SkipEmptyModHooks,
      [switch]$DualCore,
      [switch]$ClangModule, [switch]$Lockstep, [switch]$LockstepAlignCycles, [string]$LockstepAlignRange = '0x80000000:0x80575580',
      [long]$LockstepStart = 0, [long]$LockstepLimit = 0,
      [uint32]$LockstepTracePC = 0,
      [string]$RunnerPath = '', [string]$ModulePath = '', [switch]$PassThru)
$ErrorActionPreference = 'Stop'
if ($Seconds -lt 1 -or $Seconds -gt 900) { throw 'Seconds debe estar entre 1 y 900.' }
if ($CaptureIntervalSeconds -lt 0 -or $CaptureIntervalSeconds -gt 900) { throw 'CaptureIntervalSeconds debe estar entre 0 y 900.' }
if ($LockstepStart -lt 0 -or $LockstepLimit -lt 0 -or ($LockstepLimit -and $LockstepLimit -le $LockstepStart)) { throw 'Ventana lockstep inválida.' }
$taskRoot = Split-Path $PSScriptRoot -Parent
function Send-ProbeCommand([string]$Name, [string]$Content) {
    & (Join-Path $PSScriptRoot 'send-probe-command.ps1') -ProbeRoot $probeRoot -Name $Name -Content $Content
}
Set-Location -LiteralPath $taskRoot
$runner = Join-Path $taskRoot 'local/build/moderngekko/Release/moderngekko-run.exe'
if ($RunnerPath) {
    $runner = (Resolve-Path -LiteralPath $RunnerPath).Path
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) { throw 'RunnerPath debe ser un ejecutable existente.' }
}
$module = Join-Path $taskRoot 'local/build/runtime-module/Release/gRL8E54_recomp.dll'
if ($OptimizedModule -and -not $RelModule) { throw 'OptimizedModule requiere RelModule.' }
if ($RelModule) {
    $module = Join-Path $taskRoot 'local/build/runtime-module-rel/Release/gRL8E54_recomp.dll'
    if ($OptimizedModule) {
        $module = Join-Path $taskRoot 'local/build/runtime-module-rel-optimized/Release/gRL8E54_recomp.dll'
        $moduleCache = Get-Content -LiteralPath (Join-Path $taskRoot 'local/build/runtime-module-rel-optimized/CMakeCache.txt') -Raw
        if ($moduleCache -notmatch '(?m)^POWERPROS_OPTIMIZE_MODULE:BOOL=ON\r?$') {
            throw 'El módulo solicitado no tiene habilitada su optimización.'
        }
    }
    $baseCache = Get-Content -LiteralPath (Join-Path $taskRoot 'local/build/moderngekko/CMakeCache.txt') -Raw
    if ($baseCache -notmatch '(?m)^POWERPROS_FIXED_REL_HEADER:STRING=0x80575580u?\r?$') {
        throw 'El módulo REL requiere la base preparada con tools/runtime-rel.ps1.'
    }
}
if ($ClangModule) {
    if (-not $RelModule -or -not $OptimizedModule) { throw 'ClangModule requiere RelModule y OptimizedModule.' }
    $module = Join-Path $taskRoot 'local/build/runtime-module-rel-clang/gRL8E54_recomp.dll'
    $clangCache = Get-Content -LiteralPath (Join-Path $taskRoot 'local/build/runtime-module-rel-clang/CMakeCache.txt') -Raw
    if ($clangCache -notmatch '(?m)^POWERPROS_OPTIMIZE_MODULE:BOOL=ON\r?$' -or
        $clangCache -notmatch '(?m)^CMAKE_C_COMPILER:(FILEPATH|STRING|UNINITIALIZED)=.*clang-cl.exe\r?$') {
        throw 'La alternativa Clang no tiene la configuración esperada.'
    }
}
if ($ModulePath) {
    if (-not ($ClangModule -and $OptimizedModule -and $RelModule)) {
        throw 'ModulePath experimental requiere ClangModule, OptimizedModule y RelModule.'
    }
    $module = (Resolve-Path -LiteralPath $ModulePath).Path
    if (-not (Test-Path -LiteralPath $module -PathType Leaf)) { throw 'ModulePath debe ser una DLL existente.' }
}
if ($Lockstep -and ($CacheBatch -or $SchedulerIdleSkip -or $ProfileDispatchTiming -or $ProfileFallback -or $DualCore)) {
    throw 'Lockstep requiere opciones de rendimiento y otros perfiles desactivados.'
}
if (-not (Test-Path -LiteralPath $runner) -or -not (Test-Path -LiteralPath $module)) {
    throw 'Falta compilar el runtime o su módulo. Ejecuta tools/runtime.ps1.'
}
$moduleHash = (Get-FileHash -LiteralPath $module -Algorithm SHA256).Hash.ToLowerInvariant()
$moduleManifestPath = Join-Path (Split-Path $module -Parent) 'module-build-manifest.json'
if (-not (Test-Path -LiteralPath $moduleManifestPath)) {
    $moduleManifestPath = Join-Path (Split-Path (Split-Path $module -Parent) -Parent) 'module-build-manifest.json'
}
if ($ClangModule -and -not (Test-Path -LiteralPath $moduleManifestPath)) { throw 'Falta el manifiesto de compilación Clang.' }
if (Test-Path -LiteralPath $moduleManifestPath) {
    $manifest = Get-Content -LiteralPath $moduleManifestPath -Raw | ConvertFrom-Json
    if ($manifest.binary_sha256 -ne $moduleHash) { throw 'El manifiesto de compilación no coincide con la DLL.' }
}
$checkedBatchModules = @('393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6',
                         '60a0611c6e528583f67b985cc31d290973cf96666685523eec8c1ab316702865')
if ($CacheBatch -and ($ProfileFallback -or -not $OptimizedModule -or $moduleHash -notin $checkedBatchModules)) {
    throw 'CacheBatch requiere la DLL optimizada comprobada con presupuesto de bucle 256 y perfilado de callbacks desactivado.'
}
$runnerHash = (Get-FileHash -LiteralPath $runner -Algorithm SHA256).Hash.ToLowerInvariant()
$loadStateHash = $null
if ($LoadState) {
    $LoadState = (Resolve-Path -LiteralPath $LoadState).Path
    if (-not (Test-Path -LiteralPath $LoadState -PathType Leaf) -or (Get-Item -LiteralPath $LoadState).Length -eq 0) {
        throw 'El estado de diagnóstico debe ser un archivo no vacío.'
    }
    $loadStateHash = (Get-FileHash -LiteralPath $LoadState -Algorithm SHA256).Hash.ToLowerInvariant()
}
$probeRoot = Join-Path $taskRoot ('local/analysis/boot-probe-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
$controls = Join-Path $probeRoot 'control'
$commands = Join-Path $controls 'commands'
$profile = Join-Path $taskRoot 'local/runtime-probe-user'
New-Item -ItemType Directory -Force -Path $commands,$profile | Out-Null
if (Test-Path -LiteralPath $moduleManifestPath) {
    Copy-Item -LiteralPath $moduleManifestPath -Destination (Join-Path $probeRoot 'module-build-manifest.json')
}
& (Join-Path $PSScriptRoot 'prepare-probe-input.ps1') -Profile $profile
# Always write [Core] CPUThread explicitly: the pinned default is single core (CPU-GPU thread).
$dolphinIni = Join-Path $profile 'Config/Dolphin.ini'
$iniLines = [System.Collections.Generic.List[string]]@(if (Test-Path -LiteralPath $dolphinIni) { Get-Content -LiteralPath $dolphinIni } else { @() })
$cpuThreadLine = 'CPUThread = ' + $(if ($DualCore) { 'True' } else { 'False' })
$coreIndex = $iniLines.IndexOf('[Core]')
if ($coreIndex -lt 0) { $iniLines.Insert(0, '[Core]'); $coreIndex = 0 }
$sectionEnd = $coreIndex + 1
while ($sectionEnd -lt $iniLines.Count -and -not $iniLines[$sectionEnd].StartsWith('[')) { $sectionEnd++ }
$existing = -1
for ($i = $coreIndex + 1; $i -lt $sectionEnd; $i++) { if ($iniLines[$i] -match '^CPUThread\s*=') { $existing = $i } }
if ($existing -ge 0) { $iniLines[$existing] = $cpuThreadLine } else { $iniLines.Insert($coreIndex + 1, $cpuThreadLine) }
New-Item -ItemType Directory -Force -Path (Split-Path $dolphinIni -Parent) | Out-Null
Set-Content -LiteralPath $dolphinIni -Value $iniLines -Encoding ascii
$arguments = @('--game', ('"' + (Join-Path $taskRoot 'local/disc/DATA') + '"'),
    '--module', ('"' + $module + '"'), '--user-dir', ('"' + $profile + '"'),
    '--automation-dir', ('"' + $controls + '"'), '--graphics', $Graphics, '--headless', '--no-mods', '--no-cache-affinity')
$previousTracePath = $env:STATICRECOMP_TRACE_FILE
$previousRelTracePath = $env:STATICRECOMP_REL_TRACE_FILE
$previousFallbackProfile = $env:STATICRECOMP_FALLBACK_PROFILE
$previousDispatchTiming = $env:STATICRECOMP_DISPATCH_TIMING
$previousDispatchSamples = $env:STATICRECOMP_DISPATCH_SAMPLES
$previousSchedulerIdle = $env:STATICRECOMP_POWERPROS_SCHEDULER_IDLE
$previousCacheBatch = $env:STATICRECOMP_POWERPROS_CACHE_BATCH
$previousSkipEmptyModHooks = $env:STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS
$previousLockstep = $env:STATICRECOMP_LOCKSTEP
$previousLockstepLimit = $env:STATICRECOMP_LOCKSTEP_LIMIT
$lockstepOptions = @('START', 'FILTER', 'NODEDUP', 'MAXREPORT', 'STEPCAP', 'TRACE', 'REPEAT', 'WHITELIST', 'ALIGNCYCLES')
$previousLockstepOptions = @{}
foreach ($option in $lockstepOptions) {
    $key = 'STATICRECOMP_LOCKSTEP_' + $option
    $previousLockstepOptions[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
try {
    $env:STATICRECOMP_TRACE_FILE = Join-Path $probeRoot 'native-dispatch.csv'
    $env:STATICRECOMP_REL_TRACE_FILE = Join-Path $probeRoot 'rel-dispatch.csv'
    $env:STATICRECOMP_FALLBACK_PROFILE = $(if ($ProfileFallback) { Join-Path $probeRoot 'fallback-profile.csv' } else { $null })
    $env:STATICRECOMP_DISPATCH_TIMING = $(if ($ProfileDispatchTiming) { Join-Path $probeRoot 'dispatch-timing.csv' } else { $null })
    $env:STATICRECOMP_DISPATCH_SAMPLES = $(if ($ProfileFallback) { '1' } else { $null })
    $env:STATICRECOMP_POWERPROS_SCHEDULER_IDLE = $(if ($SchedulerIdleSkip) { '1' } else { $null })
    $env:STATICRECOMP_POWERPROS_CACHE_BATCH = $(if ($CacheBatch) { '1' } else { $null })
    $env:STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS = $(if ($SkipEmptyModHooks) { '1' } else { $null })
    $env:STATICRECOMP_LOCKSTEP = $(if ($Lockstep) { '1' } else { $null })
    $env:STATICRECOMP_LOCKSTEP_LIMIT = $(if ($Lockstep) { [string]$LockstepLimit } else { $null })
    $lockstepDefaults = @{ START = [string]$LockstepStart; FILTER = ''; NODEDUP = '0'; MAXREPORT = '0'; STEPCAP = '20000'; TRACE = [string]$LockstepTracePC; REPEAT = '0'; WHITELIST = ''; ALIGNCYCLES = $(if ($LockstepAlignCycles) { $LockstepAlignRange } else { '0' }) }
    foreach ($option in $lockstepOptions) { [Environment]::SetEnvironmentVariable('STATICRECOMP_LOCKSTEP_' + $option, $lockstepDefaults[$option], 'Process') }
    $process = Start-Process -FilePath $runner -ArgumentList $arguments -WorkingDirectory (Split-Path $runner -Parent) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $probeRoot 'stdout.log') -RedirectStandardError (Join-Path $probeRoot 'stderr.log')
    # Windows PowerShell 5.1 reports a null ExitCode unless the handle is opened before exit.
    $null = $process.Handle
} finally {
    $env:STATICRECOMP_TRACE_FILE = $previousTracePath
    $env:STATICRECOMP_REL_TRACE_FILE = $previousRelTracePath
    $env:STATICRECOMP_FALLBACK_PROFILE = $previousFallbackProfile
    $env:STATICRECOMP_DISPATCH_TIMING = $previousDispatchTiming
    $env:STATICRECOMP_DISPATCH_SAMPLES = $previousDispatchSamples
    $env:STATICRECOMP_POWERPROS_SCHEDULER_IDLE = $previousSchedulerIdle
    $env:STATICRECOMP_POWERPROS_CACHE_BATCH = $previousCacheBatch
    $env:STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS = $previousSkipEmptyModHooks
    $env:STATICRECOMP_LOCKSTEP = $previousLockstep
    $env:STATICRECOMP_LOCKSTEP_LIMIT = $previousLockstepLimit
    foreach ($key in $previousLockstepOptions.Keys) { [Environment]::SetEnvironmentVariable($key, $previousLockstepOptions[$key], 'Process') }
}
$forcedStop = $false
$statusPath = Join-Path $controls 'status.txt'
$initializationWatch = [System.Diagnostics.Stopwatch]::StartNew()
$ready = $false
# Hashing the private assets and initializing services precede the CPU loop.
# Do not request shutdown during that work merely because the run window ended.
while (-not $process.HasExited -and $initializationWatch.ElapsedMilliseconds -lt 120000) {
    if (Test-Path -LiteralPath $statusPath) {
        $statusText = Get-Content -LiteralPath $statusPath -Raw
        if ($statusText -match '(?m)^state=(running|paused)\r?$') { $ready = $true; break }
    }
    if ($process.WaitForExit(500)) { break }
    $process.Refresh()
}
$initializationWatch.Stop()
$executedSeconds = 0
if ($ready) {
    Copy-Item -LiteralPath $statusPath -Destination (Join-Path $probeRoot 'status-at-ready.txt')
    if ($LoadState) {
        Send-ProbeCommand '0000-load-state.ini' "command=load_state`npath=$LoadState"
    }
    $runWatch = [System.Diagnostics.Stopwatch]::StartNew()
    $nextCapture = $CaptureIntervalSeconds
    $captureIndex = 0
    while (-not $process.HasExited -and $runWatch.ElapsedMilliseconds -lt $Seconds * 1000) {
        if (Test-Path -LiteralPath (Join-Path $probeRoot 'finish-requested')) { break }
        if ($CaptureIntervalSeconds -gt 0 -and $runWatch.Elapsed.TotalSeconds -ge $nextCapture) {
            $captureIndex++
            $captureName = 'progress-{0:D4}' -f $captureIndex
            Send-ProbeCommand "0000-$captureName.ini" "command=screenshot`npath=artifacts/$captureName.png"
            if (Test-Path -LiteralPath $statusPath) {
                Copy-Item -LiteralPath $statusPath -Destination (Join-Path $probeRoot ("status-$captureName.txt"))
            }
            $nextCapture += $CaptureIntervalSeconds
        }
        if ($process.WaitForExit(500)) { break }
        $process.Refresh()
    }
    $runWatch.Stop()
    $executedSeconds = [Math]::Round($runWatch.Elapsed.TotalSeconds, 2)
}
if (-not $process.HasExited) {
    $statusPath = Join-Path $controls 'status.txt'
    if (Test-Path -LiteralPath $statusPath) {
        Copy-Item -LiteralPath $statusPath -Destination (Join-Path $probeRoot 'status-before-stop.txt')
    }
    if ($Screenshot -and $ready) {
        Send-ProbeCommand '0000-screenshot.ini' "command=screenshot`npath=artifacts/game.png"
    }
    if ($SnapshotMemory -and $ready) {
        # Pause before two contiguous reads, each within the runtime's 16 MiB limit.
        Send-ProbeCommand '0001-pause.ini' 'command=pause'
        Send-ProbeCommand '0002-read.ini' "command=read_memory`naddress=0x80000000`nsize=16777216`npath=artifacts/mem1-low.bin"
        Send-ProbeCommand '0003-read.ini' "command=read_memory`naddress=0x81000000`nsize=8388608`npath=artifacts/mem1-high.bin"
        for ($part = 0; $part -lt 4; $part++) {
            $address = '0x{0:X8}' -f (0x90000000L + $part * 16777216L)
            $commandName = '{0:D4}-read.ini' -f (4 + $part)
            Send-ProbeCommand $commandName "command=read_memory`naddress=$address`nsize=16777216`npath=artifacts/mem2-$part.bin"
        }
        # A paused guest cannot handle Dolphin's first, graceful power-button request.
        Send-ProbeCommand '0008-resume.ini' 'command=resume'
    }
    Send-ProbeCommand '0009-stop.ini' 'command=stop'
    if (-not $process.WaitForExit(5000)) {
        # Upstream treats the second request as a direct host shutdown.
        Send-ProbeCommand '0010-stop.ini' 'command=stop'
        if (-not $process.WaitForExit(15000)) {
            # The process may exit between a timed wait and Stop-Process.
            $process.Refresh()
            if (-not $process.HasExited) {
                try {
                    Stop-Process -Id $process.Id -Force -ErrorAction Stop
                    $forcedStop = $true
                } catch {
                    $process.Refresh()
                    if (-not $process.HasExited) { throw }
                }
            }
            $process.WaitForExit()
        }
    }
}
$process.Refresh()
$diagnostics = Get-Content -LiteralPath (Join-Path $probeRoot 'stderr.log') -Raw
$emptyModHooksCounters = $null
if ($diagnostics -match 'mod_hooks_skip_empty_requested=(\d+) mod_hooks_skipped_empty=(\d+) loaded_mods=(\d+)') {
    if ([bool][int]$Matches[1] -ne [bool]$SkipEmptyModHooks) { throw 'La opción de consultas de mods no coincide con el runtime.' }
    $emptyModHooksCounters = [ordered]@{ skipped_empty = [bool][int]$Matches[2]; loaded_mods = [int]$Matches[3] }
} elseif ($SkipEmptyModHooks) { throw 'El runtime no confirmó SkipEmptyModHooks.' }
$counters = $null
$lockstepCounters = $null
if ($Lockstep) {
    if ($diagnostics -notmatch "\[lockstep\] ENABLED: start=$LockstepStart limit=$LockstepLimit maxreport=0 stepcap=20000 whitelist=0") { throw 'El runtime no confirmó la configuración lockstep esperada.' }
    if ($diagnostics -notmatch '\[lockstep\] summary: checks=(\d+) reports=(\d+) skipped_fallback=(\d+) skipped_zero=(\d+) cap_hits=(\d+) filtered=(\d+) undercharges=(\d+) max_deficit=(-?\d+) distinct_pcs=(\d+)') { throw 'Falta el resumen lockstep.' }
    $lockstepCounters = [ordered]@{}
    $lockstepFields = @('checks', 'reports', 'skipped_fallback', 'skipped_zero', 'cap_hits', 'filtered', 'undercharges', 'max_deficit', 'distinct_pcs')
    for ($index = 0; $index -lt $lockstepFields.Count; $index++) { $lockstepCounters[$lockstepFields[$index]] = [long]$Matches[$index+1] }
    if ($diagnostics -notmatch '\[lockstep\] hw_mem2: writes=(\d+) bytes=(\d+) replayed=(\d+)') { throw 'Falta el resumen hw_mem2 del lockstep.' }
    $lockstepCounters['hw_mem2_writes'] = [long]$Matches[1]
    $lockstepCounters['hw_mem2_bytes'] = [long]$Matches[2]
    $lockstepCounters['hw_mem2_replayed'] = [long]$Matches[3]
}
if ($diagnostics -match '\[staticrecomp\] shutdown: native=(\d+) fallback=(\d+) native_exc=(\d+) hook_fb=(\d+) smc_failed=(\d+)') {
    $counters = [ordered]@{
        native_dispatches = [long]$Matches[1]
        interpreter_fallback_steps = [long]$Matches[2]
        native_exceptions = [long]$Matches[3]
        instruction_hook_fallbacks = [long]$Matches[4]
        failed_code_verifications = [long]$Matches[5]
    }
    if ($diagnostics -match 'fallback_jit_runs=(\d+)') {
        $counters.fallback_jit_invocations = [long]$Matches[1]
    }
    if ($diagnostics -match 'scheduler_idle_enabled=(\d+) scheduler_idle_skips=(\d+)') {
        if ([bool][int]$Matches[1] -ne [bool]$SchedulerIdleSkip) {
            throw 'La opción de espera del planificador no coincide con el runtime.'
        }
        $counters.scheduler_idle_skips = [long]$Matches[2]
    } elseif ($SchedulerIdleSkip) {
        throw 'El runtime no confirmó la opción de espera del planificador.'
    }
    if ($diagnostics -match 'cache_batch_enabled=(\d+) cache_batch_runs=(\d+) cache_batch_extra_lines=(\d+)') {
        if ([bool][int]$Matches[1] -ne [bool]$CacheBatch) { throw 'La opción CacheBatch no coincide con el runtime.' }
        $counters.cache_batch_runs = [long]$Matches[2]
        $counters.cache_batch_extra_lines = [long]$Matches[3]
    } elseif ($CacheBatch) { throw 'El runtime no confirmó CacheBatch.' }
}
$probeResult = [ordered]@{
    probe_directory = $probeRoot
    requested_seconds = $Seconds
    executed_seconds = $executedSeconds
    finish_requested = (Test-Path -LiteralPath (Join-Path $probeRoot 'finish-requested'))
    load_state_requested = [bool]$LoadState
    load_state_path = $LoadState
    load_state_sha256 = $loadStateHash
    capture_interval_seconds = $CaptureIntervalSeconds
    physical_input_mappings_disabled = $true
    input_profile = $profile
    failed_command_count = @(Get-ChildItem -LiteralPath (Join-Path $controls 'failed') -File -ErrorAction SilentlyContinue).Count
    graphics_backend = $Graphics
    module_path = $module
    module_sha256 = $moduleHash
    runner_path = $runner
    runner_sha256 = $runnerHash
    optimized_module = [bool]$OptimizedModule
    module_compiler = $(if ($ClangModule) { 'clang-cl' } else { 'msvc' })
    lockstep_requested = [bool]$Lockstep
    lockstep_start = $LockstepStart
    lockstep_limit = $LockstepLimit
    lockstep_trace_pc = $LockstepTracePC
    lockstep_counters = $lockstepCounters
    host_sampling_requested = (Test-Path -LiteralPath (Join-Path $probeRoot 'host-sampling.json'))
    fallback_profile_requested = [bool]$ProfileFallback
    dispatch_timing_requested = [bool]$ProfileDispatchTiming
    dispatch_timing_saved = (Test-Path -LiteralPath (Join-Path $probeRoot 'dispatch-timing.csv'))
    dispatch_timing_sites_saved = (Test-Path -LiteralPath (Join-Path $probeRoot 'dispatch-timing.csv.sites.csv'))
    fallback_profile_saved = (Test-Path -LiteralPath (Join-Path $probeRoot 'fallback-profile.csv'))
    scheduler_idle_skip_requested = [bool]$SchedulerIdleSkip
    cache_batch_requested = [bool]$CacheBatch
    skip_empty_mod_hooks_requested = [bool]$SkipEmptyModHooks
    dual_core_requested = [bool]$DualCore
    lockstep_align_cycles_requested = [bool]$LockstepAlignCycles
    lockstep_align_range = $(if ($LockstepAlignCycles) { $LockstepAlignRange } else { $null })
    dual_core_confirmed = $(if ((Get-Content -LiteralPath (Join-Path $probeRoot 'stderr.log') -Raw) -match 'CPU thread dual_core=(\d)') { [bool][int]$Matches[1] } else { $null })
    empty_mod_hooks_counters = $emptyModHooksCounters
    initialization_seconds = [Math]::Round($initializationWatch.Elapsed.TotalSeconds, 2)
    reached_running_or_paused_state = $ready
    exit_code = $process.ExitCode
    forced_stop = $forcedStop
    shutdown_counters = $counters
    mem1_snapshot_complete = ((Test-Path -LiteralPath (Join-Path $controls 'artifacts/mem1-low.bin')) -and (Test-Path -LiteralPath (Join-Path $controls 'artifacts/mem1-high.bin')))
    mem2_snapshot_complete = (@(0..3 | Where-Object { -not (Test-Path -LiteralPath (Join-Path $controls "artifacts/mem2-$_.bin")) }).Count -eq 0)
    screenshot_saved = (Test-Path -LiteralPath (Join-Path $controls 'artifacts/game.png'))
    module_coverage = $(if ($RelModule) { 'DOL and placement-locked REL (experimental)' } else { 'DOL only' })
    native_game_boot_validated = $false
    note = 'Los logs y los contadores deben revisarse; iniciar el proceso no prueba el arranque del juego.'
}
$probeResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $probeRoot 'result.json') -Encoding utf8
Write-Host "Diagnóstico guardado en $probeRoot"
if ($PassThru) {
    [pscustomobject]$probeResult
} else {
    Get-Content -LiteralPath (Join-Path $probeRoot 'stderr.log') -Tail 25
}
