# Builds and runs PowerUp+ (local/vendor/PowerUpPlus @ eb1a2c2 plus tools/patches/powerupplus-*.patch)
# with its command line, everything kept under local/. Each argument is one PowerUp+ command, e.g.
#   tools/powerupplus.ps1 'read-game-save --in-file D:\...\project.bin --name "MLB 2008"' 'list-rosters'
# The database and logs live in local/powerupplus/run.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$work = Join-Path $root 'local\powerupplus'
$src = Join-Path $work 'src'
$run = Join-Path $work 'run'
$home_ = Join-Path $root 'local\cache\dotnet-home'
foreach ($dir in "$home_\AppData", "$home_\LocalAppData", "$home_\tmp", $run) {
    New-Item -ItemType Directory -Force $dir | Out-Null
}
# PowerUp+ targets .NET 10; the SDK is installed under local/tools by dotnet-install.ps1 -Channel 10.0.
$dotnet = Join-Path $root 'local\tools\dotnet10\dotnet.exe'
$env:DOTNET_ROOT = Split-Path $dotnet
$env:NUGET_PACKAGES = Join-Path $root 'local\cache\nuget'
$env:DOTNET_CLI_HOME = $home_
$env:APPDATA = "$home_\AppData"
$env:LOCALAPPDATA = "$home_\LocalAppData"
$env:TEMP = "$home_\tmp"
$env:TMP = "$home_\tmp"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'

function Invoke-Checked([string]$label) {
    if ($LASTEXITCODE -ne 0) { throw "$label failed with exit code $LASTEXITCODE" }
}

if (-not (Test-Path "$src\.git")) {
    git clone -q (Join-Path $root 'local\vendor\PowerUpPlus') $src; Invoke-Checked 'git clone'
    foreach ($patch in Get-ChildItem (Join-Path $root 'tools\patches\powerupplus-*.patch') | Sort-Object Name) {
        git -C $src apply $patch.FullName; Invoke-Checked "patch $($patch.Name)"
    }
}
$cli = "$src\PowerUp\PowerUp.CommandLine"
& $dotnet build "$cli\PowerUp.CommandLine.csproj" -c Release -o "$work\bin" | Select-Object -Last 3 | Out-Host
Invoke-Checked 'dotnet build'

# The CLI reads appsettings.json next to the executable; its data (base save, libraries,
# database) is a copy of the Electron UI's Data folder.
if (-not (Test-Path "$run\Data")) { Copy-Item -Recurse "$src\PowerUp\PowerUp.ElectronUI\Data" "$run\Data" }
@{ DataDirectory = "$run\Data" } | ConvertTo-Json | Set-Content -Encoding utf8 "$work\bin\appsettings.json"
[IO.File]::WriteAllText("$run\commands.txt", ((@($args) + 'quit') -join "`n") + "`n")
Push-Location $run
try {
    cmd /c "`"$work\bin\PowerUp.CommandLine.exe`" < commands.txt 2>&1"
} finally {
    Pop-Location
}
