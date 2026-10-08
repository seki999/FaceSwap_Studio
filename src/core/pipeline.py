from threading import Event
from typing import Callable
import numpy as np
from .errors import StudioError, Cancelled
from .images import ImageProcessor

class FaceSwapPipeline:
    def __init__(self, manager=None, detector=None, swapper=None):
        self.manager, self.detector, self.swapper = manager, detector, swapper

    def check(self, cancel: Event) -> None:
        if cancel.is_set():
            raise Cancelled("已取消；正在执行的单次推理完成后停止。")

    def ensure_models(self) -> None:
        if self.detector is None:
            self.detector, self.swapper = self.manager.load()

    def detect(self, image: np.ndarray, cancel: Event) -> list:
        self.check(cancel)
        ImageProcessor.validate(image)
        self.ensure_models()
        self.check(cancel)
        faces = self.detector.detect(image)
        self.check(cancel)
        if not faces:
            raise StudioError("没有检测到人脸，请选择清晰、正面的人物图片。")
        return faces

    def run(self, source: np.ndarray, target: np.ndarray, source_faces: list, target_faces: list,
            source_index: int, target_index: int, cancel: Event, progress: Callable = lambda *_: None) -> np.ndarray:
        self.check(cancel)
        ImageProcessor.validate(source)
        ImageProcessor.validate(target)
        if not 0 <= source_index < len(source_faces) or not 0 <= target_index < len(target_faces):
            raise StudioError("请选择有效的来源与目标人脸。")
        self.ensure_models()
        self.check(cancel)
        progress(35, "CPU 换脸推理中；此步骤不能立即中断")
        try:
            result = self.swapper.swap(target, target_faces[target_index], source_faces[source_index])
        except Exception as exc:
            raise StudioError("换脸推理失败，请检查模型与输入图片。") from exc
        self.check(cancel)
        ImageProcessor.validate(result)
        if result.shape != target.shape:
            raise StudioError("模型返回了错误的输出尺寸。")
        progress(100, "处理完成")
        return result
