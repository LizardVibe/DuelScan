"""Live-Preise pro Druck/Seltenheit/Zustand über die TCG Price Lookup API (TCGplayer-Marktpreise, USD).

Der Gratis-Tarif erlaubt nur ca. 100 Anfragen pro Tag. Deshalb:
  - eine Anfrage pro Karte (liefert alle Drucke auf einmal),
  - Ergebnisse werden einige Tage in data/price_cache.json zwischengespeichert.
"""
import json
import re
import threading
import time

import requests

from .config import DATA_DIR

API = "https://api.tcgpricelookup.com/v1/cards/search"
CACHE_FILE = DATA_DIR / "price_cache.json"
QUOTA_FILE = DATA_DIR / "price_quota.json"
CACHE_DAYS = 3
CONDITIONS = ["near_mint", "lightly_played", "moderately_played", "heavily_played", "damaged"]
CONDITION_SHORT = {"near_mint": "NM", "lightly_played": "LP", "moderately_played": "MP",
                   "heavily_played": "HP", "damaged": "DMG"}


class PriceError(Exception):
    pass


def _norm(name: str) -> str:
    # Schreibweisen angleichen, z.B. "Yummy★Snatchy" vs. "Yummy*Snatchy"
    return re.sub(r"[^a-z0-9]", "", name.lower())


class LivePrices:
    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.remaining: int | None = None     # verbleibende Anfragen heute
        self.limit: int | None = None         # Anfragen pro Tag laut API
        self.reset: float | None = None       # Zeitpunkt (Unix), an dem das Kontingent zurückgesetzt wird
        self.lock = threading.Lock()
        try:
            q = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            self.remaining, self.limit, self.reset = q["remaining"], q["limit"], q["reset"]
        except (OSError, ValueError, KeyError):
            pass
        try:
            self.cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.cache = {}

    def quota(self) -> tuple[int | None, int | None, float | None]:
        """(übrig, Limit, Reset-Zeitpunkt). Nach dem Reset gilt wieder das volle Limit."""
        if self.reset and time.time() >= self.reset and self.limit:
            return self.limit, self.limit, None
        return self.remaining, self.limit, self.reset

    def _update_quota(self, headers) -> None:
        rem, lim, rst = (_header_int(headers, f"x-ratelimit-{k}") for k in ("remaining", "limit", "reset"))
        if rem is None:
            return
        self.remaining, self.limit, self.reset = rem, lim or self.limit, rst or self.reset
        try:
            QUOTA_FILE.write_text(json.dumps({"remaining": self.remaining, "limit": self.limit,
                                              "reset": self.reset}), encoding="utf-8")
        except OSError:
            pass

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def cached(self, name: str) -> list[dict] | None:
        e = self.cache.get(name)
        if e and time.time() - e["t"] < CACHE_DAYS * 86400:
            return e["printings"]
        return None

    def fetch(self, name: str) -> list[dict]:
        """Alle Drucke einer Karte: [{code, rarity, edition, set, prices: {zustand: usd}}]."""
        hit = self.cached(name)
        if hit is not None:
            return hit
        if not self.enabled:
            raise PriceError("err_no_key")
        try:
            r = requests.get(API, params={"q": name, "game": "yugioh", "limit": 100},
                             headers={"X-API-Key": self.api_key}, timeout=20)
        except requests.RequestException as e:
            raise PriceError("err_connection") from e
        self._update_quota(r.headers)
        if r.status_code == 429:
            raise PriceError("err_limit")
        if r.status_code != 200:
            raise PriceError("err_http")

        printings = []
        for c in r.json().get("data", []):
            # Namen wie "Ash Blossom & Joyous Spring (UR)" gehören auch dazu, andere Karten nicht
            if _norm(re.sub(r"\s*\(.*\)$", "", c.get("name", ""))) != _norm(name):
                continue
            raw = (c.get("prices") or {}).get("raw") or {}
            prices = {k: (v.get("tcgplayer") or {}).get("market") for k, v in raw.items()}
            printings.append({"code": c.get("number"), "rarity": c.get("rarity"), "edition": c.get("variant"),
                              "set": (c.get("set") or {}).get("name"),
                              "prices": {k: v for k, v in prices.items() if v}})
        with self.lock:
            self.cache[name] = {"t": time.time(), "printings": printings}
            CACHE_FILE.write_text(json.dumps(self.cache), encoding="utf-8")
        return printings


def _header_int(headers, name: str) -> int | None:
    try:
        return int(headers[name])
    except (KeyError, ValueError):
        return None


def rarities_live(printings: list[dict], condition: str = "near_mint") -> list[dict]:
    """Wie collection.rarities, aber mit TCGplayer-Preisen: günstigster Druck je Seltenheit.

    condition: Zustand bei Live-Daten ("near_mint", ...) bzw. "market" bei den Offline-Tagespreisen.
    """
    from .collection import RARITY_ORDER
    groups: dict[str, list] = {}
    for p in printings:
        r = p["rarity"] or "?"
        label = f"{p['code']} {p['edition'] or ''}".strip()
        groups.setdefault(r, []).append((label, p["prices"].get(condition) or 0.0, p.get("url")))
    out = []
    for r, sets in groups.items():
        known = [s for s in sets if s[1] > 0]
        cheapest = min(known, key=lambda s: s[1]) if known else None
        out.append({"rarity": r, "price": cheapest[1] if cheapest else 0.0,
                    "url": cheapest[2] if cheapest else None,
                    "sets": sorted((label, price) for label, price, _ in sets)})
    rank = {r: i for i, r in enumerate(RARITY_ORDER + ["Common / Short Print"])}
    rank["Common / Short Print"] = 0
    return sorted(out, key=lambda d: (rank.get(d["rarity"], len(rank)), d["rarity"]))
