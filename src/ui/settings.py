from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QFileDialog, QDialogButtonBox, QMessageBox
from src.core.models import ModelManager

class ModelSettings(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("本地模型设置")
        self.resize(720, 300)
        layout = QVBoxLayout(self)
        note = QLabel("请选择已获得使用权限的本地 ONNX 模型。禁止自动下载。\n识别组件必须是与 inswapper 兼容的 buffalo_l / w600k_r50；同为 512 维不代表兼容。")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.fields = {}
        for key, label in zip(ModelManager.KEYS, ("检测模型", "识别模型", "换脸模型")):
            row = QHBoxLayout()
            edit = QLineEdit(store.config.get(key, ""))
            button = QPushButton("浏览")
            button.clicked.connect(lambda checked=False, field=edit: self.browse(field))
            row.addWidget(edit); row.addWidget(button)
            form.addRow(label, row)
            self.fields[key] = edit
        layout.addLayout(form)
        layout.addWidget(QLabel("CPUExecutionProvider · inswapper_128 · 不提供虚假的 AI 强度控件"))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse(self, field):
        path, _ = QFileDialog.getOpenFileName(self, "选择授权模型", "", "ONNX 模型 (*.onnx)")
        if path:
            field.setText(path)

    def save(self):
        values = self.store.config.copy()
        values.update({key: field.text().strip() for key, field in self.fields.items()})
        # Old checksums are invalid if their corresponding files changed.
        values["sha256"] = {key: value for key, value in values.get("sha256", {}).items() if values.get(key) == self.store.config.get(key)}
        try:
            ModelManager(values).paths()
            self.store.save(values)
        except Exception as exc:
            QMessageBox.warning(self, "配置失败", str(exc))
            return
        self.accept()
