# SPDX-License-Identifier: GPL-3.0-or-later
param(
    [Parameter(Mandatory)][string]$ProbeRoot,
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$Content
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath (Join-Path $ProbeRoot 'result.json') -PathType Leaf) {
    throw 'El sondeo ya terminó. Inicia otro sondeo antes de enviar órdenes.'
}
if ($Name -notmatch '^[0-9]{4}-[a-zA-Z0-9-]+\.ini$') {
    throw 'Name debe tener el formato 0000-nombre.ini.'
}
$commands = Join-Path $ProbeRoot 'control/commands'
if (-not (Test-Path -LiteralPath $commands -PathType Container)) {
    throw 'No existe la carpeta de órdenes del sondeo.'
}
$destination = Join-Path $commands $Name
if (Test-Path -LiteralPath $destination) { throw 'La orden ya existe.' }
# Publish only complete files: the runtime polls commands concurrently.
$pending = Join-Path $ProbeRoot ('pending-' + [Guid]::NewGuid().ToString('N') + '.ini')
try {
    Set-Content -LiteralPath $pending -Value $Content -Encoding ascii
    Move-Item -LiteralPath $pending -Destination $destination
} finally {
    if (Test-Path -LiteralPath $pending) { Remove-Item -LiteralPath $pending }
}
