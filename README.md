# DuelScan

**Scan your Yu-Gi-Oh! cards with a webcam and instantly see what they're worth.**
Free, open source, runs locally on your PC.

🇩🇪 [Deutsche Anleitung](README.de.md)

> DuelScan is an unofficial fan project and is not affiliated with Konami.
> Yu-Gi-Oh! is a trademark of Konami. Prices are provided without guarantee.

## Features

- **Fast scanning:** put a card under the camera, it is recognized automatically as soon as it lies still. No clicking needed.
- **Local AI recognition:** a combination of image fingerprints and a small AI model (DINOv2) that runs on your **CPU**. No graphics card or cloud is needed.
- **Confidence instead of guessing:** confident matches are accepted automatically. Uncertain ones show the top 3 candidates, and you confirm with `1`/`2`/`3`.
- **Prices:**
  - Cardmarket "from" price (EUR)
  - TCGplayer daily prices **per rarity** (USD), free and unlimited
  - optional **live prices per condition** (NM/LP/MP/HP/DMG) with a free [TCG Price Lookup](https://tcgpricelookup.com/tcg-api) key
- **Clickable prices** open Cardmarket and TCGplayer, going straight to the cheapest printing of the chosen rarity.
- **Value alert:** cards above your threshold get a gold frame and play a sound, which helps when sorting bulk.
- **Collection** with quantity, rarity, condition and total value, plus a **CSV export** of your scan list.
- **5 languages:** English, Deutsch, Español, Français, Italiano.

## Requirements

| | |
|---|---|
| Operating system | Windows 10 / 11 (64-bit) |
| Camera | any webcam (1080p or better recommended) or a phone used as a webcam |
| Disk space | about **2.5 GB** (≈1.5 GB program incl. AI libraries, ≈0.7 GB card data) |
| Internet | for the first setup and price updates |
| Graphics card | **not** needed |
| Python | **only for the source version:** Python 3.10–3.12 ([python.org](https://www.python.org/downloads/), 3.11 recommended) |

## Installation

### Option A: Setup (.exe), recommended
1. Download `DuelScan-Setup.exe` from the releases page and run it.
2. Windows may show a blue "Windows protected your PC" warning, because the app is free and not code-signed. Click **More info → Run anyway**.
3. On first start, DuelScan downloads the card database once (about 30–40 minutes).

### Option B: Source code (for developers)
1. Install Python 3.11 from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**.
2. Download or clone this repository.
3. Double-click **`install.bat`**. It creates a virtual environment and installs everything, which takes a few minutes.
4. Double-click **`start.bat`**.

Command line alternative:
```
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scan.py
```

## First start

The setup assistant downloads about 15,000 card images, prepares the recognition and loads the current prices. You can cancel at any time, and it continues where it stopped next time.

## Tips for good scans

- Mount the camera **above** the card, looking straight down. A webcam usually needs **30–40 cm** distance to be sharp.
- Use a **plain, matte, light background**, e.g. a sheet of white paper.
- Light from the **side** (desk lamp), not straight from above, which causes glare on foils.
- The **sharpness meter** in the toolbar helps you find the best position.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `1` / `2` / `3` | choose a candidate (also corrects an automatic choice) |
| `Space` | accept best match |
| `S` | add to collection (press again for another copy) |
| `L` | load live prices (uses 1 API request) |
| `R` | rescan |
| `Ctrl+Z` | remove last card from the scan list |
| `Del` | remove one copy of the selected card from the collection |

## Price sources

| Source | What | Cost |
|---|---|---|
| [YGOPRODeck](https://ygoprodeck.com/api-guide/) | card data, images, Cardmarket "from" prices | free |
| [tcgcsv.com](https://tcgcsv.com) | daily TCGplayer prices per printing | free |
| [TCG Price Lookup](https://tcgpricelookup.com/tcg-api) | live prices per condition | free key, about 100 requests/day |

Live prices are only loaded automatically for cards above a threshold you set (default 0.85 €). Results are cached for 3 days to save requests.

## Privacy

Everything runs locally. Your collection, settings and API key are stored only in the `data/` folder on your PC.

## License

[MIT](LICENSE). Free to use, share and modify. Card images and data are not included and are downloaded by each user from YGOPRODeck.
