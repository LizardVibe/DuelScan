"""Bereits heruntergeladene Artworks nachträglich verkleinern (wie database._save_small).

  python tools/shrink_art.py
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ygo_scanner.config import ART_DIR  # noqa: E402
from ygo_scanner.database import ART_MAX_SIDE, _save_small  # noqa: E402


def main() -> None:
    files = sorted(ART_DIR.glob("*.jpg"))
    before = sum(f.stat().st_size for f in files)
    shrunk = 0
    for k, f in enumerate(files, 1):
        img = cv2.imread(str(f))
        if img is not None and max(img.shape[:2]) > ART_MAX_SIDE:
            tmp = f.with_suffix(".tmp")
            _save_small(f.read_bytes(), tmp)
            tmp.replace(f)
            shrunk += 1
        if k % 2000 == 0:
            print(f"  {k}/{len(files)}")
    after = sum(f.stat().st_size for f in files)
    print(f"{shrunk} Bilder verkleinert: {before / 1e9:.2f} GB -> {after / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
