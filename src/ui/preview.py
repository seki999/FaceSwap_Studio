import numpy as np
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy

class ImagePreview(QWidget):
    file_dropped = Signal(str)
    face_clicked = Signal(int)
    choose_requested = Signal()

    def __init__(self, editable=True):
        super().__init__()
        self.editable = editable
        self.image = None
        self.faces = []
        self.selected = -1
        self.setAcceptDrops(editable)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_image(self, image: np.ndarray | None) -> None:
        self.faces, self.selected = [], -1
        if image is None:
            self.image = None
        else:
            rgb = np.ascontiguousarray(image[:, :, ::-1])
            self.image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
        self.update()

    def rect_image(self) -> QRectF:
        if self.image is None:
            return QRectF()
        scale = min(self.width() / self.image.width(), self.height() / self.image.height())
        w, h = self.image.width() * scale, self.image.height() * scale
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202733"))
        if self.image is None:
            painter.setPen(QColor("#c3cedc"))
            painter.drawText(self.rect(), Qt.AlignCenter, "点击或拖入图片" if self.editable else "换脸结果将在这里显示")
            return
        area = self.rect_image()
        painter.drawImage(area, self.image)
        scale = area.width() / self.image.width()
        for index, face in enumerate(self.faces):
            x1, y1, x2, y2 = face.bbox
            painter.setPen(QPen(QColor("#57e6bd" if index == self.selected else "#ffd479"), 3))
            box = QRectF(area.x() + x1 * scale, area.y() + y1 * scale, (x2-x1)*scale, (y2-y1)*scale)
            painter.drawRect(box)
            painter.drawText(box.topLeft(), str(index + 1))

    def mousePressEvent(self, event):
        if self.image is None and self.editable:
            self.choose_requested.emit()
            return
        if self.image is None:
            return
        area = self.rect_image()
        scale = area.width() / self.image.width()
        x, y = (event.position().x()-area.x())/scale, (event.position().y()-area.y())/scale
        for index, face in enumerate(self.faces):
            x1, y1, x2, y2 = face.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.face_clicked.emit(index)
                break

    def dragEnterEvent(self, event):
        if self.editable and event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1 and event.mimeData().urls()[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self.editable and event.mimeData().hasUrls():
            self.file_dropped.emit(event.mimeData().urls()[0].toLocalFile())
