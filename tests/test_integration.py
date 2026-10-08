import os
from pathlib import Path
from threading import Event
import pytest
from src.core.models import ModelManager
from src.core.pipeline import FaceSwapPipeline
from src.core.images import ImageProcessor
from src.utils.config import ConfigStore
from src.core.errors import StudioError

@pytest.mark.integration
def test_real_local_models(tmp_path):
    manager=ModelManager(ConfigStore().config)
    try:
        manager.paths()
    except StudioError:
        pytest.skip("未配置有效的本地授权模型")
    pytest.importorskip("insightface",reason="缺少 InsightFace 运行依赖")
    source=os.environ.get("FSS_TEST_SOURCE"); target=os.environ.get("FSS_TEST_TARGET")
    if not source or not target:
        pytest.skip("请设置 FSS_TEST_SOURCE/FSS_TEST_TARGET 为已授权照片路径")
    # Existing but invalid models fail instead of being disguised as skipped.
    p=FaceSwapPipeline(manager); cancel=Event()
    a,b=ImageProcessor.load(Path(source)),ImageProcessor.load(Path(target))
    af,bf=p.detect(a,cancel),p.detect(b,cancel)
    output=p.run(a,b,af,bf,0,0,cancel)
    assert output.shape == b.shape
    ImageProcessor.save(output,tmp_path/"real_result.png")
