import json
import pytest
from src.core.models import ModelManager
from src.core.errors import StudioError
from src.utils.config import ConfigStore

@pytest.fixture
def config():
    return {"detector_path":"a.onnx","recognition_path":"b.onnx","swapper_path":"c.onnx","recognition_family":"buffalo_l_w600k_r50","inference_provider":"CPUExecutionProvider"}

def test_missing_models(tmp_path,config):
    with pytest.raises(StudioError,match="缺少"):
        ModelManager(config,tmp_path).paths()

@pytest.mark.parametrize("value", ["", "wrong.txt", "missing.onnx", None])
def test_wrong_path(tmp_path,config,value):
    config["detector_path"]=value
    with pytest.raises(StudioError):
        ModelManager(config,tmp_path).paths()

def test_invalid_onnx(tmp_path,config):
    for key in ModelManager.KEYS:
        (tmp_path/config[key]).write_bytes(b"invalid onnx")
    with pytest.raises(StudioError,match="模型加载失败"):
        ModelManager(config,tmp_path).load()

def test_sha256(tmp_path,config):
    for key in ModelManager.KEYS:
        (tmp_path/config[key]).write_bytes(b"invalid")
    config["sha256"]={"detector_path":"0"*64}
    with pytest.raises(StudioError,match="SHA256"):
        ModelManager(config,tmp_path).load()

def test_provider_and_family(tmp_path,config):
    config["recognition_family"]="other"
    with pytest.raises(StudioError,match="兼容"):
        ModelManager(config,tmp_path).paths()
    config["inference_provider"]="CUDAExecutionProvider"
    with pytest.raises(StudioError,match="CPU"):
        ModelManager(config,tmp_path).paths()

def test_config_roundtrip(tmp_path,config):
    store=ConfigStore(tmp_path/"用户设置.json"); store.save(config)
    assert all(ConfigStore(store.path).config[key] == value for key,value in config.items())

def test_load_cached(config):
    manager=ModelManager(config); manager.loaded=(object(),object())
    assert manager.load() is manager.loaded
