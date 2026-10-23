"""Seltenheit vorschlagen - ohne Spezial-Licht, nur aus einem normalen Kamerabild.

Idee: Die Farbe des Kartennamens verrät viel über die Seltenheit:
    normal (schwarz/weiß)  -> Common, Short Print, Super Rare (Super Rare: nur das Bild glänzt)
    silber                 -> Rare, Platinum Rare
    gold                   -> Ultra Rare, Ultimate Rare, Gold Rare ...
    silber-regenbogen      -> Secret Rare und Verwandte, Starlight, Collector's, Ghost

Kombiniert mit dem Wissen, in welchen Seltenheiten es die Karte überhaupt gibt (und wie oft),
ergibt das eine Wahrscheinlichkeit pro Seltenheit. Gibt es die Karte nur in einer Seltenheit,
ist die Sache ohnehin klar (bei ca. der Hälfte aller Karten).
"""
import datetime as dt

import cv2
import numpy as np

from .config import DATA_DIR

SAMPLES_DIR = DATA_DIR / "rarity_samples"
CLASSES = ("plain", "silver", "gold", "rainbow")

# Position auf der entzerrten Karte (421 x 614 px)
NAME_BOX = (25, 18, 340, 46)       # x1, y1, x2, y2 - ohne Attribut-Symbol rechts
FRAME_STRIP = (25, 49, 150, 57)    # Rahmen direkt unter dem Namen (links, wo keine Sterne sind)

# Rahmen mit weißer Standard-Schrift (sonst schwarz)
WHITE_TEXT_FRAMES = {"xyz", "link", "spell", "trap", "skill", "xyz_pendulum"}


def rarity_class(rarity: str) -> str:
    r = rarity.lower()
    if any(k in r for k in ("secret", "starlight", "collector", "ghost", "prismatic", "quarter century",
                            "pharaoh")):
        return "rainbow"
    if any(k in r for k in ("ultra", "ultimate", "gold")):
        return "gold"
    if "platinum" in r or r.startswith("rare") or r == "rare" or "duel terminal rare" in r:
        return "silver"
    return "plain"     # Common, Short Print, Super Rare, Parallel, ...


def name_crop(card_img: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = NAME_BOX
    return card_img[y1:y2, x1:x2]


def name_features(card_img: np.ndarray) -> dict | None:
    """Farbe der Schrift im Namensfeld: Pixel, die sich deutlich vom Rahmen unterscheiden."""
    crop = name_crop(card_img)
    fx1, fy1, fx2, fy2 = FRAME_STRIP
    strip = card_img[fy1:fy2, fx1:fx2]
    if crop.size == 0 or strip.size == 0:
        return None
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    bg = np.median(cv2.cvtColor(strip, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32), axis=0)
    dist = np.linalg.norm(lab - bg, axis=1)
    thr = max(18.0, float(np.quantile(dist, 0.70)))
    text = dist > thr
    if text.sum() < 40:            # kaum Schrift gefunden (z.B. Name verdeckt/abgeschnitten)
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)[text]
    h = hsv[:, 0] * (2 * np.pi / 180)
    hue = (np.degrees(np.arctan2(np.sin(h).mean(), np.cos(h).mean())) / 2) % 180
    hue_spread = 1 - np.hypot(np.sin(h).mean(), np.cos(h).mean())   # 0 = einheitlich, 1 = alle Farben
    bg_hsv = np.median(cv2.cvtColor(strip, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32), axis=0)
    return {"hue": float(hue), "hue_spread": float(hue_spread), "sat": float(np.median(hsv[:, 1])),
            "val": float(np.median(hsv[:, 2])), "bg_val": float(bg_hsv[2]), "bg_sat": float(bg_hsv[1])}


def class_probs(feat: dict | None, frame_type: str) -> dict[str, float]:
    """Wahrscheinlichkeit für jede Namensfarbe. Bewusst vorsichtig: lieber unentschieden als falsch."""
    if feat is None:
        return {c: 1 / len(CLASSES) for c in CLASSES}
    hue, sat, val, spread = feat["hue"], feat["sat"], feat["val"], feat["hue_spread"]
    # Relativ zum Rahmen bewerten - Webcam-Bilder sind oft dunkel, absolute Helligkeiten täuschen
    contrast = val - feat["bg_val"]            # > 0: Schrift heller als der Rahmen
    white_frame = frame_type in WHITE_TEXT_FRAMES
    score = dict.fromkeys(CLASSES, 0.0)
    metallic = _ramp(contrast, 10, 45) if not white_frame else _ramp(val, 70, 120)
    # Gold: gelblicher Farbton (OpenCV-Hue ~8-38) und sichtbar gesättigt
    score["gold"] = 2.5 * metallic * _band(hue, 8, 38, 6) * _ramp(sat, 35, 80)
    # Regenbogen: viele verschiedene Farbtöne (Secret-Rare-Schimmer)
    score["rainbow"] = 2.0 * metallic * _ramp(spread, 0.25, 0.55) * _ramp(sat, 25, 60)
    grey = 1 - _ramp(sat, 35, 75)
    if white_frame:
        # Weiße Standardschrift vs. Silber ist auf einer Webcam kaum zu trennen -> beide gleich möglich
        score["plain"] = score["silver"] = 1.2 * grey * metallic
    else:
        score["plain"] = 2.0 * (1 - _ramp(contrast, -15, 15))     # schwarze Schrift: dunkler als der Rahmen
        score["silver"] = 2.0 * grey * metallic                    # helle, graue Schrift
    w = {c: np.exp(v * 2) for c, v in score.items()}
    tot = sum(w.values())
    return {c: v / tot for c, v in w.items()}


def suggest(options: list[dict], printings: list[dict], probs: dict[str, float]) -> dict[str, float]:
    """Wahrscheinlichkeit pro angebotener Seltenheit = Namensfarbe x Häufigkeit (Anzahl Drucke)."""
    if not options:
        return {}
    if len(options) == 1:
        return {options[0]["rarity"]: 1.0}
    counts: dict[str, int] = {}
    for p in printings:
        counts[p.get("rarity") or "?"] = counts.get(p.get("rarity") or "?", 0) + 1
    raw = {}
    for o in options:
        r = o["rarity"]
        raw[r] = probs[rarity_class(r)] * (counts.get(r, 0) + 1)
    tot = sum(raw.values()) or 1.0
    return {r: v / tot for r, v in raw.items()}


def save_sample(card_img: np.ndarray, rarity: str, frame_type: str) -> None:
    """Vom Nutzer bestätigte Seltenheit + Namensfeld speichern, um die Erkennung später nachzujustieren."""
    try:
        cls = rarity_class(rarity)
        d = SAMPLES_DIR / cls
        d.mkdir(parents=True, exist_ok=True)
        stem = f"{dt.datetime.now():%Y%m%d_%H%M%S}_{frame_type}_{rarity.replace(' ', '-').replace('/', '-')}"
        cv2.imwrite(str(d / f"{stem}.png"), card_img[:70, :])
    except Exception:  # noqa: BLE001 - nur Hilfsdaten, darf nie stören
        pass


def _ramp(x: float, lo: float, hi: float) -> float:
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def _band(x: float, lo: float, hi: float, soft: float) -> float:
    return _ramp(x, lo - soft, lo) * (1 - _ramp(x, hi, hi + soft))
