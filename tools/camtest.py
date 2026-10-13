"""Kamera testen: probiert Auflösungen/Formate und speichert Testbilder nach scans/camtest_*.jpg"""
import sys
from pathlib import Path
import cv2

out = Path(__file__).resolve().parent.parent / "scans"
out.mkdir(exist_ok=True)
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for backend, bname in [(cv2.CAP_DSHOW, "dshow"), (cv2.CAP_MSMF, "msmf")]:
    for w, h in [(2560, 1440), (1920, 1080)]:
        cap = cv2.VideoCapture(idx, backend)
        if not cap.isOpened():
            print(bname, "nicht offen"); break
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        for _ in range(25): ok, f = cap.read()   # Belichtung/Fokus einschwingen lassen
        if ok:
            sharp = cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            p = out / f"camtest_{bname}_{f.shape[1]}x{f.shape[0]}.jpg"
            cv2.imwrite(str(p), f)
            print(f"{bname} angefragt {w}x{h} -> bekommen {f.shape[1]}x{f.shape[0]}, Schaerfe {sharp:.0f}, {p.name}")
        cap.release()
