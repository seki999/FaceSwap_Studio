from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QProgressBar, QDialog
from src.core.errors import StudioError
from src.core.images import ImageProcessor
from src.core.models import ModelManager, FaceDetector
from src.core.pipeline import FaceSwapPipeline
from src.workers.task import TaskThread
from .preview import ImagePreview
from .settings import ModelSettings

class MainWindow(QMainWindow):
    def __init__(self, store, pipeline=None, check_models=True):
        super().__init__()
        self.store = store
        self.pipeline = pipeline or FaceSwapPipeline(ModelManager(store.config))
        self.images = [None, None]
        self.faces = [[], []]
        self.paths = [None, None]
        self.result_image = None
        self.worker = None
        self.pending_detection = None
        self.task_cancellable = True
        self.setWindowTitle("FaceSwap Studio")
        self.resize(1200, 800)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(20,20,20,20); layout.setSpacing(16)
        top = QHBoxLayout()
        title = QLabel("FaceSwap Studio  ·  本地 CPU 图片换脸")
        title.setStyleSheet("font-size:22px; font-weight:600")
        top.addWidget(title); top.addStretch()
        self.theme = QComboBox(); self.theme.addItems(["深色主题", "浅色主题"])
        self.theme.currentIndexChanged.connect(self.apply_theme); top.addWidget(self.theme)
        self.settings_button = QPushButton("模型设置"); self.settings_button.clicked.connect(self.settings)
        top.addWidget(self.settings_button); layout.addLayout(top)
        layout.addWidget(QLabel("请仅处理本人或已获授权的人物照片，不得用于冒充、欺骗或侵权。所有图片仅在本地处理。"))
        columns = QHBoxLayout(); self.previews = []; self.selectors = []; self.import_buttons = []
        for index, name in enumerate(("A · 来源人脸", "B · 目标图片", "C · 换脸结果")):
            column = QVBoxLayout(); column.addWidget(QLabel(name))
            preview = ImagePreview(index < 2); self.previews.append(preview); column.addWidget(preview, 1)
            if index < 2:
                button = QPushButton("选择图片")
                button.clicked.connect(lambda checked=False, i=index: self.choose(i))
                self.import_buttons.append(button); column.addWidget(button)
                selector = QComboBox(); selector.currentIndexChanged.connect(lambda selected, i=index: self.select_face(i, selected))
                self.selectors.append(selector); column.addWidget(selector)
                preview.file_dropped.connect(lambda path, i=index: self.import_image(i, Path(path)))
                preview.choose_requested.connect(lambda i=index: self.choose(i))
                preview.face_clicked.connect(selector.setCurrentIndex)
            else:
                column.addWidget(QLabel("保留目标尺寸 · 128×128 模型面部细节有限"))
            columns.addLayout(column, 1)
        layout.addLayout(columns, 1)
        controls = QHBoxLayout()
        self.buttons = {}
        for label, callback in (("检测人脸", self.detect_all), ("开始换脸", self.swap), ("取消", self.cancel), ("保存图片", self.save), ("重置", self.reset)):
            button = QPushButton(label); button.clicked.connect(callback); controls.addWidget(button); self.buttons[label] = button
        layout.addLayout(controls)
        self.progress_bar = QProgressBar(); layout.addWidget(self.progress_bar)
        self.status = QLabel("就绪 · 模型从本地加载，不会自动下载")
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.apply_theme(0); self.set_busy(False)
        if check_models:
            QTimer.singleShot(0, self.startup_check)

    def apply_theme(self, index: int) -> None:
        bg, fg, control = ("#141a24", "#e3eaf4", "#293445") if index == 0 else ("#f1f4f8", "#182434", "#ffffff")
        self.setStyleSheet(f"QWidget {{background:{bg}; color:{fg}; font-family:'Microsoft YaHei UI'; font-size:14px;}} QPushButton,QComboBox,QLineEdit {{background:{control}; padding:9px; border:1px solid #607086; border-radius:5px;}} QPushButton:disabled {{color:#808895;}} QProgressBar {{border:1px solid #607086; text-align:center;}} QProgressBar::chunk {{background:#238f79;}}")

    def startup_check(self) -> None:
        try:
            self.pipeline.manager.paths()
        except StudioError as exc:
            self.status.setText(str(exc)); self.settings()

    def settings(self) -> None:
        if self.worker is not None:
            return
        if ModelSettings(self.store, self).exec() == QDialog.Accepted:
            self.pipeline = FaceSwapPipeline(ModelManager(self.store.config))
            self.faces = [[], []]
            for i in range(2):
                self.selectors[i].clear(); self.previews[i].faces = []; self.previews[i].update()
            self.invalidate_result(); self.detect_all()

    def set_busy(self, busy: bool) -> None:
        for button in self.buttons.values():
            button.setEnabled(not busy)
        self.buttons["取消"].setEnabled(busy)
        self.buttons["保存图片"].setEnabled(not busy and self.result_image is not None)
        for widget in self.import_buttons + self.selectors + [self.settings_button]:
            widget.setEnabled(not busy)
        for preview in self.previews[:2]:
            preview.setEnabled(not busy)

    def start_task(self, operation, receiver, cancellable: bool = True) -> None:
        if self.worker is not None:
            return
        self.progress_bar.setValue(0); self.set_busy(True)
        self.task_cancellable = cancellable
        self.buttons["取消"].setEnabled(cancellable)
        self.worker = TaskThread(operation, self)
        self.worker.result.connect(receiver)
        self.worker.failed.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.elapsed.connect(self.on_elapsed)
        self.worker.finished.connect(self.task_finished)
        self.worker.start()

    @Slot(int, str)
    def on_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value); self.status.setText(message)

    @Slot(str)
    def on_error(self, message: str) -> None:
        self.status.setText(message)

    @Slot(float)
    def on_elapsed(self, seconds: float) -> None:
        self.status.setText(self.status.text() + f" · 耗时 {seconds:.2f} 秒")

    @Slot()
    def task_finished(self) -> None:
        worker = self.worker; self.worker = None
        worker.deleteLater(); self.set_busy(False)
        if self.pending_detection is not None:
            index = self.pending_detection
            self.pending_detection = None
            self.detect_all(index)

    def choose(self, index: int) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片 (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            self.import_image(index, Path(path))

    def invalidate_result(self) -> None:
        self.result_image = None; self.previews[2].set_image(None)
        self.buttons["保存图片"].setEnabled(False)

    def import_image(self, index: int, path: Path) -> None:
        if self.worker is not None:
            return
        self.invalidate_result()
        self.faces[index] = []; self.selectors[index].clear()
        self.images[index] = None; self.previews[index].set_image(None)
        self.paths[index] = path
        def operation(cancel, progress):
            progress(10, "读取图片")
            image = ImageProcessor.load(path)
            return (index, image)
        self.start_task(operation, self.loaded)

    @Slot(object)
    def loaded(self, payload):
        index, image = payload
        self.images[index] = image; self.previews[index].set_image(image)
        self.status.setText("图片已加载，准备自动检测")
        # Schedule after QThread.finished has released the single task slot.
        self.pending_detection = index

    def detect_all(self, only: int | None = None) -> None:
        if self.worker is not None:
            return
        indices = [i for i in range(2) if self.images[i] is not None and (only is None or isinstance(only, bool) or i == only)]
        if not indices:
            self.status.setText("请先加载来源和目标图片。")
            return
        def operation(cancel, progress):
            detected = []
            for step, i in enumerate(indices):
                progress(int(100*step/len(indices)), "检测来源人脸" if i == 0 else "检测目标人脸")
                try:
                    faces = self.pipeline.detect(self.images[i], cancel)
                    detected.append((i, faces, ""))
                except StudioError as exc:
                    from src.core.errors import Cancelled
                    if isinstance(exc, Cancelled):
                        raise
                    detected.append((i, [], str(exc)))
            return detected
        self.start_task(operation, self.detected)

    @Slot(object)
    def detected(self, payload):
        errors = []
        for i, faces, error in payload:
            self.faces[i] = faces
            self.selectors[i].clear()
            self.selectors[i].addItems([f"人脸 {j+1} · 置信度 {face.det_score:.0%}" for j, face in enumerate(faces)])
            self.previews[i].faces = faces
            self.previews[i].selected = 0 if faces else -1
            self.previews[i].update()
            if error:
                errors.append(error)
            elif faces:
                errors.extend(FaceDetector.warnings(faces[0]))
        self.progress_bar.setValue(100)
        self.status.setText("；".join(errors) if errors else "检测完成，请确认来源与目标人脸选择。")

    def select_face(self, index: int, selected: int) -> None:
        self.previews[index].selected = selected; self.previews[index].update()
        self.invalidate_result()
        if 0 <= selected < len(self.faces[index]):
            warnings = FaceDetector.warnings(self.faces[index][selected])
            self.status.setText("；".join(warnings) if warnings else "已选择人脸 " + str(selected+1))

    def swap(self) -> None:
        if self.worker is not None:
            return
        if any(image is None for image in self.images) or any(not faces for faces in self.faces):
            self.status.setText("请先加载两张图片并成功检测、选择人脸。")
            return
        a, b = [selector.currentIndex() for selector in self.selectors]
        self.invalidate_result()
        self.start_task(lambda cancel, progress: self.pipeline.run(*self.images, *self.faces, a, b, cancel, progress), self.swapped)

    @Slot(object)
    def swapped(self, image):
        self.result_image = image; self.previews[2].set_image(image)
        self.status.setText("换脸完成，可保存完整分辨率图片。")

    def cancel(self) -> None:
        if self.worker is not None and self.task_cancellable:
            self.worker.cancel(); self.status.setText("已请求取消；等待当前不可中断步骤完成，结果将被丢弃。")

    def save(self) -> None:
        if self.result_image is None or self.worker is not None:
            return
        name = self.paths[1].stem + "_faceswap_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", str(self.paths[1].parent / name), "PNG (*.png);;JPEG (*.jpg *.jpeg)")
        if not path:
            return
        output = Path(path)
        if not output.suffix:
            output = output.with_suffix(".png")
        if output.exists() and QMessageBox.question(self, "确认覆盖", "文件已存在，是否覆盖？") != QMessageBox.Yes:
            return
        image = self.result_image
        self.start_task(lambda cancel, progress: ImageProcessor.save(image, output, overwrite=True), self.saved, cancellable=False)
        self.status.setText("正在保存完整分辨率图片…")

    @Slot(object)
    def saved(self, _):
        self.status.setText("图片保存成功。")

    def reset(self) -> None:
        if self.worker is not None:
            return
        self.images = [None,None]; self.faces = [[],[]]; self.paths = [None,None]
        for selector in self.selectors:
            selector.clear()
        for preview in self.previews:
            preview.set_image(None)
        self.invalidate_result(); self.progress_bar.setValue(0); self.status.setText("已重置。")

    def closeEvent(self, event):
        if self.worker is not None:
            self.cancel(); self.status.setText("请等待后台任务完成后再关闭窗口。" if self.task_cancellable else "正在提交保存文件，请等待保存结束后关闭窗口。")
            event.ignore()
        else:
            event.accept()
