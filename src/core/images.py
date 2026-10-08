import os
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from .errors import StudioError

class ImageProcessor:
    MAX_PIXELS = 24_000_000
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    @classmethod
    def load(cls, path: Path) -> np.ndarray:
        if path.suffix.lower() not in cls.EXTENSIONS:
            raise StudioError("不支持的图片格式，请选择 JPG、PNG、WEBP 或 BMP。")
        try:
            with Image.open(path) as image:
                if image.width * image.height > cls.MAX_PIXELS:
                    raise StudioError("图片超过 2400 万像素，请先缩小图片。")
                # Composite transparency on white; normalize EXIF without changing input.
                image = ImageOps.exif_transpose(image).convert("RGBA")
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image)
                return np.ascontiguousarray(np.asarray(background.convert("RGB"))[:, :, ::-1])
        except StudioError:
            raise
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise StudioError("无法读取图片，文件可能损坏或不可访问。") from exc

    @staticmethod
    def validate(image: np.ndarray) -> None:
        if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 2:
            raise StudioError("非法图片输入：需要 uint8 BGR 三通道图片。")

    @classmethod
    def save(cls, image: np.ndarray, path: Path, overwrite: bool = False) -> None:
        cls.validate(image)
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise StudioError("输出仅支持 PNG / JPG / JPEG。")
        if path.exists() and not overwrite:
            raise StudioError("输出文件已存在，需要确认覆盖。")
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as stream:
                temp = Path(stream.name)
            Image.fromarray(image[:, :, ::-1]).save(temp, quality=95)
            os.replace(temp, path)
        except OSError as exc:
            raise StudioError("保存失败，请检查目录权限与磁盘空间。") from exc
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
