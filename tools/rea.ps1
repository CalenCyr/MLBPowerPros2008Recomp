# SPDX-License-Identifier: GPL-3.0-or-later
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ReaArguments)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath (Join-Path $taskRoot 'config/rea-toolchain.json') -Raw | ConvertFrom-Json
foreach ($taskPath in @($taskConfig.node, $taskConfig.rea_entry, (Join-Path $taskConfig.ghidra 'support/analyzeHeadless.bat'), (Join-Path $taskConfig.java 'bin/java.exe'))) {
    if (-not (Test-Path -LiteralPath $taskPath -PathType Leaf)) { throw ('Falta una herramienta REA: '+$taskPath) }
}
$taskPrevious = @{}
$taskEnvironment = @{ GHIDRA_INSTALL_DIR = $taskConfig.ghidra; JAVA_HOME = $taskConfig.java; TEMP = $taskConfig.temp; TMP = $taskConfig.temp }
[void](New-Item -ItemType Directory -Path $taskConfig.temp -Force)
try {
    foreach ($taskKey in $taskEnvironment.Keys) {
        $taskPrevious[$taskKey] = [Environment]::GetEnvironmentVariable($taskKey, 'Process')
        [Environment]::SetEnvironmentVariable($taskKey, $taskEnvironment[$taskKey], 'Process')
    }
    if (-not $ReaArguments) { $ReaArguments = @('--help') }
    & $taskConfig.node $taskConfig.rea_entry @ReaArguments
    $taskExit = $LASTEXITCODE
} finally {
    foreach ($taskKey in $taskPrevious.Keys) { [Environment]::SetEnvironmentVariable($taskKey, $taskPrevious[$taskKey], 'Process') }
}
exit $taskExit
