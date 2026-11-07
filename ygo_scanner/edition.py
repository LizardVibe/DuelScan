"""EXPERIMENTELL, NOCH NICHT AKTIV: 1st Edition / Limited Edition / Unlimited aus dem Kamerabild schätzen.

Stand: Auf 6 scharfen Handyfotos nur 3/6 richtig (Zeile wird nicht zuverlässig gefunden), und ab einer
Karten-Schärfe unter ca. 200 unbrauchbar - typische Webcams liegen deutlich darunter. Deshalb nirgends
eingebunden; Edition/Druck wählt der Nutzer über die "Druck"-Liste. Testwerkzeuge: tools/edition_probe.py,
tools/edition_test.py (Fotos in testbilder/, nicht im Repository).


Wo der Aufdruck steht:
  - ältere Karten: links in der schmalen Zeile zwischen Artwork und Textbox
    ("1. Auflage", "LIMITIERTE AUFLAGE", "1st Edition", "LIMITED EDITION" ...)
  - neuere Karten: in der untersten Zeile, rechts neben der 8-stelligen Kartennummer
  - Unlimited: an beiden Stellen steht nichts

Wir lesen den Text nicht, sondern prüfen nur, ob dort Schrift ist und wie lang sie ist:
"1. Auflage"/"1st Edition" ist kurz, "LIMITIERTE AUFLAGE"/"LIMITED EDITION" deutlich länger.
Die Zeilen werden an der Karte selbst ausgerichtet (Unterkante Artwork, Ränder der Textbox), weil
das Entzerren nie pixelgenau ist (Hüllen, schräge Kamera).
Ist das Bild zu unscharf, gibt es bewusst KEINE Schätzung (None) - lieber nichts als Unsinn.
"""
import cv2
import numpy as np

MIN_SHARPNESS = 120          # Laplace-Varianz der entzerrten Karte, darunter keine Schätzung
OLD_X = (0.07, 0.55)         # Bereich links unter dem Artwork (rechts davon steht der Set-Code)
NEW_X = (0.17, 0.48)         # unterste Zeile: nach der Kartennummer, vor dem Copyright


LINE_H = 12                  # Höhe einer Schriftzeile in der entzerrten Karte (px)
SETCODE_X = (0.66, 0.95)     # Set-Code rechts unter dem Artwork - steht auf JEDER Karte
PASSCODE_X = (0.02, 0.16)    # 8-stellige Kartennummer unten links - steht auf JEDER Karte


def _find_line(gray: np.ndarray, y_lo: int, y_hi: int, xr: tuple[float, float]) -> int:
    """y-Position der deutlichsten Schriftzeile im Bereich (über senkrechte Kanten gemessen)."""
    h, w = gray.shape
    sx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))[:, int(xr[0] * w):int(xr[1] * w)]
    best_y, best = y_lo, -1.0
    for y in range(max(0, y_lo), min(h - LINE_H, y_hi) + 1):
        col = sx[y:y + LINE_H].max(axis=0)
        score = float(np.sort(col)[int(0.7 * len(col)):].mean())
        if score > best:
            best_y, best = y, score
    return best_y


def _art_bottom(gray: np.ndarray) -> int:
    """Unterkante des Artwork-Rahmens: stärkste waagerechte Kante unter dem Artwork (enges Suchfenster)."""
    h, w = gray.shape
    sy = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))[:, int(0.15 * w):int(0.85 * w)]
    # Eine durchgehende Linie ist über die ganze Breite stark (Median), Textzeilen nur stellenweise
    prof = np.median(sy, axis=1)
    lo, hi = 415, 465
    return lo + int(np.argmax(prof[lo:hi]))


def _bands(gray: np.ndarray) -> tuple[tuple[int, int], tuple[int, int]]:
    """Zeilenbereiche (y1, y2): alte Generation direkt unter dem Artwork, neue Generation in der untersten Zeile
    (gefunden über die Kartennummer, die dort immer steht)."""
    ab = _art_bottom(gray)
    y_old = _find_line(gray, ab + 1, ab + 8, SETCODE_X)
    y_new = _find_line(gray, 578, 614, PASSCODE_X)
    return (y_old, y_old + LINE_H), (y_new, y_new + LINE_H)


def _text_extent(gray: np.ndarray, band: tuple[int, int], xr: tuple[float, float]) -> float:
    """Länge der Schrift im Bereich (Anteil der Bereichsbreite, 0 = keine Schrift).
    Gemessen über senkrechte Kanten - Buchstaben haben viele, Rahmenlinien keine."""
    h, w = gray.shape
    x1, x2 = int(xr[0] * w), int(xr[1] * w)
    y1, y2 = band
    if y2 - y1 < 3:
        return 0.0
    sx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))[y1:y2, x1:x2]
    col = np.quantile(sx, 0.8, axis=0)
    base = float(np.median(col))
    ink = col > max(25.0, 3.0 * base)
    if ink.sum() < 6:
        return 0.0
    # Lücken zwischen Buchstaben/Wörtern schließen und den längsten zusammenhängenden Abschnitt nehmen
    ink = np.convolve(ink.astype(np.float32), np.ones(9), "same") > 0
    best = run = 0
    for v in ink:
        run = run + 1 if v else 0
        best = max(best, run)
    return best / (x2 - x1)


def detect(card_img: np.ndarray) -> dict | None:
    """Wahrscheinlichkeiten {"1st": p, "limited": p, "unlimited": p} oder None, wenn das Bild zu unscharf ist."""
    gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if cv2.Laplacian(gray, cv2.CV_32F).var() < MIN_SHARPNESS:
        return None
    old_band, new_band = _bands(gray)
    old = _text_extent(gray, old_band, OLD_X)
    new = _text_extent(gray, new_band, NEW_X)
    if max(old, new) < 0.12:
        probs = {"unlimited": 0.85, "1st": 0.1, "limited": 0.05}
    else:
        # kurze Schrift = 1st, lange = Limited (Grenzen aus Testfotos, DE)
        length, limit = (old, 0.5) if old >= new else (new, 0.75)
        probs = ({"limited": 0.8, "1st": 0.15, "unlimited": 0.05} if length >= limit
                 else {"1st": 0.8, "limited": 0.15, "unlimited": 0.05})
    probs["_debug"] = {"old": round(old, 2), "new": round(new, 2), "bands": (old_band, new_band)}
    return probs
