"""DuelScan – Sammelkarten per Webcam scannen und Preise anzeigen.

  python scan.py                  Scanner starten (beim ersten Start mit Einrichtungs-Assistent)
  python scan.py --camera 1       andere Kamera verwenden
  python scan.py --setup          Daten laden/aktualisieren ohne Oberfläche (Kommandozeile)
  python scan.py --image foto.jpg Einzelnes Foto erkennen (Test ohne Kamera)
"""
import argparse
import sys


def _log_to_file_when_frozen() -> None:
    """In der .exe gibt es keine Konsole (stdout/stderr sind None) -> Ausgaben in eine Logdatei."""
    from ygo_scanner.config import FROZEN, USER_DIR
    if FROZEN:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        log = open(USER_DIR / "duelscan.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log


def main() -> None:
    _log_to_file_when_frozen()
    ap = argparse.ArgumentParser(description="DuelScan")
    ap.add_argument("--setup", "--update-prices", dest="setup", action="store_true",
                    help="Kartendaten, Bilder, Erkennung und Preise laden bzw. aktualisieren")
    ap.add_argument("--image", help="Foto statt Webcam verwenden")
    ap.add_argument("--camera", type=int, help="Kamera-Nummer (Standard: aus den Einstellungen)")
    args = ap.parse_args()

    if args.setup:
        from ygo_scanner import database
        database.setup()
        return

    if args.image:
        from ygo_scanner import app, database
        if not database.is_ready():
            sys.exit("Noch keine Daten vorhanden. Bitte zuerst:  python scan.py --setup")
        app.scan_image(args.image)
        return

    from ygo_scanner import gui
    gui.run(args.camera)


if __name__ == "__main__":
    main()
