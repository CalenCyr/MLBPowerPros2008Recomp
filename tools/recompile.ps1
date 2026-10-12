param(
    [string]$Python = 'python',
    [string]$CMake = 'cmake',
    [string]$CTest = 'ctest',
    [int]$Jobs = 4,
    [switch]$SkipDtkAnalysis,
    [switch]$ReuseGenerated
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLock = Get-Content -LiteralPath (Join-Path $taskRoot 'config\recompiler.lock.json') -Raw | ConvertFrom-Json
$taskVendor = Join-Path $taskRoot 'local\vendor\DolRecomp'
if ($Jobs -lt 1 -or $Jobs -gt 32) { throw 'Jobs debe estar entre 1 y 32.' }

function Run-NativeStep($Executable, [string[]]$Arguments, $Log) {
    & $Executable @Arguments *> $Log
    if ($LASTEXITCODE -ne 0) {
        Get-Content -LiteralPath $Log -Tail 30 | Write-Host
        throw "Falló $Executable. Registro: $Log"
    }
}

Push-Location $taskRoot
try {
    foreach ($taskDir in @('local/analysis','local/vendor','local/generated/dolrecomp/dol','local/generated/dolrecomp/rel')) {
        New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath 'local/analysis/inventory.json')) {
        throw 'Ejecutar tools/phase0.ps1 primero.'
    }
    $taskInventory = Get-Content -LiteralPath 'local/analysis/inventory.json' -Raw | ConvertFrom-Json
    foreach ($taskInput in @(
        @{path='local/disc/DATA/sys/main.dol'; hash=$taskInventory.dol.sha256},
        @{path='local/disc/DATA/files/ovl_main.rel'; hash=$taskInventory.rels[0].sha256}
    )) {
        $taskHash = (Get-FileHash -LiteralPath $taskInput.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($taskHash -ne $taskInput.hash) { throw "Cambió la entrada: $($taskInput.path)" }
    }
    if (-not (Test-Path -LiteralPath $taskVendor)) {
        Run-NativeStep 'git' @('clone','--no-checkout',$taskLock.repository,$taskVendor) 'local/analysis/dolrecomp-clone.log'
        Run-NativeStep 'git' @('-C',$taskVendor,'checkout','--detach',$taskLock.commit) 'local/analysis/dolrecomp-checkout.log'
    }
    $taskCommit = (& git -C $taskVendor rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $taskCommit -ne $taskLock.commit) { throw 'El checkout de DolRecomp no coincide con el commit fijado.' }
    $taskPatch = Join-Path $taskRoot $taskLock.patch
    & git -C $taskVendor apply --reverse --check $taskPatch 2>$null
    if ($LASTEXITCODE -ne 0) {
        Run-NativeStep 'git' @('-C',$taskVendor,'apply','--check',$taskPatch) 'local/analysis/dolrecomp-patch-check.log'
        Run-NativeStep 'git' @('-C',$taskVendor,'apply',$taskPatch) 'local/analysis/dolrecomp-patch.log'
    }
    Write-Host 'Construyendo y comprobando DolRecomp...'
    Run-NativeStep $CMake @('-S','local/vendor/DolRecomp','-B','local/build/dolrecomp','-G','Visual Studio 17 2022','-A','x64','-DCMAKE_DISABLE_FIND_PACKAGE_ZLIB=ON') 'local/analysis/dolrecomp-configure.log'
    Run-NativeStep $CMake @('--build','local/build/dolrecomp','--config','Release','--parallel',"$Jobs") 'local/analysis/dolrecomp-build-fixed.log'
    Run-NativeStep $CTest @('--test-dir','local/build/dolrecomp','-C','Release','--output-on-failure') 'local/analysis/dolrecomp-tests-fixed.log'
    if (-not $SkipDtkAnalysis) {
        Write-Host 'Analizando funciones y relocaciones con dtk...'
        Run-NativeStep '.\local\tools\dtk.exe' @('dol','config','local/disc/DATA/sys/main.dol','local/disc/DATA/files/ovl_main.rel','-o','local/analysis/dtk-config.yml') 'local/analysis/dtk-config.log'
        Run-NativeStep '.\local\tools\dtk.exe' @('dol','split','local/analysis/dtk-config.yml','local/analysis/dtk-split','-j',"$Jobs") 'local/analysis/dtk-split.log'
    }
    if (-not $ReuseGenerated) {
        Write-Host 'Traduciendo DOL y REL a C...'
        $taskRecompiler = '.\local\build\dolrecomp\Release\dolrecomp.exe'
        Run-NativeStep $taskRecompiler @('--cpu','broadway',"-j$Jobs",'local/disc/DATA/sys/main.dol','RL8E54','local/generated/dolrecomp/dol/main.c') 'local/analysis/dolrecomp-dol.log'
        Run-NativeStep $taskRecompiler @('--cpu','broadway','--rel-base',$taskLock.rel_base_for_trial,"-j$Jobs",'local/disc/DATA/files/ovl_main.rel','RL8E54','local/generated/dolrecomp/rel/ovl_main.c') 'local/analysis/dolrecomp-rel.log'
    }
    Run-NativeStep $Python @('tools/audit_translation.py') 'local/analysis/translation-audit.log'
    Write-Host 'Compilando todo el código traducido...'
    Run-NativeStep $CMake @('-S','recompiler','-B','local/build/powerpros-cpu','-G','Visual Studio 17 2022','-A','x64') 'local/analysis/generated-configure.log'
    Run-NativeStep $CMake @('--build','local/build/powerpros-cpu','--config','Release','--parallel',"$Jobs") 'local/analysis/generated-build.log'
    Write-Host 'Comparando rutinas nativas con el PowerPC original...'
    # The reference emulator is installed only in local/, never in the port runtime.
    & $Python -c 'import sys; sys.path.insert(0,"local/python"); import unicorn; sys.exit(0 if unicorn.__version__ == sys.argv[1] else 1)' $taskLock.verification_dependencies.unicorn 2>$null
    if ($LASTEXITCODE -ne 0) {
        Run-NativeStep $Python @('-m','pip','install','--no-cache-dir','--upgrade','--target','local/python',"unicorn==$($taskLock.verification_dependencies.unicorn)") 'local/analysis/reference-dependency.log'
    }
    Run-NativeStep $Python @('tools/reference_memory.py') 'local/analysis/reference-memory.log'
    Run-NativeStep $CMake @('-S','runtime/checks','-B','local/build/native-checks','-G','Visual Studio 17 2022','-A','x64') 'local/analysis/native-checks-configure.log'
    Run-NativeStep $CMake @('--build','local/build/native-checks','--config','Release','--parallel',"$Jobs") 'local/analysis/native-checks-build.log'
    Run-NativeStep $CTest @('--test-dir','local/build/native-checks','-C','Release','--output-on-failure') 'local/analysis/native-checks-tests.log'
    Run-NativeStep '.\local\build\native-checks\Release\powerpros_native_checks.exe' @('local/analysis/memory-reference.bin') 'local/analysis/native-checks-result.txt'
    Write-Host 'Traducción compilada y rutinas de memoria verificadas. Esto todavía no inicia el juego.'
} finally {
    Pop-Location
}
