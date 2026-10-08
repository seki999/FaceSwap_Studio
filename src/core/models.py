import hashlib
from pathlib import Path
from typing import Protocol
import numpy as np
from .errors import StudioError
from .images import ImageProcessor
from src.utils.config import ROOT

class DetectorBackend(Protocol):
    def detect(self, image: np.ndarray) -> list: ...

class SwapperBackend(Protocol):
    def swap(self, image: np.ndarray, target: object, source: object) -> np.ndarray: ...

class ModelManager:
    KEYS = ("detector_path", "recognition_path", "swapper_path")

    def __init__(self, config: dict, root: Path = ROOT):
        self.config, self.root = config.copy(), root
        self.loaded = None

    def paths(self) -> dict[str, Path]:
        paths = {}
        if self.config.get("inference_provider") != "CPUExecutionProvider":
            raise StudioError("当前后端仅支持 CPUExecutionProvider。")
        if self.config.get("recognition_family") != "buffalo_l_w600k_r50":
            raise StudioError("inswapper 原型要求兼容的 buffalo_l / w600k_r50 识别模型。")
        for key in self.KEYS:
            value = self.config.get(key)
            if not isinstance(value, str) or not value.strip():
                raise StudioError("未配置本地模型：" + key)
            path = Path(value).expanduser()
            path = path if path.is_absolute() else self.root / path
            if path.suffix.lower() != ".onnx" or not path.is_file():
                raise StudioError("缺少或无效的本地 ONNX 模型：" + key + "。请在设置中选择已授权文件。")
            paths[key] = path
        return paths

    def load(self) -> tuple:
        if self.loaded is not None:
            return self.loaded
        paths = self.paths()
        try:
            for key, path in paths.items():
                expected = self.config.get("sha256", {}).get(key)
                if expected:
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(chunk)
                    if digest.hexdigest().lower() != expected.lower():
                        raise StudioError("模型 SHA256 不匹配：" + key)
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            options.inter_op_num_threads = 1
            sessions = [ort.InferenceSession(str(paths[key]), sess_options=options, providers=["CPUExecutionProvider"]) for key in self.KEYS]
            detector_session, recognition_session, swapper_session = sessions
            if len(detector_session.get_outputs()) < 5:
                raise StudioError("检测模型类型不匹配，需要 SCRFD 五点检测接口。")
            if recognition_session.get_inputs()[0].shape[1:] != [3, 112, 112] or recognition_session.get_outputs()[0].shape[-1] != 512:
                raise StudioError("识别模型需要 112×112 输入和 512 维输出。")
            inputs = swapper_session.get_inputs()
            if len(inputs) != 2 or inputs[0].shape[1:] != [3,128,128] or inputs[1].shape[-1] != 512:
                raise StudioError("换脸模型输入不符合 inswapper_128 接口。")
            from insightface.model_zoo.retinaface import RetinaFace
            from insightface.model_zoo.arcface_onnx import ArcFaceONNX
            from insightface.model_zoo.inswapper import INSwapper
            detector = RetinaFace(model_file=str(paths["detector_path"]), session=detector_session)
            recognition = ArcFaceONNX(model_file=str(paths["recognition_path"]), session=recognition_session)
            swapper = INSwapper(model_file=str(paths["swapper_path"]), session=swapper_session)
            detector.prepare(ctx_id=-1, input_size=(640, 640), det_thresh=0.5)
            recognition.prepare(ctx_id=-1)
            if tuple(swapper.input_size) != (128, 128) or swapper.emap.shape != (512, 512):
                raise StudioError("换脸模型不符合 inswapper_128 / 512 维 embedding 接口。")
            self.loaded = (FaceDetector(detector, recognition), FaceSwapper(swapper))
            return self.loaded
        except StudioError:
            raise
        except ImportError as exc:
            raise StudioError("缺少推理依赖。请在 Python 3.11 venv 中安装 requirements.txt；InsightFace 0.7.3 需要 MSVC C++ Build Tools。") from exc
        except Exception as exc:
            raise StudioError("模型加载失败。请检查 ONNX 文件、依赖及识别模型兼容性。") from exc

class FaceDetector:
    def __init__(self, detector, recognition):
        self.detector, self.recognition = detector, recognition

    def detect(self, image: np.ndarray) -> list:
        ImageProcessor.validate(image)
        from insightface.app.common import Face
        boxes, landmarks = self.detector.detect(image, max_num=0)
        faces = []
        for index, box in enumerate(boxes):
            if landmarks is None:
                raise StudioError("检测模型缺少五点人脸关键点。")
            face = Face(bbox=box[:4], kps=landmarks[index], det_score=float(box[4]))
            self.recognition.get(image, face)
            if face.embedding.shape != (512,) or not np.isfinite(face.embedding).all() or np.linalg.norm(face.embedding) == 0:
                raise StudioError("识别模型输出无效的身份特征。")
            faces.append(face)
        return sorted(faces, key=lambda face: float(face.det_score), reverse=True)

    @staticmethod
    def warnings(face) -> list[str]:
        box, points = face.bbox, face.kps
        warnings = []
        if min(box[2] - box[0], box[3] - box[1]) < 80:
            warnings.append("人脸较小，结果清晰度可能有限")
        if face.det_score < 0.7:
            warnings.append("检测置信度较低，可能存在遮挡")
        eye_distance = max(float(np.linalg.norm(points[1] - points[0])), 1)
        if abs(float(points[2][0] - (points[0][0] + points[1][0]) / 2)) / eye_distance > 0.35:
            warnings.append("姿态角度较大，可能影响融合")
        return warnings

class FaceSwapper:
    def __init__(self, model):
        self.model = model

    def swap(self, image: np.ndarray, target, source) -> np.ndarray:
        # InsightFace performs affine alignment, local edge mask feathering and paste-back.
        return self.model.get(image, target, source, paste_back=True)
