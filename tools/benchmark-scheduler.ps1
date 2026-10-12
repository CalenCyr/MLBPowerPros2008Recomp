# SPDX-License-Identifier: GPL-3.0-or-later
param(
    [Parameter(Mandatory)][ValidateCount(1, 8)][string[]]$LoadState,
    [ValidateRange(60, 300)][int]$Seconds = 120,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $taskRoot
if (@(Get-Process -Name moderngekko-run -ErrorAction SilentlyContinue).Count) {
    throw 'Ya hay un runtime activo; la comparación requiere sesiones consecutivas.'
}
# Check every requested state before launching any probe. Originals stay untouched.
$states = foreach ($state in $LoadState) {
    $resolved = (Resolve-Path -LiteralPath $state).Path
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf) -or (Get-Item -LiteralPath $resolved).Length -eq 0) {
        throw "Estado vacío o inválido: $state"
    }
    $resolved
}
$batchRoot = Join-Path $taskRoot ('local/analysis/scheduler-benchmark-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $batchRoot | Out-Null
$batch = [ordered]@{
    status = 'running'
    requested_seconds_per_probe = $Seconds
    cases = @()
    scope = 'Consecutive restored-state probes; frequencies and guest-frame speed do not measure render FPS or full-match behavior. Images require visual review.'
}
$batchPath = Join-Path $batchRoot 'result.json'
function Save-Batch {
    $batch | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $batchPath -Encoding utf8
}
Save-Batch
try {
    foreach ($state in $states) {
        $caseNumber = $batch.cases.Count + 1
        $caseRoot = Join-Path $batchRoot ('case-{0:D2}' -f $caseNumber)
        New-Item -ItemType Directory -Path $caseRoot | Out-Null
        $case = [ordered]@{
            state_path = $state
            state_sha256 = (Get-FileHash -LiteralPath $state -Algorithm SHA256).Hash.ToLowerInvariant()
            baseline_probe = $null
            candidate_probe = $null
            comparison_report = Join-Path $caseRoot 'comparison.json'
            comparison = $null
            checks_passed = $false
            screenshots_visually_reviewed = $false
        }
        $batch.cases += [pscustomobject]$case
        Save-Batch
        foreach ($enabled in @($false, $true)) {
            Write-Host "Caso ${caseNumber}: espera acelerada = $enabled; $Seconds segundos."
            $probe = & (Join-Path $PSScriptRoot 'probe-boot.ps1') -Seconds $Seconds -Graphics Vulkan -RelModule -OptimizedModule -SchedulerIdleSkip:$enabled -CaptureIntervalSeconds 10 -Screenshot -SnapshotMemory -LoadState $state -PassThru
            if (-not $probe.probe_directory) { throw 'El sondeo no devolvió un resultado estructurado.' }
            $caseEntry = $batch.cases[$caseNumber - 1]
            if ($enabled) { $caseEntry.candidate_probe = $probe.probe_directory }
            else { $caseEntry.baseline_probe = $probe.probe_directory }
            Save-Batch
            if ($probe.load_state_sha256 -ne $caseEntry.state_sha256) { throw 'El estado cambió durante la comparación.' }
            if ($probe.finish_requested) { throw 'La comparación fue interrumpida anticipadamente.' }
            $variant = $(if ($enabled) { 'on' } else { 'off' })
            foreach ($check in @('check_probe_shutdown.py', 'inspect_runtime_rel.py', 'validate_runtime_relocations.py')) {
                & $Python (Join-Path $PSScriptRoot $check) $probe.probe_directory *> (Join-Path $caseRoot "$variant-$check.log")
                if ($LASTEXITCODE -ne 0) { throw "Falló $check en $variant." }
            }
            $relCheck = Get-Content -LiteralPath (Join-Path $probe.probe_directory 'rel-relocation-validation.json') -Raw | ConvertFrom-Json
            if (-not $relCheck.all_relocation_fields_match -or -not $relCheck.all_code_bytes_match) {
                throw "El REL no coincide en $variant."
            }
        }
        $caseEntry = $batch.cases[$caseNumber - 1]
        & $Python (Join-Path $PSScriptRoot 'compare_scheduler_probe_speed.py') $caseEntry.baseline_probe $caseEntry.candidate_probe --output $caseEntry.comparison_report *> (Join-Path $caseRoot 'comparison.log')
        if ($LASTEXITCODE -ne 0) { throw 'Las condiciones de la comparación no coinciden.' }
        $caseEntry.comparison = Get-Content -LiteralPath $caseEntry.comparison_report -Raw | ConvertFrom-Json
        $caseEntry.checks_passed = $true
        Save-Batch
    }
    $batch.status = 'complete'
    Save-Batch
    Write-Host "Comparación comprobada en $batchPath. Las imágenes todavía requieren revisión visual."
} catch {
    $batch.status = 'failed'
    $batch.error = $_.Exception.Message
    Save-Batch
    throw
}
