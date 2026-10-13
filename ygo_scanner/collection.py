"""Sammlung (SQLite) und Einstellungen."""
import datetime as dt
import json
import sqlite3
from urllib.parse import quote_plus

from .config import DATA_DIR

DB_FILE = DATA_DIR / "collection.db"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "language": None,          # None = Systemsprache
    "alarm_enabled": True,
    "alarm_threshold_eur": 2.0,
    "auto_collection": False,
    "camera": 0,
    "live_price_min_eur": 0.85,
    "tcgpricelookup_api_key": None,
}


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def price(card: dict, key: str) -> float:
    try:
        return float((card.get("card_prices") or [{}])[0].get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


RARITY_ORDER = [
    "Common", "Short Print", "Super Short Print", "Rare", "Super Rare", "Ultra Rare", "Secret Rare",
    "Ultimate Rare", "Ghost Rare", "Gold Rare", "Premium Gold Rare", "Gold Secret Rare", "Platinum Rare",
    "Platinum Secret Rare", "Prismatic Secret Rare", "Quarter Century Secret Rare", "Starlight Rare",
    "Collector's Rare", "Starfoil Rare", "Shatterfoil Rare", "Mosaic Rare",
]
_RARITY_FIX = {"PLatinum Secret Rare": "Platinum Secret Rare", "Starfoil": "Starfoil Rare"}
_RARITY_WORDS = ("Rare", "Print", "Common", "Starfoil")


def rarities(card: dict) -> list[dict]:
    """Alle Seltenheiten einer Karte: [{rarity, price (günstigster bekannter Druck, 0 = unbekannt), sets}]."""
    groups: dict[str, list[tuple[str, float]]] = {}
    for s in card.get("card_sets") or []:
        r = _RARITY_FIX.get(s.get("set_rarity", ""), s.get("set_rarity", ""))
        if not any(w in r for w in _RARITY_WORDS):   # Datenmüll wie "2", "New", "Reprint" überspringen
            continue
        try:
            p = float(s.get("set_price") or 0)
        except ValueError:
            p = 0.0
        groups.setdefault(r, []).append((s.get("set_code", "?"), p))
    out = []
    for r, sets in groups.items():
        known = [p for _, p in sets if p > 0]
        out.append({"rarity": r, "price": min(known) if known else 0.0, "sets": sets})
    rank = {r: i for i, r in enumerate(RARITY_ORDER)}
    return sorted(out, key=lambda d: (rank.get(d["rarity"], len(rank)), d["rarity"]))


def cardmarket_url(card: dict) -> str:
    return f"https://www.cardmarket.com/de/YuGiOh/Products/Search?searchString={quote_plus(card['name'])}"


def tcgplayer_url(card: dict) -> str:
    return f"https://www.tcgplayer.com/search/yugioh/product?productLineName=yugioh&q={quote_plus(card['name'])}"


class Collection:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_FILE)
        self.db.execute("""CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            image_id INTEGER,
            added_at TEXT NOT NULL,
            price_cm_at_add REAL,
            price_tcg_at_add REAL,
            set_code TEXT, rarity TEXT, condition TEXT)""")
        self.db.commit()

    def add(self, card: dict, image_id: int, rarity: str | None = None, rarity_price: float = 0.0,
            condition: str | None = None) -> int:
        self.db.execute(
            "INSERT INTO cards (card_id, name, image_id, added_at, price_cm_at_add, price_tcg_at_add, rarity, "
            "condition) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (card["id"], card["name"], image_id, dt.datetime.now().isoformat(timespec="seconds"),
             price(card, "cardmarket_price"), rarity_price or price(card, "tcgplayer_price"), rarity, condition))
        self.db.commit()
        return self.count(card["id"])

    def remove_one(self, card_id: int, rarity: str | None) -> None:
        self.db.execute("DELETE FROM cards WHERE id = (SELECT MAX(id) FROM cards WHERE card_id = ? "
                        "AND rarity IS ?)", (card_id, rarity))
        self.db.commit()

    def count(self, card_id: int) -> int:
        return self.db.execute("SELECT COUNT(*) FROM cards WHERE card_id = ?", (card_id,)).fetchone()[0]

    def grouped(self) -> list[tuple[int, str, str | None, int, str]]:
        """(card_id, name, seltenheit, anzahl, zuletzt hinzugefügt), neueste zuerst."""
        return self.db.execute(
            "SELECT card_id, name, rarity, COUNT(*), MAX(added_at) FROM cards "
            "GROUP BY card_id, rarity ORDER BY MAX(id) DESC"
        ).fetchall()
