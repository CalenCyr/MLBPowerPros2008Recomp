# SPDX-License-Identifier: GPL-3.0-or-later
# Input is a private, exact function-byte extraction with provenance in input.json.
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath (Join-Path $taskRoot 'config/rea-toolchain.json') -Raw | ConvertFrom-Json
$taskOutput = Join-Path $taskRoot 'local/analysis/ghidra-ppc-memcpy'
$taskInput = Join-Path $taskOutput 'memcpy.bin'
$taskMetadata = Get-Content -LiteralPath (Join-Path $taskOutput 'input.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $taskInput -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskMetadata.extracted_sha256) { throw 'PowerPC input hash mismatch' }
$taskProject = Join-Path $taskOutput 'project'
[void](New-Item -ItemType Directory -Path $taskProject -Force)
$taskJavaUser = Join-Path $taskRoot 'local/analysis/ghidra-user'
[void](New-Item -ItemType Directory -Path $taskJavaUser -Force)
$taskEnvironment = @{ JAVA_HOME = $taskConfig.java; TEMP = $taskConfig.temp; TMP = $taskConfig.temp;
    GHIDRA_HEADLESS_JAVA_OPTIONS = ('-Duser.home='+$taskJavaUser.Replace('\','/')); GHIDRA_HEADLESS_MAXMEM = '1G' }
$taskPrevious = @{}
try {
    foreach ($taskKey in $taskEnvironment.Keys) {
        $taskPrevious[$taskKey] = [Environment]::GetEnvironmentVariable($taskKey, 'Process')
        [Environment]::SetEnvironmentVariable($taskKey, $taskEnvironment[$taskKey], 'Process')
    }
    $taskHeadless = Join-Path $taskConfig.ghidra 'support/analyzeHeadless.bat'
    & $taskHeadless $taskProject 'powerpros-memcpy' -import $taskInput -loader BinaryLoader -loader-baseAddr 8000626c -processor 'PowerPC:BE:32:default' -cspec default -noanalysis -scriptPath (Join-Path $taskRoot 'tools/ghidra') -postScript PowerProsFunctionProbe.java $taskMetadata.function.address $taskMetadata.function.name $taskInput $taskOutput -deleteProject -max-cpu 2 -log (Join-Path $taskOutput 'headless.log') -scriptlog (Join-Path $taskOutput 'script.log') 1> (Join-Path $taskOutput 'console.log') 2>&1
    $taskExit = $LASTEXITCODE
} finally {
    foreach ($taskKey in $taskPrevious.Keys) { [Environment]::SetEnvironmentVariable($taskKey, $taskPrevious[$taskKey], 'Process') }
}
if ($taskExit -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $taskOutput 'probe-status.txt'))) {
    Get-Content -LiteralPath (Join-Path $taskOutput 'console.log') -Tail 35
    throw 'Ghidra PowerPC probe failed'
}
Get-Content -LiteralPath (Join-Path $taskOutput 'probe-status.txt')
