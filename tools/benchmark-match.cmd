@echo off
setlocal
rem Yankees - Colorado test match with the live x1-x4 / 16:9 panel; tools\benchmark-match.ps1 measures unattended.
cd /d "%~dp0..\local\wiicompiled-mlb\build"
set WIICOMPILED_MATCH_BENCH=1
set WIICOMPILED_MATCH_SECONDS=0
set WIICOMPILED_BENCH=
set WIICOMPILED_PAD_SCRIPT=
set WIICOMPILED_KPAD_SCRIPT=
WiiCompiled.exe
