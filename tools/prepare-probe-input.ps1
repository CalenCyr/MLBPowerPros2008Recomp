# SPDX-License-Identifier: GPL-3.0-or-later
param([Parameter(Mandatory)][string]$Profile)
$ErrorActionPreference = 'Stop'
$configDirectory = Join-Path $Profile 'Config'
New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
# A present INI loads empty mappings instead of the keyboard/mouse defaults.
# Keep Nunchuk attached, as in the default Wii controller, and one emulated remote.
$wii = @('# Power Pros automated probe: no physical input mappings.')
$gc = @('# Power Pros automated probe: no physical input mappings.')
for ($port = 1; $port -le 4; $port++) {
    $wii += "[Wiimote$port]", 'Device=CodexAutomation/0/Disconnected', "Source=$(if ($port -eq 1) { 1 } else { 0 })", 'Extension=Nunchuk'
    $gc += "[GCPad$port]", 'Device=CodexAutomation/0/Disconnected'
}
$writes = @()
foreach ($entry in @(@{Name='WiimoteNew.ini'; Lines=$wii}, @{Name='GCPadNew.ini'; Lines=$gc})) {
    $path = Join-Path $configDirectory $entry.Name
    $expected = ($entry.Lines -join "`n") + "`n"
    if (Test-Path -LiteralPath $path) {
        $actual = [System.IO.File]::ReadAllText($path).Replace("`r`n", "`n")
        # Dolphin rewrites INI spacing and drops comments and empty GC sections.
        $actualLines = @($actual -split "`n" | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { $_ -replace '\s*=\s*', '=' })
        $expectedLines = @($entry.Lines | Where-Object { -not $_.StartsWith('#') })
        $legacyLines = @($expectedLines | Where-Object { $_ -notmatch '^Device=' })
        $recognizedLegacy = (($actualLines -join "`n") -eq ($legacyLines -join "`n"))
        if ($entry.Name -eq 'GCPadNew.ini' -and @($actualLines | Where-Object { $_ -notmatch '^\[GCPad[1-4]\]$' }).Count -eq 0) {
            $recognizedLegacy = $true
        }
        if (($actualLines -join "`n") -ne ($expectedLines -join "`n") -and -not $recognizedLegacy) {
            throw "El perfil de automatización contiene otros ajustes: $path"
        }
    }
    $writes += @{Path=$path; Text=$expected}
}
# A device key keeps otherwise empty GC sections when Dolphin saves the INI.
# Verify both files first, then publish only recognized diagnostic settings.
foreach ($write in $writes) {
    Set-Content -LiteralPath $write.Path -Value $write.Text -NoNewline -Encoding ascii
}
