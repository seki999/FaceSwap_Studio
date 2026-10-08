import logging
import time
from threading import Event
from PySide6.QtCore import QThread, Signal
from src.core.errors import Cancelled, StudioError

class TaskThread(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)
    elapsed = Signal(float)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.cancel_event = Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        started = time.perf_counter()
        try:
            result = self.operation(self.cancel_event, self.progress.emit)
            if not self.cancel_event.is_set():
                self.result.emit(result)
        except (Cancelled, StudioError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            # Do not log exception content, input paths, photos or embeddings.
            logging.error("Background operation failed: %s", type(exc).__name__)
            self.failed.emit("处理失败，请检查文件、模型与环境。")
        finally:
            self.elapsed.emit(time.perf_counter() - started)
