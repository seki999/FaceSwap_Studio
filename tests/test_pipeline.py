from threading import Event
from unittest.mock import Mock
import numpy as np
import pytest
from src.core.errors import StudioError, Cancelled
from src.core.pipeline import FaceSwapPipeline

def pipeline(faces,image):
    detector=Mock(); detector.detect.return_value=faces
    swapper=Mock(); swapper.swap.return_value=image.copy()
    return FaceSwapPipeline(detector=detector,swapper=swapper)

def test_no_face(image):
    with pytest.raises(StudioError,match="没有检测"):
        pipeline([],image).detect(image,Event())

def test_multiple_faces(image,faces):
    assert pipeline(faces,image).detect(image,Event()) == faces

@pytest.mark.parametrize("source_index,target_index",[(0,1),(1,0),(1,1)])
def test_selected_faces(image,faces,source_index,target_index):
    p=pipeline(faces,image)
    p.run(image,image,faces,faces,source_index,target_index,Event())
    args=p.swapper.swap.call_args.args
    assert args[1] is faces[target_index] and args[2] is faces[source_index]

def test_invalid_selection(image,faces):
    p=pipeline(faces,image)
    with pytest.raises(StudioError,match="选择"):
        p.run(image,image,faces,faces,-1,0,Event())
    p.swapper.swap.assert_not_called()

def test_cancel_before(image,faces):
    p=pipeline(faces,image); event=Event(); event.set()
    with pytest.raises(Cancelled):
        p.run(image,image,faces,faces,0,0,event)
    p.swapper.swap.assert_not_called()

def test_cancel_after_inference(image,faces):
    p=pipeline(faces,image); event=Event()
    def swap(*args):
        event.set(); return image.copy()
    p.swapper.swap.side_effect=swap
    with pytest.raises(Cancelled):
        p.run(image,image,faces,faces,0,0,event)

def test_inference_failure(image,faces):
    p=pipeline(faces,image); p.swapper.swap.side_effect=RuntimeError("failure")
    with pytest.raises(StudioError,match="推理失败"):
        p.run(image,image,faces,faces,0,0,Event())

def test_continuous(image,faces):
    p=pipeline(faces,image)
    for _ in range(4):
        result=p.run(image,image,faces,faces,0,0,Event())
        assert result.shape == image.shape
    assert p.swapper.swap.call_count == 4

def test_invalid_input(image,faces):
    with pytest.raises(StudioError,match="非法"):
        pipeline(faces,image).detect(np.zeros((10,10)),Event())

def test_wrong_result_dimensions(image,faces):
    p=pipeline(faces,image); p.swapper.swap.return_value=image[:10]
    with pytest.raises(StudioError,match="尺寸"):
        p.run(image,image,faces,faces,0,0,Event())
