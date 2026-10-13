"""Vergleicht ein entzerrtes Kartenbild mit dem Artwork-Index.

Zwei Erkenner, die sich ergänzen:
  - pHash (Bild-Fingerabdruck): robust gegen Unschärfe, Dunkelheit, Farbstich
  - KI (DINOv2-Merkmale):       stark bei guten Bildern, Spiegelungen, leichter Verschiebung
Standard ist die Kombination ("combo"): beide Ergebnisse werden normalisiert und addiert.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from .config import COMBO_EMBED_WEIGHT, COMBO_MIN_SCORE, COMBO_TEMPERATURE, EMBED_FILE, INDEX_FILE
from .database import load_cards
from .vision import card_artwork, phash


@dataclass(eq=False)
class Candidate:
    card: dict
    image_id: int
    score: float          # kombinierter Wert (größer = besser)
    confidence: float
    rarity: str | None = None     # vom Nutzer gewählte Seltenheit
    rarity_price: float = 0.0     # Preis dieser Seltenheit (TCGplayer, USD; 0 = unbekannt)
    rarity_url: str | None = None # TCGplayer-Seite des günstigsten Drucks dieser Seltenheit
    condition: str = "near_mint"  # Zustand für Live-Preise

    @property
    def name(self) -> str:
        return self.card["name"]

    @property
    def prices(self) -> dict:
        p = self.card.get("card_prices") or [{}]
        return p[0]


def _z(x: np.ndarray) -> np.ndarray:
    return (x - x.mean()) / (x.std() + 1e-9)


class Matcher:
    def __init__(self, mode: str | None = None):
        self.card_by_image = {img["id"]: c for c in load_cards() for img in c.get("card_images", [])}
        hidx = np.load(INDEX_FILE)
        self.ids, self.hashes = hidx["ids"], hidx["hashes"]
        self.mode = mode or ("combo" if EMBED_FILE.exists() else "phash")
        if self.mode != "phash":
            eidx = np.load(EMBED_FILE)
            # KI-Merkmale in die Reihenfolge des pHash-Index bringen
            pos = {int(i): k for k, i in enumerate(eidx["ids"])}
            keep = np.array([int(i) in pos for i in self.ids])
            self.ids, self.hashes = self.ids[keep], self.hashes[keep]
            self.feats = eidx["feats"][[pos[int(i)] for i in self.ids]].astype(np.float32)
            from .embed import model
            model()  # schon beim Start laden, damit der erste Scan nicht hängt

    def scores(self, card_img: np.ndarray) -> np.ndarray:
        """Bewertung aller Artworks (größer = besser), beide Ausrichtungen der Karte geprüft."""
        arts = [card_artwork(card_img), card_artwork(cv2.rotate(card_img, cv2.ROTATE_180))]
        per_rotation = []
        for a in arts:
            dist = np.unpackbits(np.bitwise_xor(self.hashes, phash(a)), axis=1).sum(axis=1).astype(np.float32)
            s = _z(-dist)
            if self.mode != "phash":
                from .embed import embed
                sim = self.feats @ embed([a])[0]
                w = 1.0 if self.mode == "embed" else COMBO_EMBED_WEIGHT
                s = (1 - w) * s + w * _z(sim)
            per_rotation.append(s)
        return np.maximum(*per_rotation)

    def match(self, card_img: np.ndarray, top_k: int = 3) -> list[Candidate]:
        s = self.scores(card_img)
        # Pro Karte nur das beste Artwork behalten (Alternativ-Artworks gehören zur selben Karte)
        picked, seen = [], set()
        for i in np.argsort(-s)[:200]:
            card = self.card_by_image[int(self.ids[i])]
            if card["id"] in seen:
                continue
            seen.add(card["id"])
            picked.append((card, int(self.ids[i]), float(s[i])))
            if len(picked) == 10:
                break
        sc = np.array([p[2] for p in picked])
        w = np.exp((sc - sc.max()) / COMBO_TEMPERATURE)
        conf = w / w.sum()
        if sc.max() < COMBO_MIN_SCORE:  # selbst der beste Treffer hebt sich kaum ab
            conf *= 0.3
        return [Candidate(c, i, v, float(p)) for (c, i, v), p in zip(picked[:top_k], conf[:top_k])]
