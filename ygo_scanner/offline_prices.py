"""Offline-Preisdatenbank aus den täglichen TCGplayer-Exporten von tcgcsv.com.

tcgcsv.com stellt einmal täglich (ca. 20 Uhr UTC) alle TCGplayer-Produkte und -Preise bereit,
kostenlos und ohne API-Key. Wir laden pro Set (TCGplayer "group") die Produkte und Preise und
bauen daraus einen Index: Kartenname -> alle Drucke mit Set-Code, Seltenheit, Edition, Preis, Link.

Produkte ändern sich selten und werden pro Set zwischengespeichert (nur neu geladen, wenn sich das
Set geändert hat). Preise werden bei jedem Update neu geladen.
"""
import datetime as dt
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .config import DATA_DIR

BASE = "https://tcgcsv.com/tcgplayer/2"          # 2 = Yu-Gi-Oh! bei TCGplayer
DIR = DATA_DIR / "tcgcsv"
PRODUCTS_DIR = DIR / "products"
INDEX_FILE = DIR / "index.json"
MAX_AGE_HOURS = 24


def norm(name: str) -> str:
    """Kartennamen vergleichbar machen ("Ash Blossom & Joyous Spring (UR)" -> "ashblossomjoyousspring")."""
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _session() -> requests.Session:
    s = requests.Session()
    # Ohne eigenen User-Agent antwortet tcgcsv mit 401
    s.headers["User-Agent"] = "YGO-Scanner/0.1 (personal card price lookup)"
    return s


def _get(session: requests.Session, url: str, tries: int = 3) -> dict:
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return {}


def _slim_products(results: list[dict]) -> list[dict]:
    """Nur Einzelkarten mit Set-Code behalten, unnötige Felder (Kartentext usw.) weglassen."""
    out = []
    for p in results:
        ext = {e["name"]: e["value"] for e in p.get("extendedData", [])}
        if not ext.get("Number") or not ext.get("Rarity"):
            continue   # Booster, Displays, Zubehör ...
        out.append({"id": p["productId"], "name": p["name"], "code": ext["Number"],
                    "rarity": ext["Rarity"], "url": p.get("url")})
    return out


def update(log=print, workers: int = 6, progress=None) -> None:
    """Lädt die aktuellen Daten von tcgcsv.com und baut den Index neu (ca. 1-3 Minuten)."""
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    s = _session()
    groups = _get(s, f"{BASE}/groups")["results"]
    log(f"Offline-Preise: {len(groups)} Sets werden geladen ...")
    if progress:
        progress("prices", 0, len(groups))

    def load_group(g: dict) -> tuple[dict, list[dict], list[dict]]:
        gid = g["groupId"]
        pfile = PRODUCTS_DIR / f"{gid}.json"
        products = None
        if pfile.exists():
            cached = json.loads(pfile.read_text(encoding="utf-8"))
            if cached.get("modifiedOn") == g.get("modifiedOn"):
                products = cached["products"]
        if products is None:
            products = _slim_products(_get(s, f"{BASE}/{gid}/products").get("results", []))
            pfile.write_text(json.dumps({"modifiedOn": g.get("modifiedOn"), "products": products}),
                             encoding="utf-8")
        prices = _get(s, f"{BASE}/{gid}/prices").get("results", []) if products else []
        return g, products, prices

    index: dict[str, list[dict]] = {}
    done = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in [pool.submit(load_group, g) for g in groups]:
            try:
                g, products, prices = fut.result()
            except Exception:  # noqa: BLE001 - ein kaputtes Set soll nicht alles abbrechen
                failed += 1
                continue
            by_id: dict[int, list[dict]] = {}
            for pr in prices:
                by_id.setdefault(pr["productId"], []).append(pr)
            for p in products:
                for pr in by_id.get(p["id"], [{}]):
                    market = pr.get("marketPrice") or pr.get("midPrice") or 0.0
                    index.setdefault(norm(p["name"]), []).append({
                        "code": p["code"], "rarity": p["rarity"], "edition": pr.get("subTypeName"),
                        "set": g["name"], "url": p["url"],
                        "prices": {"market": market, "low": pr.get("lowPrice") or 0.0}})
            done += 1
            if progress and (done % 10 == 0 or done == len(groups)):
                progress("prices", done, len(groups))
            if done % 100 == 0:
                log(f"  {done}/{len(groups)} Sets")

    DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps({"updated": time.time(), "cards": index}), encoding="utf-8")
    log(f"Offline-Preise fertig: {len(index)} Karten, {sum(map(len, index.values()))} Drucke"
        + (f", {failed} Sets fehlgeschlagen" if failed else ""))


class OfflinePrices:
    def __init__(self):
        self.updated: float | None = None
        self.cards: dict[str, list[dict]] = {}
        self.reload()

    def reload(self) -> None:
        try:
            d = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            self.updated, self.cards = d["updated"], d["cards"]
        except (OSError, ValueError, KeyError):
            self.updated, self.cards = None, {}

    @property
    def available(self) -> bool:
        return bool(self.cards)

    def needs_update(self) -> bool:
        return self.updated is None or time.time() - self.updated > MAX_AGE_HOURS * 3600

    def stand(self) -> str:
        return f"{dt.datetime.fromtimestamp(self.updated):%d.%m. %H:%M}" if self.updated else "–"

    def printings(self, name: str) -> list[dict]:
        return self.cards.get(norm(name), [])
