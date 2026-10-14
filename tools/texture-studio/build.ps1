# SPDX-License-Identifier: GPL-3.0-or-later
# Configures and builds Power Pros Wii 2008 Texture Studio with the pinned llvm-mingw, CMake and Ninja
# from a prepared Wiicompiled tree (tools/wiicompiled-translate.ps1 makes one). Output: <Output>\TextureStudio.exe
param(
    [string]$Source = 'local\wiicompiled-mlb\src',
    [string]$Output = 'local\build\texture-studio'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
function Resolve-Root([string]$path) { if ([IO.Path]::IsPathRooted($path)) { $path } else { [IO.Path]::GetFullPath((Join-Path $root $path)) } }
$Source = Resolve-Root $Source
$Output = Resolve-Root $Output
$tools = Join-Path $Source 'Launcher\artifacts\portable-tools'
$deps = Join-Path $Source 'Launcher\artifacts\dependencies'
$env:PATH = "$tools\llvm-mingw\bin;$tools\CMake\bin;$tools\Ninja;$env:PATH"
$tc = "$tools\llvm-mingw\bin".Replace('\', '/')
function Fwd([string]$p) { $p.Replace('\', '/') }
cmake -S $PSScriptRoot -B $Output -G Ninja -DCMAKE_BUILD_TYPE=Release `
    "-DCMAKE_C_COMPILER=$tc/clang.exe" "-DCMAKE_CXX_COMPILER=$tc/clang++.exe" "-DCMAKE_RC_COMPILER=$tc/llvm-windres.exe" `
    "-DSDL_SOURCE_DIR=$(Fwd "$deps\SDL")" "-DIMGUI_SOURCE_DIR=$(Fwd "$deps\imgui")" `
    "-DXXHASH_SOURCE_DIR=$(Fwd "$deps\xxhash")" "-DUI_INCLUDE_DIR=$(Fwd "$Source\runtime\include")" | Out-Host
if ($LASTEXITCODE -ne 0) { throw "texture studio configure failed ($LASTEXITCODE)" }
cmake --build $Output --parallel | Out-Host
if ($LASTEXITCODE -ne 0) { throw "texture studio build failed ($LASTEXITCODE)" }
