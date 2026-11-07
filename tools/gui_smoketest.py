"""Automatischer Oberflächen-Test ohne Kamera (läuft unsichtbar, ohne Töne, verändert keine echten Daten).

  python tools/gui_smoketest.py [pfad/zu/kamerafoto.jpg]

Prüft: Erkennung + Lernen, Suche, Duplikate, Seltenheits-Vorschlag, Hit-Alarm.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

import cv2  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from ygo_scanner import collection, gui, i18n, matcher as M, rarity as R  # noqa: E402
from ygo_scanner.matcher import Candidate  # noqa: E402
from ygo_scanner.vision import find_card, warp_card  # noqa: E402

# Alles, was geschrieben wird, in einen Wegwerf-Ordner umleiten
TMP = Path(tempfile.mkdtemp(prefix="duelscan_test_"))
collection.DB_FILE = TMP / "collection.db"
M.LEARNED_DIR = TMP / "learned"
M.LEARNED_FILE = M.LEARNED_DIR / "learned.npz"
R.SAMPLES_DIR = TMP / "rarity_samples"
sounds: list[bool] = []
gui.play_sound = lambda alarm: sounds.append(alarm)
gui.save_settings = lambda s: None
gui.ScannerWorker.run = lambda self: None
gui.MainWindow._start_price_update = lambda self, with_cards: None   # keine Netz-Updates im Test

failures = []


def check(name: str, ok: bool, detail=""):
    print(("  OK   " if ok else "  FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


def main(photo: str) -> int:
    app = QApplication([])
    i18n.set_language("de")
    w = gui.MainWindow(collection.load_settings())
    w.resize(1600, 1000)
    w.show()
    m = M.Matcher()
    w.worker.matcher = m
    f = cv2.imread(photo)
    card = warp_card(f, find_card(f))

    print("Erkennung & Lernen")
    cands = m.match(card)
    check("Foto wird erkannt", cands[0].confidence > 0.5, f"{cands[0].name} {cands[0].confidence:.0%}")
    for c, p in zip(cands, (0.5, 0.3, 0.2)):
        c.confidence = p                         # unsicheren Scan simulieren
    w._on_scanned(cands, card)
    w.choose(0)
    time.sleep(1.5)
    check("unsichere Bestätigung wird gelernt", m.learned_count == 1)
    check("danach sicherer erkannt", m.match(card)[0].confidence >= 0.9)

    print("Seltenheits-Vorschlag")
    w._on_scanned(m.match(card), card)
    app.processEvents()
    c = w._current()
    check("Vorschlag vorhanden", bool(c.rarity_guess), str({k: f"{v:.0%}" for k, v in (c.rarity_guess or {}).items()}))
    check("Preiszeile zeigt Vorschlag", (c.rarity or "") in w.tcg_label.text())

    print("Suche")
    d = gui.SearchDialog(w, list(w._cards_by_id.values()))
    d.edit.setText("ash bloss")
    check("Suche findet Ash Blossom", d.list.count() >= 1 and "Ash Blossom" in d.list.item(0).text())

    print("Duplikate")
    w.scan_list.clear()
    for _ in range(3):
        w._on_scanned(m.match(card), card)
        w.choose(0)
    check("3 gleiche Karten = 1 Zeile mit 3×", w.scan_table.rowCount() == 1 and w.scan_table.item(0, 2).text() == "3×")
    w.undo()
    check("Strg+Z -> 2×", w.scan_table.item(0, 2).text() == "2×")

    print("Hit-Alarm")
    w.alarm_check.setChecked(True)
    w.alarm_value.setValue(5.0)
    cards = {x["name"]: x for x in w._cards_by_id.values()}
    ash = cards["Ash Blossom & Joyous Spring"]
    sounds.clear()
    w._on_scanned([Candidate(ash, ash["card_images"][0]["id"], 9.0, 0.97)], None)
    check("billige Version: kein Alarm", w.alarm_label.text() == "")
    opts = w._rarity_options(w._current())[1]
    pricey = max(opts, key=lambda o: o["price"])
    w.choose_rarity(pricey)
    check("teure Seltenheit -> HIT + Ton", "HIT" in w.alarm_label.text() and sounds[-1] is True,
          w.alarm_label.text())
    check("kein Vorschlag ohne Kamerabild", not w._current().rarity_guess)

    print("Ergebnis:", "alles OK" if not failures else f"{len(failures)} Fehler: {failures}")
    w.close()
    return 1 if failures else 0


if __name__ == "__main__":
    default = ROOT.parent / "scans" / "snap.jpg"
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(default)))
