param(
    [Parameter(Mandatory = $true)][string]$Image,
    [Parameter(Mandatory = $true)][string]$DolphinTool,
    [string]$Python = 'python',
    [switch]$Convert,
    [switch]$AnalyzeRel
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskImage = (Resolve-Path -LiteralPath $Image).Path
$taskDolphin = (Resolve-Path -LiteralPath $DolphinTool).Path
if ($Convert -and $taskImage -notmatch '\.nkit\.iso$') { throw '-Convert espera una imagen .nkit.iso.' }
$taskDtk = Join-Path $taskRoot 'local\tools\dtk.exe'
$taskNkit = Join-Path $taskRoot 'local\tools\nkit\nkit.exe'
if (-not (Test-Path -LiteralPath $taskDtk)) { throw 'Ejecutar tools/bootstrap.ps1 primero.' }
$taskLocal = Join-Path $taskRoot 'local'
foreach ($taskDir in @('analysis','disc','images','tmp')) {
    New-Item -ItemType Directory -Path (Join-Path $taskLocal $taskDir) -Force | Out-Null
}

Push-Location $taskRoot
try {
    & $taskDolphin header -i $taskImage -j | Set-Content -LiteralPath 'local/analysis/disc-header.json' -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Dolphin no pudo leer la cabecera.' }
    $taskHeader = Get-Content -LiteralPath 'local/analysis/disc-header.json' -Raw | ConvertFrom-Json
    $taskProject = Get-Content -LiteralPath 'config/project.json' -Raw | ConvertFrom-Json
    if ($taskHeader.game_id -ne $taskProject.game_id) { throw "ID de juego inesperado: $($taskHeader.game_id)" }

    & $taskDolphin extract -i $taskImage -g -l | Set-Content -LiteralPath 'local/analysis/fst-dolphin.txt' -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Falló el listado del disco.' }
    # Do not mix a previous image's assets into a new extraction.
    $taskExtractionStamp = 'local/disc/source-sha256.txt'
    $taskSourceHash = (Get-FileHash -LiteralPath $taskImage -Algorithm SHA256).Hash
    $taskDol = 'local/disc/DATA/sys/main.dol'
    if (Test-Path -LiteralPath $taskDol) {
        if (-not (Test-Path -LiteralPath $taskExtractionStamp)) {
            throw 'Extracción existente sin identidad de origen. Usar una carpeta local/disc vacía.'
        }
        $taskPreviousHash = (Get-Content -LiteralPath $taskExtractionStamp -Raw).Trim()
        if ($taskPreviousHash -ne $taskSourceHash) { throw 'La extracción existente corresponde a otra imagen.' }
    } else {
        & $taskDolphin extract -i $taskImage -o (Join-Path $taskLocal 'disc') -g
        if ($LASTEXITCODE -ne 0) { throw 'Falló la extracción.' }
        $taskSourceHash | Set-Content -LiteralPath $taskExtractionStamp -Encoding ascii
    }
    # dtk's VFS interprets a colon as a container separator: use relative paths.
    & $taskDtk dol info $taskDol *> 'local/analysis/dol-info.txt'
    if ($LASTEXITCODE -ne 0) { throw 'Falló el análisis del DOL.' }
    if ($AnalyzeRel) {
        # This large REL can take significantly longer than the DOL.
        & $taskDtk rel info 'local/disc/DATA/files/ovl_main.rel' *> 'local/analysis/rel-info.txt'
        if ($LASTEXITCODE -ne 0) { throw 'Falló el análisis del REL.' }
    }
    if ($Convert) {
        & $taskNkit expand $taskImage --output (Join-Path $taskLocal 'images') --temp (Join-Path $taskLocal 'tmp') --verify y --no-config --results --results-out (Join-Path $taskLocal 'analysis') --log (Join-Path $taskLocal 'analysis/nkit-expand.log') --skip-if-completed
        if ($LASTEXITCODE -ne 0) { throw 'Falló la expansión NKit; revisar el registro.' }
        $taskIsoName = [System.IO.Path]::GetFileName($taskImage) -replace '\.nkit\.iso$', '.iso'
        if ($taskIsoName -eq [System.IO.Path]::GetFileName($taskImage)) { throw '-Convert espera una imagen .nkit.iso.' }
        $taskIso = "local/images/$taskIsoName"
        if (-not (Test-Path -LiteralPath $taskIso)) { throw 'NKit no creó el ISO esperado; revisar el registro.' }
        & $taskDtk disc info $taskIso *> 'local/analysis/disc-info.txt'
        if ($LASTEXITCODE -ne 0) { throw 'dtk no pudo leer el ISO expandido.' }
        & $taskDtk disc verify $taskIso *> 'local/analysis/disc-verify.txt'
        if ($LASTEXITCODE -ne 0) { throw 'Falló la lectura/verificación del ISO.' }
        $taskVerification = Get-Content -LiteralPath 'local/analysis/disc-verify.txt' -Raw
        if ($taskVerification -match 'Not found') {
            Write-Warning 'El ISO expandido no coincide con la base Redump de dtk. Consultar los registros; la fase 0 sigue abierta.'
        }
    }
    & $Python 'tools/analyze_disc.py' --image $taskImage --extracted 'local/disc/DATA' --output 'local/analysis'
    if ($LASTEXITCODE -ne 0) { throw 'Falló el inventario.' }
    $taskDolphinInfo = Get-Item -LiteralPath $taskDolphin
    [ordered]@{
        dolphin_tool = [ordered]@{
            path = $taskDolphin
            file_version = $taskDolphinInfo.VersionInfo.FileVersion
            sha256 = (Get-FileHash -LiteralPath $taskDolphin -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        python_version = (& $Python --version)
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath 'local/analysis/tool-versions.json' -Encoding utf8
    Write-Host 'Inventario guardado en local/analysis/inventory.json.'
} finally {
    Pop-Location
}
