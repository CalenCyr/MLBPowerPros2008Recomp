@echo off
setlocal
if not defined PY set PY=python
cd /d "%~dp0.."
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
"%PY%" tools/map_clang_module.py %*
exit /b %errorlevel%
