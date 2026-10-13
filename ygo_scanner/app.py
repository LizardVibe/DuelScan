"""Einzelnes Foto erkennen (Test ohne Kamera). Die eigentliche Oberfläche ist gui.py."""
import sys

import cv2
import numpy as np

from .matcher import Matcher
from .vision import find_card, warp_card


def scan_image(path: str) -> None:
    img = cv2.imread(path)
    if img is None:
        sys.exit(f"Bild nicht lesbar: {path}")
    quad = find_card(img)
    if quad is None:
        print("Keine Karte gefunden - nehme das ganze Bild als Karte.")
        h, w = img.shape[:2]
        quad = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    cands = Matcher().match(warp_card(img, quad))
    for i, c in enumerate(cands, 1):
        print(f"[{i}] {c.confidence:5.0%}  (Score {c.score:6.3f})  {c.name}   "
              f"CM ab {c.prices.get('cardmarket_price')} EUR / TCG ab {c.prices.get('tcgplayer_price')} $")
