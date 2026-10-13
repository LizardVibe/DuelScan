"""Kartendaten + Preise von YGOPRODeck laden und die Erkennungs-Indizes aufbauen.

Alle Schritte sind inkrementell: Beim Aktualisieren werden nur neue Karten/Bilder geladen und
nur deren Fingerabdrücke/KI-Merkmale berechnet. Fortschritt wird über einen Callback
progress(stage, done, total) gemeldet, Abbruch über ein threading.Event.
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import cv2
import numpy as np
import requests

from .config import API_URL, ART_DIR, CARDS_FILE, DATA_DIR, EMBED_FILE, INDEX_FILE
from .vision import phash, reference_artwork

Progress = Callable[[str, int, int], None]
STAGES = ("cards", "art", "index", "ai", "prices")


class Cancelled(Exception):
    pass


def _print_progress(stage: str, done: int, total: int) -> None:
    if total and (done == total or done % max(total // 20, 1) == 0):
        print(f"  [{stage}] {done}/{total}")


def is_ready() -> bool:
    """Ist die Ersteinrichtung abgeschlossen (Kartendaten + Erkennungs-Index vorhanden)?"""
    return CARDS_FILE.exists() and INDEX_FILE.exists()


def download_cards(progress: Progress = _print_progress) -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    progress("cards", 0, 1)
    r = requests.get(API_URL, timeout=180)
    r.raise_for_status()
    cards = r.json()["data"]
    CARDS_FILE.write_text(json.dumps(cards), encoding="utf-8")
    progress("cards", 1, 1)
    return cards


def load_cards() -> list[dict]:
    return json.loads(CARDS_FILE.read_text(encoding="utf-8"))


def _image_ids(cards: list[dict]) -> list[int]:
    return [img["id"] for c in cards for img in c.get("card_images", [])]


class _RateLimiter:
    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second
        self.lock = threading.Lock()
        self.next_time = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = self.next_time - now
            self.next_time = max(now, self.next_time) + self.interval
        if delay > 0:
            time.sleep(delay)


ART_MAX_SIDE = 320   # Erkennung rechnet mit 64-224 px; 320 px reicht auch für Vorschaubilder


def _save_small(data: bytes, path) -> None:
    """Artwork verkleinert speichern (~35 KB statt ~150 KB pro Bild, insgesamt ~0,5 statt 2 GB)."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("kein gültiges Bild")
    h, w = img.shape[:2]
    if max(h, w) > ART_MAX_SIDE:
        s = ART_MAX_SIDE / max(h, w)
        img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("Bild konnte nicht gespeichert werden")
    path.write_bytes(buf.tobytes())


def download_artworks(cards: list[dict], progress: Progress = _print_progress,
                      cancel: threading.Event | None = None, per_second: float = 10.0) -> int:
    """Lädt fehlende Artworks (beim ersten Mal ~15.000 Bilder). Gibt die Zahl der Fehlschläge zurück.

    YGOPRODeck bittet darum, Bilder einmalig herunterzuladen statt sie ständig abzurufen -
    deshalb gedrosselt auf ca. 10 Bilder pro Sekunde.
    """
    ART_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(img["id"], img["image_url_cropped"])
            for c in cards for img in c.get("card_images", [])
            if not (ART_DIR / f"{img['id']}.jpg").exists()]
    total = len(jobs)
    progress("art", 0, total)
    if not jobs:
        return 0
    limiter = _RateLimiter(per_second)
    session = requests.Session()
    lock = threading.Lock()
    state = {"done": 0, "failed": 0}

    def fetch(job):
        if cancel is not None and cancel.is_set():
            return
        img_id, url = job
        limiter.wait()
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            _save_small(r.content, ART_DIR / f"{img_id}.jpg")
        except Exception:  # noqa: BLE001 - einzelne fehlende Bilder sind kein Drama
            with lock:
                state["failed"] += 1
        with lock:
            state["done"] += 1
            done = state["done"]
        if done % 25 == 0 or done == total:
            progress("art", done, total)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, jobs))
    if cancel is not None and cancel.is_set():
        raise Cancelled
    return state["failed"]


def build_index(cards: list[dict], progress: Progress = _print_progress,
                cancel: threading.Event | None = None) -> None:
    """Bild-Fingerabdrücke (pHash). Vorhandene Einträge werden übernommen, nur neue berechnet."""
    old: dict[int, np.ndarray] = {}
    if INDEX_FILE.exists():
        idx = np.load(INDEX_FILE)
        old = dict(zip(idx["ids"].tolist(), idx["hashes"]))
    images = [i for i in _image_ids(cards) if (ART_DIR / f"{i}.jpg").exists()]
    todo = [i for i in images if i not in old]
    progress("index", 0, len(todo))
    for k, img_id in enumerate(todo, 1):
        if cancel is not None and cancel.is_set():
            raise Cancelled
        img = cv2.imread(str(ART_DIR / f"{img_id}.jpg"))
        if img is not None:
            old[img_id] = phash(reference_artwork(img))
        if k % 200 == 0 or k == len(todo):
            progress("index", k, len(todo))
    ids = [i for i in images if i in old]
    np.savez_compressed(INDEX_FILE, ids=np.array(ids, dtype=np.int64),
                        hashes=np.array([old[i] for i in ids], dtype=np.uint8))


def build_embeddings(cards: list[dict], progress: Progress = _print_progress,
                     cancel: threading.Event | None = None, batch: int = 64) -> None:
    """KI-Merkmale (DINOv2). Beim ersten Mal ca. 4-15 Minuten je nach CPU, danach nur neue Karten."""
    from .embed import embed

    old: dict[int, np.ndarray] = {}
    if EMBED_FILE.exists():
        idx = np.load(EMBED_FILE)
        old = dict(zip(idx["ids"].tolist(), idx["feats"]))
    images = [i for i in _image_ids(cards) if (ART_DIR / f"{i}.jpg").exists()]
    todo = [i for i in images if i not in old]
    progress("ai", 0, len(todo))
    for start in range(0, len(todo), batch):
        if cancel is not None and cancel.is_set():
            raise Cancelled
        chunk_ids, chunk_imgs = [], []
        for img_id in todo[start:start + batch]:
            img = cv2.imread(str(ART_DIR / f"{img_id}.jpg"))
            if img is not None:
                chunk_ids.append(img_id)
                chunk_imgs.append(reference_artwork(img))
        if chunk_imgs:
            for img_id, f in zip(chunk_ids, embed(chunk_imgs).astype(np.float16)):
                old[img_id] = f
        progress("ai", min(start + batch, len(todo)), len(todo))
    ids = [i for i in images if i in old]
    if ids:
        np.savez_compressed(EMBED_FILE, ids=np.array(ids, dtype=np.int64),
                            feats=np.stack([old[i] for i in ids]))


def setup(progress: Progress = _print_progress, cancel: threading.Event | None = None) -> None:
    """Komplette Einrichtung bzw. Aktualisierung: Kartendaten, Bilder, Indizes, Tagespreise."""
    from . import offline_prices
    cards = download_cards(progress)
    download_artworks(cards, progress, cancel)
    build_index(cards, progress, cancel)
    build_embeddings(cards, progress, cancel)
    if cancel is not None and cancel.is_set():
        raise Cancelled
    offline_prices.update(progress=progress)
