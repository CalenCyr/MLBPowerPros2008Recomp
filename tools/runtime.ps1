param(
    [string]$CMake = 'cmake',
    [string]$CTest = 'ctest',
    [string]$Python = 'python',
    [int]$Jobs = 4,
    [switch]$SkipDependencies
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $taskRoot
$lock = Get-Content -LiteralPath 'config/runtime.lock.json' -Raw | ConvertFrom-Json
if (-not $env:VCToolsRedistDir) {
    $vsLocator = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (Test-Path -LiteralPath $vsLocator) {
        $vsRoot = & $vsLocator -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        $redistRoot = Join-Path $vsRoot 'VC/Redist/MSVC'
        $redist = Get-ChildItem -LiteralPath $redistRoot -Directory | Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName 'vc_redist.x64.exe')
        } | Sort-Object Name -Descending | Select-Object -First 1
        if ($redist) { $env:VCToolsRedistDir = $redist.FullName + '\' }
    }
}
$runtimeSource = Join-Path $taskRoot 'local/vendor/ModernGekko'
New-Item -ItemType Directory -Force -Path 'local/analysis' | Out-Null
if (-not (Test-Path -LiteralPath "$runtimeSource/.git")) {
    & git clone $lock.repository $runtimeSource
    if ($LASTEXITCODE) { throw 'No se pudo obtener el runtime.' }
    & git -C $runtimeSource checkout --detach $lock.commit
    if ($LASTEXITCODE) { throw 'No se pudo fijar la revisión del runtime.' }
}
$actual = (& git -C $runtimeSource rev-parse HEAD).Trim()
if ($actual -ne $lock.commit) { throw "Revisión inesperada del runtime: $actual" }
if (-not $SkipDependencies) {
    & git -C $runtimeSource submodule update --init --recursive --depth 1 *> local/analysis/moderngekko-submodules.log
    if ($LASTEXITCODE) { throw 'No se pudieron preparar todas las dependencias.' }
}
$chassisRoot = Join-Path $runtimeSource 'vendor/dolphin'
$chassisRevision = (& git -C $chassisRoot rev-parse HEAD).Trim()
if ($chassisRevision -ne $lock.recompcore_commit) { throw "Revisión inesperada de RecompCore: $chassisRevision" }
$nestedRevision = (& git -C (Join-Path $chassisRoot 'DolRecomp') rev-parse HEAD).Trim()
if ($nestedRevision -ne $lock.nested_dolrecomp_commit) { throw "Revisión inesperada del recompilador incluido: $nestedRevision" }
& $Python tools/check_runtime_patches.py --prepare
if ($LASTEXITCODE) { throw 'No se pudo preparar la serie completa de parches; se conservan cambios no reconocidos.' }
$checks = @{
    'local/disc/DATA/sys/main.dol' = '789c208f1611c4b150d272eb32cbd461d24aebbc5d7c11a420102d868ff1c5f7'
    'local/disc/DATA/files/ovl_main.rel' = 'dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc'
}
foreach ($file in $checks.Keys) {
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $checks[$file]) {
        throw "El archivo de entrada no coincide: $file"
    }
}
& $CMake -S runtime/module -B local/build/runtime-module -G 'Visual Studio 17 2022' -A x64 "-DPython3_EXECUTABLE=$Python" *> local/analysis/runtime-module-configure.log
if ($LASTEXITCODE) { throw 'Error configurando el módulo.' }
& $CMake --build local/build/runtime-module --config Release --parallel $Jobs *> local/analysis/runtime-module-build.log
if ($LASTEXITCODE) { throw 'Error compilando el módulo.' }
& $CTest --test-dir local/build/runtime-module -C Release --output-on-failure *> local/analysis/runtime-module-checks.log
if ($LASTEXITCODE) { throw 'Las pruebas del módulo fallaron.' }
& $CMake -S $runtimeSource -B local/build/moderngekko -G 'Visual Studio 17 2022' -A x64 -DBUILD_TESTING=OFF -DDOLRECOMP_ENABLE_LLVM=OFF -DUSE_SYSTEM_LIBS=OFF -DMODERNGEKKO_REQUIRED_DISC_ID=RL8E54 -DMODERNGEKKO_USER_DIRECTORY_NAME=PowerPros2008Recomp '-DMODERNGEKKO_FRONTEND_NAME=MLB Power Pros 2008 Recomp' -DPOWERPROS_FIXED_REL_HEADER= "-DCMAKE_C_FLAGS=/MP$Jobs" "-DCMAKE_CXX_FLAGS=/MP$Jobs /EHsc" *> local/analysis/moderngekko-configure.log
if ($LASTEXITCODE) { throw 'Error configurando la base del runtime.' }
& $CMake --build local/build/moderngekko --config Release --target moderngekko-run --parallel $Jobs *> local/analysis/moderngekko-build.log
if ($LASTEXITCODE) { throw 'Error compilando la base del runtime.' }
Write-Host 'Módulo y base preparados. El arranque y la cobertura del REL requieren verificación independiente.'
