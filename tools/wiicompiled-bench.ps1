# SPDX-License-Identifier: GPL-3.0-or-later
# Event-driven frame-time benchmark of the Wiicompiled MLB build. The runtime (WIICOMPILED_BENCH in
# settings_overlay.cpp) waits for a frame with at least -MinDraws draw calls, records -Seconds of
# frames that keep that load, writes bench_result.txt and exits; nothing is timed from outside.
#   -Route demo:    scripted GameCube A presses pass the strap screens, then the title's attract demo
#                   plays a game by itself; its fielding view issues ~650-990 draws.
#   -Route homerun: scripted Wii Remote + Nunchuk into Home Run mode (~400-500 draws at most).
# The demo does not reach the fielding view on every boot, so each attempt is capped at -MaxWait and
# retried up to -Attempts times; a failed attempt saves one window capture just before it gives up
# (never during a measurement). -Api temporarily overrides video.graphics_api in Config.toml.
param([ValidateSet('auto', 'd3d12', 'vulkan')][string]$Api = 'auto', [int]$MinDraws = 600,
      [int]$Seconds = 20, [int]$MaxWait = 300, [int]$Attempts = 3, [string]$Name = 'bench',
      [ValidateSet('demo', 'homerun')][string]$Route = 'demo')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root 'local\wiicompiled-mlb\build'
$logs = Join-Path $root 'local\analysis'
$config = Join-Path $build 'UserData\Config.toml'
$result = Join-Path $build 'bench_result.txt'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class BenchWindow {
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  struct R { public int L, T, Ri, B; }
  public static void Save(IntPtr h, string path) {
    R r; if (h == IntPtr.Zero || !GetWindowRect(h, out r)) return;
    using (var bmp = new System.Drawing.Bitmap(r.Ri - r.L, r.B - r.T))
    using (var g = System.Drawing.Graphics.FromImage(bmp)) {
      var dc = g.GetHdc(); PrintWindow(h, dc, 2); g.ReleaseHdc(dc); bmp.Save(path);
    }
  }
}
'@ -ReferencedAssemblies System.Drawing

$saved = [IO.File]::ReadAllText($config)
Copy-Item $config "$config.bench-backup" -Force
try {
    if ($Api -ne 'auto') {
        $text = $saved -replace '(?m)^graphics_api\s*=.*\r?\n?', ''
        if ($text -notmatch '(?m)^\[video\]') { $text = $text.TrimEnd() + "`r`n`r`n[video]`r`n" }
        [IO.File]::WriteAllText($config, ($text -replace '(?m)^\[video\]\r?\n', "[video]`r`ngraphics_api = `"$Api`"`r`n"))
    }
    $env:WIICOMPILED_BENCH = "$MinDraws,$Seconds,$MaxWait"
    if ($Route -eq 'homerun') {
        $times = @(8, 10, 12, 14, 34, 37, 40) + (46..($MaxWait + 60) | Where-Object { ($_ - 40) % 6 -eq 0 })
        $env:WIICOMPILED_KPAD_SCRIPT = ($times | ForEach-Object { "$($_ * 1000)-$($_ * 1000 + 150):800" }) -join ','
        $env:WIICOMPILED_KPAD_EXT = 'nunchuk'
    } else {
        $env:WIICOMPILED_PAD_SCRIPT = ((8, 10, 12, 14) | ForEach-Object { "$($_ * 1000)-$($_ * 1000 + 150):100" }) -join ','
    }
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        Remove-Item $result -ErrorAction SilentlyContinue
        $tag = "$Name-$attempt"
        $process = Start-Process (Join-Path $build 'WiiCompiled.exe') -WorkingDirectory $build -PassThru `
            -RedirectStandardOutput "$logs\wc-$tag.out.log" -RedirectStandardError "$logs\wc-$tag.err.log"
        $null = $process.Handle  # keeps ExitCode readable after exit
        $started = Get-Date
        $captured = $false
        while (-not $process.WaitForExit(500)) {
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $measuring = Select-String -Path "$logs\wc-$tag.err.log" -Pattern '^\[bench\] scene' -Quiet
            if (-not $captured -and -not $measuring -and $elapsed -gt $MaxWait - 3) {
                $process.Refresh()
                [BenchWindow]::Save($process.MainWindowHandle, "$logs\wc-$tag-stuck.png")
                $captured = $true
            }
            if ($elapsed -gt $MaxWait + $Seconds * 6 + 60) { Stop-Process -Id $process.Id -Force; break }
        }
        $api = Select-String -Path "$logs\wc-$tag.out.log", "$logs\wc-$tag.err.log" -Pattern 'graphics backend: (\w+)' |
            Select-Object -First 1 | ForEach-Object { $_.Matches[0].Groups[1].Value }
        Select-String -Path "$logs\wc-$tag.err.log" -Pattern '^\[bench\] scene' | ForEach-Object { "[$api #$attempt] $($_.Line)" }
        if (Test-Path $result) {
            $text = Get-Content $result
            $text | ForEach-Object { "[$api #$attempt] $_" }
            if ($text -notmatch 'not reached') { break }
        } else {
            "[$api #$attempt] no result (exit code $($process.ExitCode))"
        }
    }
} finally {
    Remove-Item Env:WIICOMPILED_BENCH, Env:WIICOMPILED_PAD_SCRIPT, Env:WIICOMPILED_KPAD_SCRIPT, Env:WIICOMPILED_KPAD_EXT -ErrorAction SilentlyContinue
    Copy-Item "$config.bench-backup" $config -Force
    Remove-Item "$config.bench-backup"
}
