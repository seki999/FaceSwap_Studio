param([string]$Python311, [switch]$CoreOnly)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-CheckedPython {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python 命令失败（$LASTEXITCODE）：$($Arguments -join ' ')" }
}

if (-not $Python311) {
    $cachedRoot = Join-Path $env:APPDATA "uv\python"
    if (Test-Path -LiteralPath $cachedRoot) {
        $candidate = Get-ChildItem -LiteralPath $cachedRoot -Directory -Filter "cpython-3.11.*-windows-x86_64-none" | Sort-Object Name -Descending | Select-Object -First 1
        if ($candidate) { $Python311 = Join-Path $candidate.FullName "python.exe" }
    }
}
if (-not $Python311) {
    $existingExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $existingExe) {
        & $existingExe -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8 else 1)"
        if ($LASTEXITCODE -eq 0) { $Python311 = $existingExe }
    }
}
if (-not $Python311 -or -not (Test-Path -LiteralPath $Python311)) {
    throw "找不到 Python 3.11 x64。请安装官方 Python 3.11，再运行 .\setup.ps1 -Python311 '对应的python.exe完整路径'。不要使用系统 Python 3.13 创建此项目 venv。"
}
Invoke-CheckedPython -Executable $Python311 -Arguments @("-c", "import sys,struct; assert sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8, 'Python 3.11 x64 is required'; print(sys.version)")
$venvDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".venv"))
$workspaceDir = [IO.Path]::GetFullPath($PSScriptRoot)
if ([IO.Path]::GetDirectoryName($venvDir) -ne $workspaceDir) { throw "venv 路径不在项目目录内。" }
$venvExe = Join-Path $venvDir "Scripts\python.exe"
if (Test-Path -LiteralPath $venvDir) {
    $valid = $false
    if (Test-Path -LiteralPath $venvExe) {
        & $venvExe -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8 else 1)"
        $valid = $LASTEXITCODE -eq 0
    }
    if (-not $valid) {
        $backupDir = Join-Path $workspaceDir (".venv-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss-fff"))
        if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($backupDir)) -ne $workspaceDir) { throw "备份路径不在项目目录内。" }
        Move-Item -LiteralPath $venvDir -Destination $backupDir
        Write-Output "已保留错误版本环境备份：$backupDir"
    }
}
if (-not (Test-Path -LiteralPath $venvExe)) {
    Invoke-CheckedPython -Executable $Python311 -Arguments @("-m", "venv", $venvDir)
}
Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "ensurepip", "--upgrade")
Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "install", "-r", "requirements-core.txt")
if ($CoreOnly) {
    Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "check")
    Write-Output "Python 3.11 核心环境就绪，可运行 .\run.ps1 和测试；尚未安装真实换脸后端。"
    exit 0
}
& $venvExe -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('insightface') else 1)"
$hasBackend = $LASTEXITCODE -eq 0
if (-not $hasBackend) {
    $hasCompiler = $null -ne (Get-Command cl.exe -ErrorAction SilentlyContinue)
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not $hasCompiler -and (Test-Path -LiteralPath $vswhere)) {
        $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        $hasCompiler = [bool]$vsPath
    }
    if (-not $hasCompiler) {
        throw "核心环境已就绪，但 InsightFace 需要 C++ 编译器。请从 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 安装‘使用 C++ 的桌面开发’、MSVC x64 与 Windows SDK，重开 PowerShell 后再次运行 .\setup.ps1。"
    }
    Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "install", "-r", "requirements-source-build.txt")
    Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "install", "--no-build-isolation", "-r", "requirements.txt")
} else {
    Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
}
Invoke-CheckedPython -Executable $venvExe -Arguments @("-m", "pip", "check")
Invoke-CheckedPython -Executable $venvExe -Arguments @("-c", "import insightface, onnxruntime; print('后端导入成功', onnxruntime.get_available_providers())")
Write-Output "安装完成。运行 .\run.ps1 并配置已授权的本地模型。"
