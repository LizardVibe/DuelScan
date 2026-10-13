"""Karte im Kamerabild finden, entzerren und Artwork-Fingerabdruck berechnen."""
import cv2
import numpy as np

from .config import ART_BOX, ART_MARGIN, CARD_H, CARD_W

CARD_RATIO = CARD_H / CARD_W  # ~1.46


def order_points(pts: np.ndarray) -> np.ndarray:
    """Sortiert 4 Punkte: oben-links, oben-rechts, unten-rechts, unten-links."""
    pts = pts.astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    dtype=np.float32)


def find_card(frame: np.ndarray) -> np.ndarray | None:
    """Sucht das größte kartenförmige Viereck. Gibt 4 Eckpunkte zurück oder None."""
    h, w = frame.shape[:2]
    scale = 800 / max(h, w) if max(h, w) > 800 else 1.0
    small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    min_area = 0.03 * small.shape[0] * small.shape[1]

    # Alle kartenförmigen Vierecke sammeln (auch verschachtelte: Karte liegt z.B. auf Papier oder Dose)
    quads: list[tuple[float, np.ndarray]] = []
    for lo, hi in ((40, 120), (20, 60), (80, 200)):
        edges = cv2.dilate(cv2.Canny(gray, lo, hi), np.ones((3, 3), np.uint8), iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:25]:
            area = cv2.contourArea(c)
            if area < min_area:
                break
            q = _card_quad(c)
            if q is not None:
                quads.append((area, q))
        if quads:
            break
    if not quads:
        return None

    # Größtes Viereck nehmen, das KEIN anderes deutlich kleineres kartenförmiges Viereck enthält
    # (sonst ist es ein Papierblatt/Untergrund mit der Karte darauf).
    quads.sort(key=lambda t: t[0], reverse=True)
    for area, q in quads:
        center_inside = [a for a, q2 in quads
                         if 0.08 * area < a < 0.8 * area
                         and cv2.pointPolygonTest(q.reshape(-1, 1, 2), tuple(map(float, q2.mean(0))), False) > 0]
        if not center_inside:
            return q / scale
    return quads[-1][1] / scale


def _card_quad(contour) -> np.ndarray | None:
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    if len(approx) != 4 or not cv2.isContourConvex(approx):
        # Fallback: kleinstes umschließendes Rechteck (z.B. abgerundete/verdeckte Ecken)
        rect = cv2.minAreaRect(contour)
        if cv2.contourArea(contour) / max(rect[1][0] * rect[1][1], 1) < 0.85:
            return None
        approx = cv2.boxPoints(rect)
    quad = order_points(np.asarray(approx).reshape(4, 2))
    top = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
    side = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
    ratio = max(top, side) / max(min(top, side), 1)
    # Etwas Spielraum, weil eine schräge Kamera das Seitenverhältnis verzerrt
    return quad if 1.22 < ratio < 1.72 else None


def warp_card(frame: np.ndarray, quad: np.ndarray) -> np.ndarray:
    """Entzerrt die Karte auf CARD_W x CARD_H (hochkant)."""
    tl, tr, br, bl = quad
    if np.linalg.norm(tr - tl) > np.linalg.norm(bl - tl):
        # Karte liegt quer -> Ecken so drehen, dass sie hochkant wird
        quad = np.array([bl, tl, tr, br], dtype=np.float32)
    dst = np.array([[0, 0], [CARD_W - 1, 0], [CARD_W - 1, CARD_H - 1], [0, CARD_H - 1]], dtype=np.float32)
    m = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    return cv2.warpPerspective(frame, m, (CARD_W, CARD_H))


def crop_margin(img: np.ndarray, margin: float = ART_MARGIN) -> np.ndarray:
    h, w = img.shape[:2]
    my, mx = int(h * margin), int(w * margin)
    return img[my:h - my, mx:w - mx]


def card_artwork(card: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = ART_BOX
    return crop_margin(card[y1:y2, x1:x2])


def reference_artwork(cropped: np.ndarray) -> np.ndarray:
    """Artwork aus einem YGOPRODeck-'cropped'-Bild. Pendel-Artworks sind breiter als hoch:
    dann nehmen wir den oberen quadratischen Teil, der dem sichtbaren Bereich ähnelt."""
    h, w = cropped.shape[:2]
    if w > h * 1.1:
        cx = w // 2
        cropped = cropped[:, max(0, cx - h // 2): cx + h // 2]
    return crop_margin(cropped)


def phash(img: np.ndarray) -> np.ndarray:
    """256-Bit Perceptual Hash (DCT), als 32 Bytes."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.resize(g, (64, 64), interpolation=cv2.INTER_AREA)
    g = cv2.equalizeHist(g)
    d = cv2.dct(np.float32(g))[:16, :16].flatten()
    bits = d > np.median(d[1:])
    return np.packbits(bits)
