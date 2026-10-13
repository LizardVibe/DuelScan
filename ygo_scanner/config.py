import os
import sys
from pathlib import Path

APP_NAME = "DuelScan"
APP_VERSION = "0.1.0"

FROZEN = getattr(sys, "frozen", False)          # True in der installierten .exe-Version
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

if FROZEN:
    # Installierte Programme dürfen nicht in ihren Programmordner schreiben -> Benutzerordner
    USER_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    DATA_DIR = USER_DIR / "data"
    SCANS_DIR = Path.home() / "Documents" / APP_NAME
    DEBUG_DIR = USER_DIR / "debug"
else:
    # Quellcode-Variante: alles im Projektordner
    USER_DIR = ROOT
    DATA_DIR = ROOT / "data"
    SCANS_DIR = ROOT / "scans"
    DEBUG_DIR = ROOT / "scans" / "debug"

# Optional: eigener Datenordner (z.B. für portable Nutzung oder Tests)
if os.environ.get("DUELSCAN_DATA_DIR"):
    DATA_DIR = Path(os.environ["DUELSCAN_DATA_DIR"])

ART_DIR = DATA_DIR / "art"
CARDS_FILE = DATA_DIR / "cards.json"
INDEX_FILE = DATA_DIR / "index.npz"
EMBED_FILE = DATA_DIR / "embeddings.npz"
# KI-Modell (DINOv2) ebenfalls bei den Daten ablegen statt im globalen torch-Cache
os.environ.setdefault("TORCH_HOME", str(DATA_DIR / "torch"))

API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

# Normalisierte Kartengröße nach dem Entzerren (Pixel), entspricht den YGOPRODeck-Vollbildern.
CARD_W, CARD_H = 421, 614
# Artwork-Box auf der entzerrten Karte (x1, y1, x2, y2) für normale Karten.
ART_BOX = (50, 111, 371, 432)
# Rand, der beim Artwork-Vergleich innen abgeschnitten wird (Anteil), um Ungenauigkeiten abzufangen.
ART_MARGIN = 0.04

# Matching
AUTO_ACCEPT_CONFIDENCE = 0.90
# Kombiniertes Matching (z-normalisierte Werte von pHash und KI)
COMBO_EMBED_WEIGHT = 0.5   # Anteil der KI (0 = nur pHash, 1 = nur KI)
COMBO_TEMPERATURE = 0.4    # kleiner = Wahrscheinlichkeiten "entschiedener"
COMBO_MIN_SCORE = 4.0      # bester Wert darunter -> insgesamt unsicher

# Stabilitätserkennung: so viele ruhige Frames, bevor gescannt wird
STABLE_FRAMES = 6
STABLE_MAX_MOVE_PX = 6.0
