from hashlib import sha256
from pathlib import Path
from datetime import date
import json, mimetypes

TODAY_DIR = Path("data/rossmann") / date.today().isoformat()
IMAGES_DIR = TODAY_DIR / "images"
SNAP_DIR   = TODAY_DIR / "snapshots"

for d in (TODAY_DIR, IMAGES_DIR, SNAP_DIR):
    d.mkdir(parents=True, exist_ok=True)

class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.f = path.open("a", encoding="utf-8")
    def write(self, obj: dict):
        self.f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    def close(self):
        self.f.close()

def _ext_from_ctype(ctype: str) -> str:
    if "jpeg" in ctype: return "jpg"
    if "png"  in ctype: return "png"
    if "webp" in ctype: return "webp"
    if "avif" in ctype: return "avif"
    return (mimetypes.guess_extension(ctype) or ".bin").lstrip(".")

def save_snapshot(name: str, html: str, png_bytes: bytes | None = None):
    (SNAP_DIR / f"{name}.html").write_text(html, encoding="utf-8")
    if png_bytes:
        (SNAP_DIR / f"{name}.png").write_bytes(png_bytes)
