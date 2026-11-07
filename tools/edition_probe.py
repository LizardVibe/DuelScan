"""Hilfsskript: Testfotos entzerren, erkennen und die Bereiche für Edition/Set-Code ausschneiden."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ygo_scanner.matcher import Matcher  # noqa: E402
from ygo_scanner.vision import find_card, warp_card  # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "testbilder"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC / "_probe"
OUT.mkdir(parents=True, exist_ok=True)
m = Matcher()
rows = []
for f in sorted(SRC.glob("*.jp*g")):
    img = cv2.imread(str(f))
    q = find_card(img)
    if q is None:
        print(f"{f.name:34s} KEINE KARTE GEFUNDEN")
        continue
    w = warp_card(img, q)
    c = m.match(w)[0]
    sharp = cv2.Laplacian(cv2.cvtColor(w, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    print(f"{f.name:34s} -> {c.name[:34]:34s} {c.confidence:4.0%}  Schaerfe {sharp:5.0f}")
    cv2.imwrite(str(OUT / f"{f.stem}_warp.png"), w)
    rows.append(cv2.resize(w[420:480, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))   # unter dem Artwork
    rows.append(cv2.resize(w[585:614, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))   # unterer Rand
    rows.append(np.full((6, 842, 3), 255, np.uint8))
cv2.imwrite(str(OUT / "strips.png"), np.vstack(rows))
