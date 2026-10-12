@echo off
rem Experimental module: DolRecomp LLVM-backend DOL objects + the preserved MSVC REL objects,
rem or, with a third argument, LLVM-backend linked REL objects too.
setlocal
cd /d "%~dp0.."
set GEN=%~1
if "%GEN%"=="" set GEN=local/generated/dolrecomp-llvm/dol
set OUT=%~2
if "%OUT%"=="" set OUT=local/build/runtime-module-rel-llvm-dol
set RELARGS=-DPOWERPROS_REUSE_MSVC_REL_OBJECTS=ON "-DPOWERPROS_LLVM_REL_DIR="
if not "%~3"=="" set RELARGS=-DPOWERPROS_REUSE_MSVC_REL_OBJECTS=OFF "-DPOWERPROS_LLVM_REL_DIR=%CD%/%~3"
rem BUILD_JOBS (default 8): use 2 for the all-LLVM link (~56k objects) on a loaded machine.
if "%BUILD_JOBS%"=="" set BUILD_JOBS=8
if not defined PY set PY=python
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
"%PY%" tools/module_build_manifest.py local/build/runtime-module-rel-optimized --check-rel-objects
if errorlevel 1 exit /b 1
cmake -S runtime/module -B %OUT% -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="%CD%/local/tools/llvm-22.1.8/bin/clang-cl.exe" -DCMAKE_CXX_COMPILER="%CD%/local/tools/llvm-22.1.8/bin/clang-cl.exe" -DPOWERPROS_ENABLE_REL=ON -DPOWERPROS_OPTIMIZE_MODULE=ON %RELARGS% "-DPOWERPROS_LLVM_DOL_DIR=%CD%/%GEN%" "-DPython3_EXECUTABLE=%PY%"
if errorlevel 1 exit /b 1
cmake --build %OUT% --target gRL8E54_recomp powerpros_module_checks powerpros_rel_checks --parallel %BUILD_JOBS%
if errorlevel 1 exit /b 1
ctest --test-dir %OUT% --output-on-failure
if errorlevel 1 exit /b 1
"%PY%" tools/module_build_manifest.py %OUT%
exit /b %errorlevel%
