# SPDX-License-Identifier: GPL-3.0-or-later
param([string]$Python='python',[string]$CMake='cmake',[string]$CTest='ctest',
      [int]$Jobs=4,[switch]$ReuseGenerated,[switch]$Optimize,[switch]$ModuleOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $taskRoot
if ($Jobs -lt 1 -or $Jobs -gt 16) { throw 'Jobs debe estar entre 1 y 16.' }
$moduleBuild = 'local/build/runtime-module-rel'
$moduleLog = 'local/analysis/runtime-module-rel'
$optimizeFlag = 'OFF'
if ($Optimize) {
    $moduleBuild += '-optimized'
    $moduleLog += '-optimized'
    $optimizeFlag = 'ON'
}
if (-not $ReuseGenerated) {
    & $Python tools/prepare_linked_rel.py local/analysis/boot-probe-20261008-005615-342 --jobs $Jobs
    if ($LASTEXITCODE) { throw 'No se pudo preparar el REL enlazado.' }
    & $Python tools/reference_rel.py local/analysis/boot-probe-20261008-005615-342
    if ($LASTEXITCODE) { throw 'No se pudo preparar la referencia independiente.' }
}
$relLayout=Get-Content -LiteralPath local/generated/dolrecomp/rel-linked/layout.json -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath local/disc/DATA/files/ovl_main.rel -Algorithm SHA256).Hash.ToLowerInvariant() -ne $relLayout.source_rel_sha256 -or
    (Get-FileHash -LiteralPath local/generated/dolrecomp/rel-linked/linked-analysis.dol -Algorithm SHA256).Hash.ToLowerInvariant() -ne $relLayout.analysis_dol_sha256) {
    throw 'Las entradas REL cambiaron; volver a preparar la traducción.'
}
if ((Get-FileHash -LiteralPath local/disc/DATA/sys/main.dol -Algorithm SHA256).Hash.ToLowerInvariant() -ne '789c208f1611c4b150d272eb32cbd461d24aebbc5d7c11a420102d868ff1c5f7') {
    throw 'El DOL no coincide con la revisión comprobada.'
}
& $CMake -S runtime/module -B $moduleBuild -G 'Visual Studio 17 2022' -A x64 -DPOWERPROS_ENABLE_REL=ON "-DPOWERPROS_OPTIMIZE_MODULE=$optimizeFlag" "-DPython3_EXECUTABLE=$Python" "-DCMAKE_C_FLAGS=/MP$Jobs" *> "$moduleLog-configure.log"
if ($LASTEXITCODE) { throw 'Error configurando el módulo combinado.' }
& $CMake --build $moduleBuild --config Release --parallel $Jobs *> "$moduleLog-build.log"
if ($LASTEXITCODE) { throw 'Error compilando el módulo combinado.' }
& $CTest --test-dir $moduleBuild -C Release --output-on-failure *> "$moduleLog-checks.log"
if ($LASTEXITCODE) { Get-Content -LiteralPath "$moduleLog-checks.log" -Tail 30; throw 'Fallaron las comprobaciones del módulo combinado.' }
# Dependencies and patches are prepared by runtime.ps1. Refuse revision drift.
$lock=Get-Content -LiteralPath config/runtime.lock.json -Raw | ConvertFrom-Json
$runtimeSource=Join-Path $taskRoot 'local/vendor/ModernGekko'
$coreSource=Join-Path $runtimeSource 'vendor/dolphin'
if ((& git -C $runtimeSource rev-parse HEAD).Trim() -ne $lock.commit -or
    (& git -C $coreSource rev-parse HEAD).Trim() -ne $lock.recompcore_commit -or
    (& git -C (Join-Path $coreSource 'DolRecomp') rev-parse HEAD).Trim() -ne $lock.nested_dolrecomp_commit) {
    throw 'Las revisiones del runtime no coinciden con el lock.'
}
& $Python tools/check_runtime_patches.py
if ($LASTEXITCODE) { throw 'La serie completa de parches no coincide con las fuentes; preparar con runtime.ps1.' }
if ($ModuleOnly) {
    Write-Host "Módulo preparado y comprobado en $moduleBuild."
    return
}
& $CMake -S $runtimeSource -B local/build/moderngekko -DPOWERPROS_FIXED_REL_HEADER=0x80575580u *> local/analysis/moderngekko-rel-configure.log
if ($LASTEXITCODE) { throw 'Error configurando la protección de ubicación del REL.' }
& $CMake --build local/build/moderngekko --config Release --target moderngekko-run --parallel $Jobs *> local/analysis/moderngekko-rel-build.log
if ($LASTEXITCODE) { throw 'Error compilando la base con protección REL.' }
Write-Host 'Módulo combinado preparado y comprobado. Su prueba en el juego usa probe-boot.ps1 -RelModule.'
