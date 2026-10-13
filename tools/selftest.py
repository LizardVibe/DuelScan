"""Selbsttest ohne Kamera: echte Kartenbilder werden zu "Handyfotos" verfremdet
(schief, gedreht, Hintergrund, Licht, Unschärfe, Rauschen, Spiegelung) und dann erkannt.

  python tools/selftest.py [Anzahl]
"""
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ygo_scanner.config import DATA_DIR  # noqa: E402
from ygo_scanner.matcher import Matcher  # noqa: E402
from ygo_scanner.vision import find_card, warp_card  # noqa: E402

CACHE = DATA_DIR / "selftest_full"
MODE = next((a[2:] for a in sys.argv if a in ("--phash", "--embed", "--combo")), None)
sys.argv = [a for a in sys.argv if a not in ("--phash", "--embed", "--combo")]
HARD = "--hard" in sys.argv
if HARD:
    sys.argv.remove("--hard")


def fake_photo(card: np.ndarray, rng: random.Random) -> np.ndarray:
    H, W = 720, 1280
    bg = np.full((H, W, 3), [rng.randint(20, 120)] * 3, np.uint8)
    bg = cv2.add(bg, np.random.randint(0, 25, bg.shape, np.uint8))
    ch, cw = card.shape[:2]
    hard = HARD
    scale = (rng.uniform(0.4, 0.55) if hard else rng.uniform(0.75, 0.95)) * H / ch
    cx, cy = W / 2 + rng.uniform(-200, 200), H / 2 + rng.uniform(-20, 20)
    ang = np.deg2rad(rng.uniform(-15, 15) + (180 if rng.random() < 0.2 else 0))
    hw, hh = cw * scale / 2, ch * scale / 2
    corners = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
    rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    dst = corners @ rot.T + [cx, cy] + np.random.uniform(-25, 25, (4, 2))  # Perspektive
    m = cv2.getPerspectiveTransform(np.float32([[0, 0], [cw, 0], [cw, ch], [0, ch]]), np.float32(dst))
    warped = cv2.warpPerspective(card, m, (W, H))
    mask = cv2.warpPerspective(np.full((ch, cw), 255, np.uint8), m, (W, H))
    img = np.where(mask[..., None] > 0, warped, bg)

    img = cv2.convertScaleAbs(img, alpha=rng.uniform(0.7, 1.25), beta=rng.uniform(-30, 30))
    if rng.random() < 0.5:  # Lichtreflex
        glare = np.zeros((H, W), np.float32)
        cv2.circle(glare, (int(cx + rng.uniform(-150, 150)), int(cy + rng.uniform(-200, 200))),
                   rng.randint(40, 120), 1.0, -1)
        glare = cv2.GaussianBlur(glare, (0, 0), 40) * rng.uniform(80, 160)
        img = np.clip(img + glare[..., None], 0, 255).astype(np.uint8)
    if hard:  # realistischere Webcam: dunkler, kontrastarm, Farbstich, unscharf
        img = cv2.convertScaleAbs(img, alpha=rng.uniform(0.45, 0.8), beta=rng.uniform(-10, 15))
        cast = np.array([rng.uniform(0.85, 1.15), rng.uniform(0.85, 1.05), rng.uniform(0.85, 1.2)])
        img = np.clip(img * cast, 0, 255).astype(np.uint8)
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(1.5, 3.0))
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.3, 1.5))
    img = np.clip(img + np.random.normal(0, rng.uniform(2, 8), img.shape), 0, 255).astype(np.uint8)
    return img


def main(n: int = 60) -> None:
    rng = random.Random(42)
    np.random.seed(42)
    m = Matcher(MODE)
    CACHE.mkdir(parents=True, exist_ok=True)
    pool = [c for c in m.card_by_image.values() if c["type"] not in ("Skill Card", "Token")]
    cards = rng.sample(pool, n)
    top1 = top3 = found = auto = auto_wrong = 0
    failures = []
    for c in cards:
        img_info = c["card_images"][0]
        p = CACHE / f"{img_info['id']}.jpg"
        if not p.exists():
            p.write_bytes(requests.get(img_info["image_url"], timeout=30).content)
        full = cv2.imread(str(p))
        photo = fake_photo(full, rng)
        quad = find_card(photo)
        if quad is None:
            failures.append((c["name"], "Karte nicht gefunden"))
            continue
        found += 1
        cands = m.match(warp_card(photo, quad))
        ids = [x.card["id"] for x in cands]
        top1 += ids[0] == c["id"]
        top3 += c["id"] in ids
        if cands[0].confidence >= 0.9:
            auto += 1
            auto_wrong += ids[0] != c["id"]
        if ids[0] != c["id"]:
            failures.append((c["name"], f"erkannt als {cands[0].name} ({cands[0].confidence:.0%}, score={cands[0].score:.3f})"))

    print(f"Karten: {n} | Karte gefunden: {found} | Top-1 richtig: {top1} | in Top-3: {top3}")
    print(f"Automatisch übernommen (>=90%): {auto}, davon falsch: {auto_wrong}")
    for name, why in failures:
        print(f"  x {name}: {why}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
