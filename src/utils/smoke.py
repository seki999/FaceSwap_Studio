"""Explicit diagnostic mode: tests runtime plumbing, never pretends to swap faces."""
import json
import tempfile
from pathlib import Path
import numpy as np
from PySide6.QtCore import QTimer
from src.core.images import ImageProcessor

def run_smoke(app, report_path: Path) -> int:
    report = {"gui_started": False, "unicode_image_io": False, "onnx_cpu_inference": False, "insightface_available": False, "real_face_swap_verified": False}
    try:
        from src.ui.window import MainWindow
        from src.utils.config import ConfigStore
        with tempfile.TemporaryDirectory(prefix="FaceSwapStudio_smoke_") as temp:
            directory = Path(temp)
            window = MainWindow(ConfigStore(directory / "config.json"), check_models=False)
            window.show()
            app.processEvents()
            report["gui_started"] = window.isVisible()
            image = np.full((96,128,3), 128, np.uint8)
            path = directory / "中文_日本語.png"
            ImageProcessor.save(image,path)
            loaded = ImageProcessor.load(path)
            report["unicode_image_io"] = bool(np.array_equal(image, loaded))
            window.previews[0].set_image(loaded)
            app.processEvents()
            window.close()
        import onnxruntime as ort
        from onnx import helper, TensorProto
        graph = helper.make_graph([helper.make_node("Identity",["x"],["y"])],"diagnostic",[helper.make_tensor_value_info("x",TensorProto.FLOAT,[1])],[helper.make_tensor_value_info("y",TensorProto.FLOAT,[1])])
        model = helper.make_model(graph,opset_imports=[helper.make_opsetid("",13)])
        model.ir_version=9
        session = ort.InferenceSession(model.SerializeToString(),providers=["CPUExecutionProvider"])
        report["onnx_cpu_inference"] = bool(session.run(None,{"x":np.array([1],np.float32)})[0][0] == 1)
        try:
            import insightface
            report["insightface_available"] = True
        except ImportError:
            pass
        code = 0
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        code = 1
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return code
