import logging
import sys
from logging.handlers import RotatingFileHandler
from PySide6.QtWidgets import QApplication, QMessageBox
from src.utils.config import ConfigStore, DATA
from src.ui.window import MainWindow

def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(DATA / "studio.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("FaceSwap Studio")
    if "--smoke-report" in sys.argv:
        from pathlib import Path
        from src.utils.smoke import run_smoke
        position = sys.argv.index("--smoke-report")
        return run_smoke(app, Path(sys.argv[position + 1]))
    try:
        window = MainWindow(ConfigStore())
    except Exception as exc:
        logging.error("Startup failure: %s", type(exc).__name__)
        QMessageBox.critical(None, "启动失败", "无法读取配置。请检查用户数据目录的 model_config.json。")
        return 1
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
