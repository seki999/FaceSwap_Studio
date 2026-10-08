import time
from threading import get_ident, Event
from pathlib import Path
from PySide6.QtCore import QObject, Slot
from src.ui.window import MainWindow
from src.workers.task import TaskThread
from src.utils.config import ConfigStore
from src.core.pipeline import FaceSwapPipeline
from unittest.mock import Mock

def spin(app,predicate,timeout=5):
    end=time.monotonic()+timeout
    while not predicate() and time.monotonic()<end:
        app.processEvents(); time.sleep(.005)
    assert predicate()
    app.processEvents()

def test_reset(app,tmp_path,image,faces):
    w=MainWindow(ConfigStore(tmp_path/"config.json"),check_models=False)
    w.images=[image,image]; w.faces=[faces,faces]; w.result_image=image; w.reset()
    assert w.images == [None,None] and w.faces == [[],[]] and w.result_image is None
    w.close()

def test_thread_safety(app):
    main_id=get_ident(); recorded=[]; worker_ids=[]
    class Receiver(QObject):
        @Slot(object)
        def receive(self,value):
            recorded.append((get_ident(),value))
    receiver=Receiver()
    worker=TaskThread(lambda c,p: worker_ids.append(get_ident()) or 42)
    worker.result.connect(receiver.receive); worker.start()
    spin(app,lambda: bool(recorded)); worker.wait()
    assert recorded == [(main_id,42)] and worker_ids[0] != main_id

def test_no_parallel_jobs(app,tmp_path):
    w=MainWindow(ConfigStore(tmp_path/"config.json"),check_models=False)
    gate=Event(); results=[]
    w.start_task(lambda c,p: gate.wait(2),results.append)
    original=w.worker
    w.start_task(lambda c,p: 99,results.append)
    assert w.worker is original and not w.buttons["开始换脸"].isEnabled()
    gate.set(); spin(app,lambda: w.worker is None); w.close()

def test_ui_import_auto_detection_selection_and_swap(app,tmp_path,image,faces):
    from src.core.images import ImageProcessor
    detector=Mock(); detector.detect.return_value=faces
    swapper=Mock(); swapper.swap.return_value=image.copy()
    w=MainWindow(ConfigStore(tmp_path/"config.json"),FaceSwapPipeline(detector=detector,swapper=swapper),False)
    for i in range(2):
        path=tmp_path/f"授权测试{i}.png"; ImageProcessor.save(image,path)
        w.import_image(i,path)
        spin(app,lambda: w.worker is None and len(w.faces[i])==2)
        assert w.selectors[i].currentIndex()==0
    w.selectors[0].setCurrentIndex(1); w.selectors[1].setCurrentIndex(0)
    assert w.previews[0].selected==1 and w.previews[1].selected==0
    w.swap(); spin(app,lambda: w.worker is None)
    assert w.result_image is not None and w.buttons["保存图片"].isEnabled()
    assert swapper.swap.call_args.args[2] is faces[1]
    w.reset(); w.close()

def test_worker_cancel_discards_result(app):
    event=Event(); output=[]
    worker=TaskThread(lambda c,p: event.wait(2) or 42)
    worker.result.connect(output.append); worker.start(); worker.cancel(); event.set()
    worker.wait(); app.processEvents(); assert output==[]
