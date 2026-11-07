"""Wechselkurs Dollar -> Euro, damit TCGplayer-Preise (USD) mit dem Wert-Alarm (EUR) vergleichbar sind.

Quelle: Referenzkurse der Europäischen Zentralbank (einmal täglich, kostenlos, kein Key).
Es wird nur eine Zahl geladen und in data/fx.json gespeichert; ohne Internet gilt der letzte
bekannte Kurs bzw. ein grober Standardwert.
"""
import json
import re
import time

import requests

from .config import DATA_DIR

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FX_FILE = DATA_DIR / "fx.json"
FALLBACK_USD_PER_EUR = 1.10     # grober Notwert, falls noch nie ein Kurs geladen wurde

_cache: dict | None = None


def update() -> float | None:
    """Aktuellen EZB-Kurs laden und speichern. Gibt USD pro EUR zurück (oder None bei Fehler)."""
    global _cache
    try:
        r = requests.get(ECB_URL, timeout=20)
        r.raise_for_status()
        m = re.search(r"currency=['\"]USD['\"]\s+rate=['\"]([0-9.]+)['\"]", r.text)
        if not m:
            return None
        rate = float(m.group(1))
        if not 0.5 < rate < 2.5:      # Plausibilitätscheck
            return None
        _cache = {"usd_per_eur": rate, "t": time.time()}
        FX_FILE.parent.mkdir(parents=True, exist_ok=True)
        FX_FILE.write_text(json.dumps(_cache), encoding="utf-8")
        return rate
    except (requests.RequestException, ValueError, OSError):
        return None


def usd_per_eur() -> float:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(FX_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = {"usd_per_eur": FALLBACK_USD_PER_EUR, "t": 0}
    return float(_cache.get("usd_per_eur") or FALLBACK_USD_PER_EUR)


def usd_to_eur(usd: float) -> float:
    return usd / usd_per_eur()
