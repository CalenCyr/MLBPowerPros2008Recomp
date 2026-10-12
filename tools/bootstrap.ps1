param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskTools = Join-Path $taskRoot 'local\tools'
New-Item -ItemType Directory -Path $taskTools -Force | Out-Null
$taskLock = Get-Content -LiteralPath (Join-Path $taskRoot 'config\tools.lock.json') -Raw | ConvertFrom-Json

function Get-VerifiedTool($Url, $Destination, $ExpectedHash) {
    if (Test-Path -LiteralPath $Destination) {
        $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -eq $ExpectedHash) { return }
        throw "Hash inesperado del archivo existente: $Destination"
    }
    $temporary = "$Destination.download"
    Invoke-WebRequest -Uri $Url -OutFile $temporary
    $actual = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedHash) { throw "Falló la verificación SHA256: $temporary" }
    Move-Item -LiteralPath $temporary -Destination $Destination
}

Get-VerifiedTool $taskLock.dtk.url (Join-Path $taskTools 'dtk.exe') $taskLock.dtk.sha256
Get-VerifiedTool $taskLock.nkit.url (Join-Path $taskTools 'nkit.zip') $taskLock.nkit.sha256
$taskNkit = Join-Path $taskTools 'nkit'
if (-not (Test-Path -LiteralPath (Join-Path $taskNkit 'nkit.exe'))) {
    Expand-Archive -LiteralPath (Join-Path $taskTools 'nkit.zip') -DestinationPath $taskNkit
}
Write-Host "Herramientas preparadas en $taskTools"

