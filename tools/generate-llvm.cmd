@echo off
rem Translate with the DolRecomp LLVM backend (tools/build-dolrecomp-llvm.cmd builds it).
rem Usage: generate-llvm.cmd dol|rel OUTPUT_DIR [JOBS] [lockstep]
rem The generator's object cache defaults to %%LOCALAPPDATA%% (drive C:); keep it under local\ on D:.
setlocal
cd /d "%~dp0.."
set KIND=%~1
set OUTDIR=%~2
set JOBS=%~3
if "%JOBS%"=="" set JOBS=4
set INSTR=
if /i "%~4"=="lockstep" set INSTR=--instrumentation lockstep
set DOLRECOMP_LLVM_CACHE=%CD%\local\cache\dolrecomp-llvm
if not exist "%DOLRECOMP_LLVM_CACHE%" mkdir "%DOLRECOMP_LLVM_CACHE%"
rem Second level keyed on each chunk's lowered IR: a generator edit re-lowers every
rem chunk (~1%% of the cost) but only re-optimizes chunks whose IR changed.
set DOLRECOMP_LLVM_IR_CACHE=%CD%\local\cache\dolrecomp-llvm-ir
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if /i "%KIND%"=="dol" (
  set INPUT=local/disc/DATA/sys/main.dol
  set STEM=main.c
) else if /i "%KIND%"=="rel" (
  set INPUT=local/generated/dolrecomp/rel-linked/linked-analysis.dol
  set STEM=runtime_rel.c
) else (
  echo usage: generate-llvm.cmd dol^|rel OUTPUT_DIR [JOBS] [lockstep]
  exit /b 2
)
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
local\build\dolrecomp-llvm\dolrecomp.exe --cpu broadway --backend llvm --runtime recompcore --native-abi off %INSTR% --targets x86-64-v2 -j%JOBS% %INPUT% RL8E54 %OUTDIR%/%STEM%
exit /b %errorlevel%
