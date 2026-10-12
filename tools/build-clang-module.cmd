@echo off
setlocal
if not defined PY set PY=python
cd /d "%~dp0.."
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
"%PY%" tools/module_build_manifest.py local/build/runtime-module-rel-optimized --check-rel-objects
if errorlevel 1 exit /b 1
cmake -S runtime/module -B local/build/runtime-module-rel-clang -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="%CD%/local/tools/llvm-22.1.8/bin/clang-cl.exe" -DCMAKE_CXX_COMPILER="%CD%/local/tools/llvm-22.1.8/bin/clang-cl.exe" -DPOWERPROS_ENABLE_REL=ON -DPOWERPROS_OPTIMIZE_MODULE=ON -DPOWERPROS_REUSE_MSVC_REL_OBJECTS=ON "-DPython3_EXECUTABLE=%PY%"
if errorlevel 1 exit /b 1
cmake --build local/build/runtime-module-rel-clang --target gRL8E54_recomp powerpros_module_checks powerpros_rel_checks --parallel 4
if errorlevel 1 exit /b 1
ctest --test-dir local/build/runtime-module-rel-clang --output-on-failure
if errorlevel 1 exit /b 1
"%PY%" tools/module_build_manifest.py local/build/runtime-module-rel-clang
exit /b %errorlevel%
