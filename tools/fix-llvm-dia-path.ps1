# Point the LLVM 20.1.8 package's LLVMExports.cmake at this machine's DIA SDK (idempotent).
param([Parameter(Mandatory)][string]$VsInstallDir)
$file = 'local/tools/llvm-20.1.8/lib/cmake/llvm/LLVMExports.cmake'
$dia = (Join-Path $VsInstallDir 'DIA SDK/lib/amd64/diaguids.lib').Replace('\', '/')
if (-not (Test-Path -LiteralPath $dia)) { throw "Missing $dia" }
$text = [IO.File]::ReadAllText($file)
$fixed = $text.Replace('C:/Program Files (x86)/Microsoft Visual Studio/2019/Professional/DIA SDK/lib/amd64/diaguids.lib', $dia)
if ($fixed -ne $text) { [IO.File]::WriteAllText($file, $fixed) }
