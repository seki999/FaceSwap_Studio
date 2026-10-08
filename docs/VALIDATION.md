# 验证记录与剩余验收

日期：2026-10-08（日本时间）。所有已完成项来自实际执行，不包含真实模型效果的推测。

## 环境

Windows x64，项目私有 `.venv`，CPython 3.11.13。原系统 Python 是 3.13.14，使用 uv 获取独立 Python 3.11 并创建环境；已补装 venv pip。未修改系统 Python 版本。

## 分阶段检查

1. 目录、固定依赖、默认配置和基础三栏 UI 已生成。Qt 6.8.1 原生 Windows 渲染检查通过；中文字体正常。无脸照片的 UI 截图为 `docs/interface.png`。
2. 图片导入、Unicode/扩展长路径、EXIF、多格式读取、预览、自动后台检测接线通过单元测试。
3. 实现显式 CPU session + InsightFace RetinaFace/ArcFace/INSwapper 适配器，不经过 FaceAnalysis 下载入口。模型接口/embedding/128×128 投影矩阵检查已实现；尚无合法权重进行实际人脸推理。
4. QThread Signal、单任务门控、取消前后、推理异常、结果尺寸、连续处理、原子保存失败保护通过单元测试。
5. 模型缺失、配置错误、损坏 ONNX、SHA256、配置读写、选择与重置测试通过；真实集成测试明确 skipped。
6. 中文 README、模型说明、venv 运行脚本和 PyInstaller onedir/onefile 构建脚本已生成。onedir 诊断构建及运行 smoke 通过。

## 实际测试

`python -m pytest -q`：**42 passed, 1 skipped**。包括模型缺失/路径错误、损坏和不支持的图片、中日文文件名、图片读写、多脸与来源/目标选择、取消、推理异常、连续处理、重置、后台线程安全、非法数组/ONNX 输入。UI 流程使用明确的 mock 后端，不声称 mock 结果是 AI 换脸。

`python -m pip check`：已安装的 GUI/ONNX/测试/构建依赖子集显示 **No broken requirements found**。其精确版本记录在 `constraints-validated.txt`。这不证明尚未安装的 InsightFace 完整依赖链兼容。

原始安装失败：`insightface==0.7.3` 从官方源码发行包构建扩展时，`error: Microsoft Visual C++ 14.0 or greater is required`。本机无 MSVC/Windows SDK。该依赖未安装成功。

修复：安装官方 Microsoft C++ Build Tools 的“使用 C++ 的桌面开发”及 x64 MSVC / Windows SDK，重开 PowerShell，然后在 Python 3.11 venv 执行：

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe -m pip check
```

## EXE 验证

构建命令：`.\build_exe.ps1 -AllowMissingBackend`，输出 `dist/FaceSwapStudio/FaceSwapStudio.exe`。这是 **诊断包**，缺少 InsightFace，不能完成真实换脸，不用于完整产品发布。

源码和 EXE 都实际执行了显式诊断模式。EXE 直接运行，退出码 0，未启动任何外部 Python 进程：

```json
{
  "gui_started": true,
  "unicode_image_io": true,
  "onnx_cpu_inference": true,
  "insightface_available": false,
  "real_face_swap_verified": false
}
```

CPU 检查使用现场生成的 ONNX Identity 图，只验证 ORT DLL/CPU 推理；图像检查使用灰色测试图，只验证文件读写，不是人像或换脸推理。检查工具：

```powershell
.\dist\FaceSwapStudio\FaceSwapStudio.exe --smoke-report "$PWD\exe-smoke.json"
```

Qt 主界面渲染正常。offscreen 插件没有读取 Windows 中文字体数据库，因此界面视觉检查使用实际 Windows Qt 平台完成；pytest 用 offscreen 做行为/线程测试。

## 尚未验证

- InsightFace 0.7.3 本机成功安装和完整依赖链。
- 合法检测/识别/换脸模型加载、身份迁移效果、肤色/姿态/边界质量与 CPU 耗时。
- 完整后端 EXE 在无 Python 的另一台干净 Windows 11 机器上的实际运行。
- 授权模型下的完整 EXE 人脸检测、选择、换脸及导出验收。
- onefile 构建、不同 DPI 显示器之间移动、最低配置性能基准。
- 文件对话框在所有 Windows 长路径策略组合下的人工验收。

## 完整发布前清单

1. 成功安装全部 requirements，正常导入 InsightFace，并执行标准 `.\build_exe.ps1`（不传诊断开关）。
2. 在已获得许可的本地 ONNX 文件上填写用户模型设置，检查张量和可选 SHA256。
3. 用已授权的单脸、多脸、遮挡、侧脸照片检查选定目标人脸及背景保持情况。
4. 用 `FSS_TEST_SOURCE/FSS_TEST_TARGET` 跑真实集成测试，不能 skipped。
5. 在另一台无 Python 的 Windows 11 机器执行 EXE smoke、导入中日文路径、检测、取消、换脸、PNG/JPEG 保存与覆盖/磁盘错误检查。
6. 检查 100%/150%/200% DPI、小窗口和不同显示器；记录 CPU 时间、最大内存和真实效果限制。

本仓库与打包脚本不附带或复制模型权重，不包含个人照片。

## 2026-10-08 安装日志跟进

用户再次运行系统 `python -m venv .venv`，把环境改为了 CPython 3.13.14；日志中的 `cp313` wheel 和 `cpython-313` 编译目录证实了这一点。最终安装仍失败于缺少 MSVC C++ 编译器。

已新增 `setup.ps1`：验证 3.11 x64、保留错误环境备份、创建干净 venv、安装核心依赖、完整安装前预检查 MSVC。`-CoreOnly` 只安装可运行界面与测试的组件；完整模式在编译前准备固定版本的 NumPy/Cython/setuptools/wheel，使用非隔离构建。后端是否能编译仍需安装 MSVC 后实际验证。

README 已改为优先运行 setup 脚本，避免误用系统 Python 3.13。备份目录已加入 .gitignore。

恢复后实际验证：Python 3.11.13；`pip check` 无冲突；pytest **42 passed, 1 skipped**；源码 smoke 确认 GUI、Unicode 图片读写和 CPU ONNX 推理通过，InsightFace 仍缺失。脚本已实际拒绝显式传入的 Python 3.13，拒绝时保留新 3.11 环境。
