param([switch]$OneFile, [switch]$AllowMissingBackend)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "请先创建 .venv。" }
& $pythonExe -c "import sys; assert sys.version_info[:2] == (3,11); import PySide6, onnxruntime, cv2, PIL, numpy, PyInstaller"
if ($LASTEXITCODE -ne 0) { throw "依赖预检查失败。" }
& $pythonExe -c "import insightface"
if ($LASTEXITCODE -ne 0 -and -not $AllowMissingBackend) { throw "InsightFace 不可用，请安装 C++ Build Tools 后重装依赖。仅界面诊断打包可使用 -AllowMissingBackend。" }
$mode = "--onedir"
if ($OneFile) { $mode = "--onefile" }
$buildArgs = @("--noconfirm", "--windowed", $mode, "--name", "FaceSwapStudio", "--add-data", "config/model_config.json;config", "--collect-all", "onnxruntime", "--collect-submodules", "insightface", "--collect-submodules", "onnx", "--exclude-module", "PyQt5", "--exclude-module", "PyQt6", "--manifest", "assets/windows.manifest", "main.py")
& $pythonExe -m PyInstaller @buildArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败。" }
$outputDir = Join-Path $PSScriptRoot "dist\FaceSwapStudio"
if ($OneFile) { $outputDir = Join-Path $PSScriptRoot "dist" }
New-Item -ItemType Directory -Force (Join-Path $outputDir "models") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $outputDir "config") | Out-Null
Copy-Item -LiteralPath "config/model_config.json" -Destination (Join-Path $outputDir "config/model_config.json")
Copy-Item -LiteralPath "docs/MODELS.md" -Destination (Join-Path $outputDir "models/README.md")
Write-Output "构建完成：$outputDir。请执行 docs/VALIDATION.md 的手工检查。未包含模型权重。"
