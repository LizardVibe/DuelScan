"""Vergleicht ein entzerrtes Kartenbild mit dem Artwork-Index.

Zwei Erkenner, die sich ergänzen:
  - pHash (Bild-Fingerabdruck): robust gegen Unschärfe, Dunkelheit, Farbstich
  - KI (DINOv2-Merkmale):       stark bei guten Bildern, Spiegelungen, leichter Verschiebung
Standard ist die Kombination ("combo"): beide Ergebnisse werden normalisiert und addiert.

Dazu kommen "gelernte" Vergleichsbilder: Wenn der Nutzer eine unsichere Karte bestätigt oder
korrigiert, wird das Artwork aus SEINER Kamera als zusätzliche Referenz gespeichert. Beim nächsten
Scan derselben Karte (gleiche Kamera, gleiches Licht) ist der Treffer dann deutlich sicherer.
"""
import threading
import time
import uuid
from dataclasses import dataclass

import cv2
import numpy as np

from .config import (COMBO_EMBED_WEIGHT, COMBO_MIN_SCORE, COMBO_TEMPERATURE, DATA_DIR, EMBED_FILE, INDEX_FILE)
from .database import load_cards
from .vision import card_artwork, phash

LEARNED_DIR = DATA_DIR / "learned"
LEARNED_FILE = LEARNED_DIR / "learned.npz"
MAX_LEARNED_PER_IMAGE = 3
# Gelernte Bilder zählen nur, wenn sie dem Scan sehr ähnlich sind. Gemessen: zwei Fotos derselben Karte
# ~0,85 (KI-Ähnlichkeit), verschiedene Karten höchstens ~0,77 -> sonst "ziehen" unscharfe gelernte Bilder
# andere unscharfe Scans an.
LEARNED_MIN_SIM = 0.80
LEARNED_MAX_HASH_DIST = 60      # dasselbe für den pHash-Modus (ohne KI), von 256 Bit


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
    rarity_guess: dict | None = None  # automatischer Seltenheits-Vorschlag {Seltenheit: Wahrscheinlichkeit}
    rarity_class_probs: dict | None = None  # Namensfarbe aus dem Kamerabild (plain/silver/gold/rainbow)
    rarity_auto: bool = False     # Seltenheit stammt aus dem Vorschlag (noch nicht bestätigt)
    rarity_user: bool = False     # Nutzer hat die Seltenheit selbst gewählt
    printing: str | None = None   # gewählter Druck, z.B. "DCR-000 Unlimited" (None = günstigster)

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
        self.feats = None
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
        self._lock = threading.Lock()
        self._load_learned()

    # ---------------------------------------------------------------- gelernte Referenzen
    def _load_learned(self) -> None:
        self.l_keys: list[str] = []
        self.l_ids = np.zeros(0, np.int64)
        self.l_hashes = np.zeros((0, self.hashes.shape[1]), np.uint8)
        self.l_feats = np.zeros((0, self.feats.shape[1] if self.feats is not None else 0), np.float32)
        if not LEARNED_FILE.exists():
            return
        try:
            d = np.load(LEARNED_FILE, allow_pickle=False)
            known = np.array([int(i) in self.card_by_image for i in d["ids"]], bool)
            self.l_keys = [k for k, ok in zip(d["keys"].tolist(), known) if ok]
            self.l_ids, self.l_hashes = d["ids"][known], d["hashes"][known]
            if self.feats is not None and d["feats"].shape[1] == self.feats.shape[1]:
                self.l_feats = d["feats"][known].astype(np.float32)
            elif self.feats is not None:     # KI-Merkmale fehlen -> aus den gespeicherten Bildern neu berechnen
                self.l_feats = self._embed_files(self.l_keys)
        except (OSError, ValueError, KeyError):
            self.l_keys = []

    def _embed_files(self, keys: list[str]) -> np.ndarray:
        from .embed import embed
        imgs = [cv2.imread(str(LEARNED_DIR / f"{k}.jpg")) for k in keys]
        return embed(imgs) if imgs else np.zeros((0, self.feats.shape[1]), np.float32)

    def _save_learned(self) -> None:
        LEARNED_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(LEARNED_FILE, keys=np.array(self.l_keys, dtype="U40"), ids=self.l_ids,
                            hashes=self.l_hashes, feats=self.l_feats)

    @property
    def learned_count(self) -> int:
        return len(self.l_keys)

    def learn(self, image_id: int, card_img: np.ndarray) -> str | None:
        """Artwork aus dem Kamerabild als zusätzliche Referenz für image_id speichern. Gibt einen Schlüssel
        zurück, mit dem sich der Eintrag wieder entfernen lässt (z.B. wenn der Nutzer nochmal korrigiert)."""
        base = np.flatnonzero(self.ids == image_id)
        upright, flipped = card_artwork(card_img), card_artwork(cv2.rotate(card_img, cv2.ROTATE_180))
        art = upright
        if len(base):   # die Ausrichtung nehmen, die besser zum Original-Artwork passt
            ref = self.hashes[base[0]]
            d_up = np.unpackbits(np.bitwise_xor(ref, phash(upright))).sum()
            d_fl = np.unpackbits(np.bitwise_xor(ref, phash(flipped))).sum()
            art = upright if d_up <= d_fl else flipped
        key = f"{image_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        LEARNED_DIR.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(LEARNED_DIR / f"{key}.jpg"), art)
        feat = None
        if self.feats is not None:
            from .embed import embed
            feat = embed([art]).astype(np.float32)
        with self._lock:
            # Pro Artwork nur die neuesten paar behalten
            same = [k for k, i in zip(self.l_keys, self.l_ids) if i == image_id]
            for old in same[:max(0, len(same) - MAX_LEARNED_PER_IMAGE + 1)]:
                self._remove(old)
            self.l_keys.append(key)
            self.l_ids = np.append(self.l_ids, np.int64(image_id))
            self.l_hashes = np.vstack([self.l_hashes, phash(art)[None]])
            if feat is not None:
                self.l_feats = np.vstack([self.l_feats, feat])
            self._save_learned()
        return key

    def _remove(self, key: str) -> None:
        if key not in self.l_keys:
            return
        k = self.l_keys.index(key)
        self.l_keys.pop(k)
        self.l_ids = np.delete(self.l_ids, k)
        self.l_hashes = np.delete(self.l_hashes, k, axis=0)
        if len(self.l_feats):
            self.l_feats = np.delete(self.l_feats, k, axis=0)
        (LEARNED_DIR / f"{key}.jpg").unlink(missing_ok=True)

    def forget(self, key: str | None) -> None:
        if not key:
            return
        with self._lock:
            self._remove(key)
            self._save_learned()

    def forget_all(self) -> None:
        with self._lock:
            for key in list(self.l_keys):
                self._remove(key)
            self._save_learned()

    # ---------------------------------------------------------------- Erkennung
    def scores(self, card_img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(ids, Bewertung) aller Artworks inkl. gelernter Referenzen (größer = besser).
        Beide Ausrichtungen der Karte werden geprüft."""
        with self._lock:
            ids = np.concatenate([self.ids, self.l_ids])
            hashes = np.concatenate([self.hashes, self.l_hashes])
            feats = np.concatenate([self.feats, self.l_feats]) if self.feats is not None else None
        n_base = len(self.ids)
        arts = [card_artwork(card_img), card_artwork(cv2.rotate(card_img, cv2.ROTATE_180))]
        per_rotation = []
        for a in arts:
            dist = np.unpackbits(np.bitwise_xor(hashes, phash(a)), axis=1).sum(axis=1).astype(np.float32)
            s = _z(-dist)
            weak = dist[n_base:] > LEARNED_MAX_HASH_DIST
            if feats is not None:
                from .embed import embed
                sim = feats @ embed([a])[0]
                w = 1.0 if self.mode == "embed" else COMBO_EMBED_WEIGHT
                s = (1 - w) * s + w * _z(sim)
                weak = sim[n_base:] < LEARNED_MIN_SIM
            s[n_base:][weak] = -np.inf     # gelernte Bilder nur bei sehr hoher Ähnlichkeit berücksichtigen
            per_rotation.append(s)
        return ids, np.maximum(*per_rotation)

    def match(self, card_img: np.ndarray, top_k: int = 3) -> list[Candidate]:
        ids, s = self.scores(card_img)
        # Pro Karte nur das beste Artwork behalten (Alternativ-Artworks gehören zur selben Karte)
        picked, seen = [], set()
        for i in np.argsort(-s)[:200]:
            card = self.card_by_image[int(ids[i])]
            if card["id"] in seen:
                continue
            seen.add(card["id"])
            picked.append((card, int(ids[i]), float(s[i])))
            if len(picked) == 10:
                break
        sc = np.array([p[2] for p in picked])
        w = np.exp((sc - sc.max()) / COMBO_TEMPERATURE)
        conf = w / w.sum()
        if sc.max() < COMBO_MIN_SCORE:  # selbst der beste Treffer hebt sich kaum ab
            conf *= 0.3
        return [Candidate(c, i, v, float(p)) for (c, i, v), p in zip(picked[:top_k], conf[:top_k])]
