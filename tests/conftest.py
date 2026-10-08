import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
import numpy as np
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def image():
    return np.zeros((120,160,3), dtype=np.uint8)

@pytest.fixture
def faces():
    return [SimpleNamespace(bbox=np.array([10,10,100,110]), kps=np.array([[30,40],[70,40],[50,60],[35,80],[65,80]]), det_score=score, embedding=np.ones(512)) for score in (0.95,0.85)]
