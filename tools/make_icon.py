"""Erzeugt das App-Icon (ygo_scanner/assets/icon.png und icon.ico) – ohne zusätzliche Pakete."""
import struct
import sys
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "ygo_scanner" / "assets"


def draw(size: int) -> np.ndarray:
    s = size / 256
    img = np.zeros((size, size, 4), np.uint8)
    # Hintergrund: abgerundetes Quadrat, Indigo
    bg = np.zeros((size, size), np.uint8)
    r = int(48 * s)
    cv2.rectangle(bg, (r, 0), (size - r, size), 255, -1)
    cv2.rectangle(bg, (0, r), (size, size - r), 255, -1)
    for cx, cy in ((r, r), (size - r, r), (r, size - r), (size - r, size - r)):
        cv2.circle(bg, (cx, cy), r, 255, -1, cv2.LINE_AA)
    img[..., :3] = (219, 91, 59)       # BGR von #3b5bdb
    img[..., 3] = bg
    # Karte (hochkant, leicht gedreht) in Gold
    card = np.array([[-52, -76], [52, -76], [52, 76], [-52, 76]], np.float32) * s
    ang = np.deg2rad(-10)
    rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    pts = (card @ rot.T + [size * 0.44, size * 0.48]).astype(np.int32)
    cv2.fillConvexPoly(img, pts, (66, 197, 245, 255), cv2.LINE_AA)
    inner = (card * 0.72 @ rot.T + [size * 0.44, size * 0.44]).astype(np.int32)
    cv2.fillConvexPoly(img, inner, (40, 30, 30, 255), cv2.LINE_AA)
    # Lupe
    c = (int(size * 0.66), int(size * 0.66))
    cv2.circle(img, c, int(40 * s), (255, 255, 255, 255), max(2, int(14 * s)), cv2.LINE_AA)
    end = (int(c[0] + 52 * s), int(c[1] + 52 * s))
    start = (int(c[0] + 30 * s), int(c[1] + 30 * s))
    cv2.line(img, start, end, (255, 255, 255, 255), max(2, int(20 * s)), cv2.LINE_AA)
    return img


def write_ico(path: Path, sizes=(256, 64, 48, 32, 16)) -> None:
    pngs = [cv2.imencode(".png", draw(sz))[1].tobytes() for sz in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for sz, data in zip(sizes, pngs):
        entries += struct.pack("<BBBBHHII", sz % 256, sz % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(pngs))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "icon.png"), draw(256))
    write_ico(OUT / "icon.ico")
    print("Icon gespeichert:", OUT)
    sys.exit(0)
