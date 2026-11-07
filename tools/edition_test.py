"""Edition-Erkennung an den Testfotos prüfen - auch künstlich verschlechtert (Richtung Webcam-Qualität)."""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ygo_scanner import edition  # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "testbilder" / "_probe"
TRUTH = {"newgen-holo-goldrare": "1st", "Newgen-Holo": "1st", "newgen-limited": "limited",
         "oldgen-superrare-firsted": "1st", "oldgen-ultirare-sleeved": "limited", "oldgen-unlimited": "unlimited"}
for sigma in (0, 0.8, 1.2, 1.6, 2.0, 2.5):
    ok = total = 0
    lines = []
    for f in sorted(SRC.glob("*_warp.png")):
        name = f.name.replace("_warp.png", "")
        w = cv2.imread(str(f))
        if sigma:
            w = cv2.GaussianBlur(w, (0, 0), sigma)
        sharp = cv2.Laplacian(cv2.cvtColor(w, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        r = edition.detect(w)
        if r is None:
            lines.append(f"   {name:26s} Schaerfe {sharp:5.0f}  -> zu unscharf, keine Schaetzung")
            continue
        fill = r.pop("_debug")
        guess = max(r, key=r.get)
        total += 1
        ok += guess == TRUTH[name]
        lines.append(f"   {name:26s} Schaerfe {sharp:5.0f}  -> {guess:9s} (richtig: {TRUTH[name]:9s}) fill={fill}"
                     + ("" if guess == TRUTH[name] else "   <-- FALSCH"))
    print(f"Unschaerfe {sigma}: {ok}/{total} richtig geschaetzt")
    print("\n".join(lines))
