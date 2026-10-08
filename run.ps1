$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "请先使用 Python 3.11 创建 .venv 并安装依赖。" }
& $pythonExe -c "import sys; assert sys.version_info[:2] == (3,11), '需要 Python 3.11'"
if ($LASTEXITCODE -ne 0) { throw "Python 版本检查失败。" }
& $pythonExe main.py
if ($LASTEXITCODE -ne 0) { throw "应用退出，错误码：$LASTEXITCODE" }
