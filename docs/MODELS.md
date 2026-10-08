# 本地模型与接口

本项目不附带和不自动下载模型。只能从使用者已取得适当许可的本地来源加载。

原型匹配：

| 配置 | 接口 | 常见对应组件 |
| --- | --- | --- |
| detector_path | InsightFace SCRFD 五点检测，至少 5 个输出 | buffalo_l 的 det_10g.onnx |
| recognition_path | ArcFace，NCHW 112×112，512 维身份输出 | buffalo_l 的 w600k_r50.onnx |
| swapper_path | 图像 NCHW 128×128 + 512 维 latent，512×512 emap | inswapper_128.onnx |

默认 `recognition_family` 固定 `buffalo_l_w600k_r50`，运行时验证维度、关键点、特征有限性和模型投影矩阵。无法单靠张量维度证明实际训练来源匹配：使用者必须确认识别模型出处，必要时在 `sha256` 中固定各个文件哈希。

```json
{
  "detector_path": "models/det_10g.onnx",
  "recognition_path": "models/w600k_r50.onnx",
  "swapper_path": "models/inswapper_128.onnx",
  "recognition_family": "buffalo_l_w600k_r50",
  "inference_provider": "CPUExecutionProvider",
  "sha256": {}
}
```

SHA256 的键是 detector_path、recognition_path、swapper_path，值为完整 64 位十六进制字符串。可以在用户数据 JSON 手工填写。设置界面更换某个路径时清除该字段原先的 checksum，以免沿用旧文件校验值。可用 `Get-FileHash -Algorithm SHA256` 计算本地文件哈希。

相对路径基于源码项目根目录或 EXE 所在目录；绝对路径只写入用户数据配置。会话由 ONNX Runtime CPU 创建，InsightFace 适配器显式接收 session，不使用 FaceAnalysis 的模型包查找或下载入口。模型首次后台加载后缓存，配置修改创建新 manager。

融合由 InsightFace 的对齐、局部遮罩腐蚀/高斯羽化、逆仿射与回贴完成；目标未受遮罩影响的区域保留。没有额外的光照重建、超分辨率或独立肤色校正保证。只有选定目标人脸调用一次换脸推理。

官方源代码与模型许可证需要分别核对：[InsightFace](https://github.com/deepinsight/insightface)。仓库和 EXE 不再分发受限模型。
