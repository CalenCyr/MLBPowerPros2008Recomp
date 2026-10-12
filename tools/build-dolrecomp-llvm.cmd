@echo off
rem Build the nested DolRecomp generator with its LLVM backend (LLVM 20.1.8, config/tools.lock.json).
rem Applies once, in order: dolrecomp-llvm-gekko-single.patch (Gekko-exact stfs/lfs/psq_st float) and
rem dolrecomp-llvm-scalar-fast.patch (inline non-NaN fadds/fsubs/fmuls with RecompCore helper semantics) and
rem dolrecomp-llvm-halfword-reverse.patch (sthbrx/lhbrx swapped the whole word, not the halfword) and
rem dolrecomp-llvm-ir-cache.patch (object cache keyed on lowered IR; see tools/generate-llvm.cmd).
setlocal
cd /d "%~dp0.."
set DR=local/vendor/ModernGekko/vendor/dolphin/DolRecomp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set PATCHES=dolrecomp-llvm-gekko-single dolrecomp-llvm-scalar-fast dolrecomp-llvm-halfword-reverse dolrecomp-llvm-ir-cache
set LAST=dolrecomp-llvm-ir-cache
rem Stacked patches share context: if the last one is applied, the whole series is.
git -C %DR% apply --reverse --check "%CD%/tools/patches/%LAST%.patch" 2>nul
if not errorlevel 1 goto patched
for %%P in (%PATCHES%) do (
  git -C %DR% apply --check "%CD%/tools/patches/%%P.patch" 2>nul
  if not errorlevel 1 (
    git -C %DR% apply "%CD%/tools/patches/%%P.patch"
    if errorlevel 1 exit /b 1
  )
)
git -C %DR% apply --reverse --check "%CD%/tools/patches/%LAST%.patch"
if errorlevel 1 exit /b 1
:patched
rem The official Windows package records the DIA SDK path of its build machine; point it at this VS install.
powershell -NoProfile -File tools/fix-llvm-dia-path.ps1 -VsInstallDir "%VSINSTALLDIR:~0,-1%"
if errorlevel 1 exit /b 1
cmake -S %DR% -B local/build/dolrecomp-llvm -G Ninja -DCMAKE_BUILD_TYPE=Release -DDOLRECOMP_ENABLE_LLVM=ON "-DLLVM_DIR=%CD%/local/tools/llvm-20.1.8/lib/cmake/llvm"
if errorlevel 1 exit /b 1
cmake --build local/build/dolrecomp-llvm --parallel 10
exit /b %errorlevel%
