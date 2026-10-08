from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from src.core.images import ImageProcessor
from src.core.errors import StudioError

@pytest.mark.parametrize("name", ["中文照片.png", "日本語の写真.png", "photo.png"])
def test_unicode_load_save(tmp_path, image, name):
    path = tmp_path / name
    image[0,0] = [10,20,30]
    ImageProcessor.save(image,path)
    assert np.array_equal(ImageProcessor.load(path), image)

@pytest.mark.parametrize("suffix", [".jpg", ".jpeg", ".png", ".webp", ".bmp"])
def test_supported_formats(tmp_path, suffix):
    path=tmp_path / ("test"+suffix)
    Image.new("RGB", (20,30), "red").save(path)
    assert ImageProcessor.load(path).shape == (30,20,3)

def test_unsupported(tmp_path):
    with pytest.raises(StudioError,match="不支持"):
        ImageProcessor.load(tmp_path/"bad.gif")

def test_corrupt(tmp_path):
    path=tmp_path/"bad.png"; path.write_bytes(b"corrupt")
    with pytest.raises(StudioError,match="无法读取"):
        ImageProcessor.load(path)

def test_exif(tmp_path):
    path=tmp_path/"rotated.jpg"
    im=Image.new("RGB", (40,20)); exif=im.getexif(); exif[274]=6; im.save(path,exif=exif)
    assert ImageProcessor.load(path).shape[:2] == (40,20)

def test_limit(tmp_path, monkeypatch):
    path=tmp_path/"large.png"; Image.new("RGB",(20,20)).save(path)
    monkeypatch.setattr(ImageProcessor,"MAX_PIXELS",100)
    with pytest.raises(StudioError,match="像素"):
        ImageProcessor.load(path)

def test_save_overwrite(tmp_path,image):
    path=tmp_path/"result.png"; path.write_bytes(b"original")
    with pytest.raises(StudioError,match="覆盖"):
        ImageProcessor.save(image,path)
    assert path.read_bytes() == b"original"
    ImageProcessor.save(image,path,True)

def test_save_failed_preserves_original(tmp_path,image,monkeypatch):
    path=tmp_path/"result.png"; path.write_bytes(b"original")
    monkeypatch.setattr(Image.Image,"save",lambda *a,**k: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(StudioError,match="保存失败"):
        ImageProcessor.save(image,path,True)
    assert path.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [path]

def test_long_path(tmp_path,image):
    directory=tmp_path
    for i in range(6):
        directory=directory/("directory_"+str(i)+"x"*35)
    # Extended-length prefix avoids relying on the Windows registry policy.
    directory=Path("\\\\?\\"+str(directory.resolve()))
    directory.mkdir(parents=True)
    path=directory/"中文.png"; ImageProcessor.save(image,path)
    assert ImageProcessor.load(path).shape == image.shape
