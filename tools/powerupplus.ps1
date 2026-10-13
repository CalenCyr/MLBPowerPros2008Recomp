# Builds and runs PowerUp+ (local/vendor/PowerUpPlus @ eb1a2c2 plus tools/patches/powerupplus-*.patch),
# everything kept under local/. The database and logs live in local/powerupplus/run.
#   tools/powerupplus.ps1 -Ui
#       the editor in the browser (http://127.0.0.1:5123): Import Roster accepts the game's
#       project.bin, Export Roster has "MLB Power Pros 2008 Mod". Ctrl+C stops it.
#   tools/powerupplus.ps1 'read-game-save --in-file D:\...\project.bin --name "MLB 2008"' 'list-rosters'
#       the command line; each argument is one PowerUp+ command.
param([switch]$Ui)
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
$env:npm_config_cache = Join-Path $root 'local\cache\npm'
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
# Both front ends share one data folder (base save, libraries, database), a copy of the UI's.
if (-not (Test-Path "$run\Data")) { Copy-Item -Recurse "$src\PowerUp\PowerUp.ElectronUI\Data" "$run\Data" }

if ($Ui) {
    # The Electron UI's web build, served by its own ASP.NET backend; no Electron needed.
    $ui = "$src\PowerUp\PowerUp.ElectronUI"
    Push-Location "$ui\electron"
    try {
        if (-not (Test-Path node_modules)) { cmd /c "npm ci --ignore-scripts --no-audit --no-fund"; Invoke-Checked 'npm ci' }
        cmd /c "npm run build"; Invoke-Checked 'npm run build'
    } finally {
        Pop-Location
    }
    & $dotnet build "$ui\PowerUp.ElectronUI.csproj" -c Release -o "$work\bin-ui" | Select-Object -Last 3 | Out-Host
    Invoke-Checked 'dotnet build'
    Start-Process 'http://127.0.0.1:5123/'
    Push-Location $run
    try {
        & "$work\bin-ui\PowerUp.ElectronUI.exe" --urls http://127.0.0.1:5123 --contentRoot $ui "--DataDirectory=$run\Data"
    } finally {
        Pop-Location
    }
    return
}

$cli = "$src\PowerUp\PowerUp.CommandLine"
& $dotnet build "$cli\PowerUp.CommandLine.csproj" -c Release -o "$work\bin" | Select-Object -Last 3 | Out-Host
Invoke-Checked 'dotnet build'
# The CLI reads appsettings.json next to the executable.
@{ DataDirectory = "$run\Data" } | ConvertTo-Json | Set-Content -Encoding utf8 "$work\bin\appsettings.json"
[IO.File]::WriteAllText("$run\commands.txt", ((@($args) + 'quit') -join "`n") + "`n")
Push-Location $run
try {
    cmd /c "`"$work\bin\PowerUp.CommandLine.exe`" < commands.txt 2>&1"
} finally {
    Pop-Location
}
