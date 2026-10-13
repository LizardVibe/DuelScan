# DuelScan

**Yu-Gi-Oh!-Karten per Webcam scannen und sofort sehen, was sie wert sind.**
Kostenlos, Open Source, läuft lokal auf deinem PC.

🇬🇧 [English README](README.md)

> DuelScan ist ein inoffizielles Fan-Projekt und steht in keiner Verbindung zu Konami.
> Yu-Gi-Oh! ist eine Marke von Konami. Preise ohne Gewähr.

## Funktionen

- **Schnell scannen:** Karte unter die Kamera legen. Sobald sie ruhig liegt, wird sie automatisch erkannt, ohne Klicken.
- **Lokale KI-Erkennung:** eine Kombination aus Bild-Fingerabdruck und einem kleinen KI-Modell (DINOv2), das auf der **CPU** läuft. Grafikkarte oder Cloud sind nicht nötig.
- **Wahrscheinlichkeit statt Raten:** Sichere Treffer werden automatisch übernommen. Bei unsicheren siehst du die 3 besten Kandidaten und bestätigst mit `1`/`2`/`3`.
- **Preise:**
  - Cardmarket-„ab“-Preis (EUR)
  - TCGplayer-Tagespreise **pro Seltenheit** (USD), kostenlos und unbegrenzt
  - optional **Live-Preise nach Zustand** (NM/LP/MP/HP/DMG) mit einem kostenlosen [TCG-Price-Lookup](https://tcgpricelookup.com/tcg-api)-Key
- **Klickbare Preise** führen zu Cardmarket und TCGplayer, und zwar direkt zum günstigsten Druck der gewählten Seltenheit.
- **Wert-Alarm:** Karten über deiner Schwelle bekommen einen goldenen Rahmen und einen eigenen Ton. Das hilft beim Durchsortieren von Bulk.
- **Sammlung** mit Anzahl, Seltenheit, Zustand und Gesamtwert, dazu ein **CSV-Export** der Scan-Liste.
- **5 Sprachen:** Deutsch, English, Español, Français, Italiano.

## Voraussetzungen

| | |
|---|---|
| Betriebssystem | Windows 10 / 11 (64 Bit) |
| Kamera | beliebige Webcam (1080p oder besser empfohlen) oder ein Handy als Webcam |
| Speicherplatz | ca. **2,5 GB** (≈1,5 GB Programm inkl. KI-Bibliotheken, ≈0,7 GB Kartendaten) |
| Internet | für die Ersteinrichtung und Preis-Updates |
| Grafikkarte | **nicht** nötig |
| Python | **nur für die Quellcode-Variante:** Python 3.10–3.12 ([python.org](https://www.python.org/downloads/), 3.11 empfohlen) |

## Installation

### Variante A: Setup (.exe), empfohlen
1. `DuelScan-Setup.exe` von der Release-Seite herunterladen und starten.
2. Windows zeigt eventuell die blaue Warnung „Der Computer wurde durch Windows geschützt“, weil die App kostenlos und nicht signiert ist. Klicke auf **Weitere Informationen → Trotzdem ausführen**.
3. Beim ersten Start lädt DuelScan einmalig die Kartendatenbank herunter (ca. 30–40 Minuten).

### Variante B: Quellcode (für Entwickler)
1. Python 3.11 von [python.org](https://www.python.org/downloads/) installieren und dabei **„Add python.exe to PATH“** anhaken.
2. Dieses Repository herunterladen oder klonen.
3. **`install.bat`** doppelklicken. Das richtet eine eigene Python-Umgebung ein und installiert alles, was ein paar Minuten dauert.
4. **`start.bat`** doppelklicken.

## Erster Start

Der Einrichtungs-Assistent lädt ca. 15.000 Kartenbilder, bereitet die Erkennung vor und holt die aktuellen Preise. Du kannst jederzeit abbrechen, beim nächsten Mal geht es an derselben Stelle weiter.

## Tipps für gute Scans

- Kamera **über** der Karte anbringen, senkrecht nach unten. Webcams brauchen meist **30–40 cm** Abstand, um scharf zu sein.
- **Einfarbiger, matter, heller Untergrund**, z.B. ein weißes Blatt Papier.
- Licht **von der Seite** (Schreibtischlampe), nicht direkt von oben, sonst spiegeln Foil-Karten.
- Die **Schärfe-Anzeige** oben in der Leiste hilft, die beste Position zu finden.

## Tastenkürzel

| Taste | Funktion |
|---|---|
| `1` / `2` / `3` | Kandidat wählen (korrigiert auch eine automatische Wahl) |
| `Leertaste` | besten Treffer übernehmen |
| `S` | zur Sammlung (nochmal = weiteres Exemplar) |
| `L` | Live-Preise laden (kostet 1 API-Anfrage) |
| `R` | neu scannen |
| `Strg+Z` | letzte Karte aus der Scan-Liste entfernen |
| `Entf` | ein Exemplar der markierten Karte aus der Sammlung entfernen |

## Preisquellen

| Quelle | Was | Kosten |
|---|---|---|
| [YGOPRODeck](https://ygoprodeck.com/api-guide/) | Kartendaten, Bilder, Cardmarket-„ab“-Preise | kostenlos |
| [tcgcsv.com](https://tcgcsv.com) | tägliche TCGplayer-Preise pro Druck | kostenlos |
| [TCG Price Lookup](https://tcgpricelookup.com/tcg-api) | Live-Preise nach Zustand | kostenloser Key, ca. 100 Anfragen/Tag |

Live-Preise werden nur für Karten ab einer einstellbaren Schwelle automatisch geladen (Standard 0,85 €). Ergebnisse werden 3 Tage gespeichert, um Anfragen zu sparen.

## Datenschutz

Alles läuft lokal. Sammlung, Einstellungen und API-Key liegen nur im Ordner `data/` auf deinem PC.

## Lizenz

[MIT](LICENSE). Frei nutzbar, weitergeben und verändern erlaubt. Kartenbilder und -daten sind nicht enthalten, sie lädt jeder Nutzer selbst von YGOPRODeck.
