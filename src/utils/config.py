import json
import os
import sys
from pathlib import Path

ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FaceSwapStudio"

class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or DATA / "model_config.json"
        self.config = json.loads((ROOT / "config/model_config.json").read_text(encoding="utf-8"))
        if self.path.exists():
            self.config.update(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, values: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)
        self.config = values.copy()
