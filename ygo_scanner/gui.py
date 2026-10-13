"""Desktop-Oberfläche (PySide6).

Tasten:  1/2/3 Kandidat wählen | Leertaste besten übernehmen | S zur Sammlung | L Live-Preise
         R neu scannen | Strg+Z letzte Karte aus der Scan-Liste | Entf: aus Sammlung entfernen
Alle sichtbaren Texte kommen aus i18n.py (t("key")).
"""
import csv
import datetime as dt
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import requests
from PySide6.QtCore import QObject, QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSlider, QTableWidget,
                               QTableWidgetItem, QTabWidget, QToolBar, QVBoxLayout, QWidget)

from . import database, offline_prices
from .collection import (Collection, cardmarket_url, load_settings, price, rarities, save_settings,
                         tcgplayer_url)
from .config import (APP_NAME, APP_VERSION, ART_DIR, ASSETS_DIR, AUTO_ACCEPT_CONFIDENCE, DATA_DIR, DEBUG_DIR, SCANS_DIR,
                     STABLE_FRAMES, STABLE_MAX_MOVE_PX)
from .i18n import LANGUAGES, set_language, system_language, t
from .matcher import Candidate, Matcher
from .prices import CONDITION_SHORT, CONDITIONS, LivePrices, PriceError, rarities_live
from .setup_dialog import SetupDialog
from .vision import find_card, warp_card

FULL_DIR = DATA_DIR / "full"
GOLD = "#f5c542"

STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #e6e6eb; }
QMainWindow, QWidget#root, QScrollArea, QDialog { background: #15161a; }
QToolBar { background: #1d1f25; border: none; padding: 6px; spacing: 10px; }
QFrame#result { background: #1f2128; border: 2px solid #2c2f38; border-radius: 12px; }
QFrame#result[alarm="true"] { border: 3px solid #f5c542; background: #2a2618; }
QLabel#name { font-size: 20px; font-weight: 600; }
QLabel#sub { color: #9a9cab; }
QLabel#price { font-size: 16px; }
QLabel#alarm { color: #f5c542; font-size: 15px; font-weight: 700; }
QLabel#badge { border-radius: 9px; padding: 2px 10px; font-size: 12px; font-weight: 700; }
QLabel#badge[state="live"] { background: #1f3d2a; color: #69db7c; border: 1px solid #2f9e44; }
QLabel#badge[state="ygo"] { background: #3d2e14; color: #ffa94d; border: 1px solid #e8590c; }
QLabel#badge[state="loading"] { background: #1f2d45; color: #74c0fc; border: 1px solid #1c7ed6; }
QLabel#badge[state="daily"] { background: #163a3a; color: #63e6be; border: 1px solid #0ca678; }
QLabel#status { color: #9a9cab; padding: 4px 2px; }
QLabel#camera { background: #0d0e11; border-radius: 12px; }
QPushButton { background: #2a2d36; border: 1px solid #3a3e4a; border-radius: 8px; padding: 8px 12px; }
QPushButton:hover { background: #343844; }
QPushButton:pressed { background: #23262e; }
QPushButton:disabled { color: #6b6e7a; }
QPushButton#primary { background: #3b5bdb; border-color: #4c6ef5; }
QPushButton#primary:hover { background: #4c6ef5; }
QPushButton#collect { background: #2b8a3e; border-color: #37b24d; }
QPushButton#collect:hover { background: #37b24d; }
QPushButton#cand { text-align: left; padding: 6px 10px; }
QPushButton#cand[chosen="true"] { border: 2px solid #4c6ef5; background: #263056; }
QPushButton#rarity { padding: 4px 6px; font-size: 12px; border-radius: 6px; }
QPushButton#rarity:checked { border: 2px solid #f5c542; background: #3a3320; }
QLabel#raritytitle { color: #9a9cab; font-size: 12px; }
QPushButton#cond { padding: 3px 8px; font-size: 12px; border-radius: 6px; }
QPushButton#cond:checked { border: 2px solid #4c6ef5; background: #263056; }
QTabWidget::pane { border: 1px solid #2c2f38; border-radius: 8px; top: -1px; }
QTabBar::tab { background: #1f2128; padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:selected { background: #2c2f38; }
QTableWidget { background: #1a1c21; gridline-color: #2a2d36; border: none; selection-background-color: #34405e; }
QHeaderView::section { background: #1f2128; border: none; padding: 6px; color: #9a9cab; }
QDoubleSpinBox, QLineEdit, QComboBox { background: #2a2d36; border: 1px solid #3a3e4a; border-radius: 6px;
    padding: 4px; }
QProgressBar { background: #2a2d36; border: none; border-radius: 6px; height: 12px; }
QProgressBar::chunk { background: #4c6ef5; border-radius: 6px; }
a { color: #74c0fc; }
"""


def eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(v: float) -> str:
    return f"$ {v:,.2f}"


def amp(text: str) -> str:
    """'&' auf Buttons verdoppeln (sonst macht Qt daraus eine Tastenkürzel-Markierung)."""
    return text.replace("&", "&&")


def play_sound(alarm: bool) -> None:
    if sys.platform != "win32":
        return
    import winsound
    if alarm:
        def melody():
            for f, d in ((880, 90), (1175, 90), (1568, 160)):
                winsound.Beep(f, d)
        threading.Thread(target=melody, daemon=True).start()
    else:
        winsound.MessageBeep(winsound.MB_OK)


# --------------------------------------------------------------------------- Kamera-Thread
class ScannerWorker(QThread):
    frame_ready = Signal(QImage, float)           # Vorschaubild, Schärfe der Karte (-1 = keine Karte)
    scanned = Signal(object, object)               # Kandidaten, entzerrte Karte
    status = Signal(str)

    def __init__(self, camera: int):
        super().__init__()
        self.camera = camera
        self.running = True
        self.rescan = threading.Event()
        self.zoom = 1.0                 # nur für die Vorschau, die Erkennung nutzt immer das volle Bild
        self.matcher: Matcher | None = None
        self._center = None

    def run(self):
        self.status.emit(t("loading_model"))
        matcher = self.matcher = Matcher()
        # Media Foundation statt DirectShow: manche Webcams liefern über DirectShow nur schwarze Bilder
        cap = cv2.VideoCapture(self.camera, cv2.CAP_MSMF)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
        if not cap.isOpened():
            self.status.emit(t("camera_failed", n=self.camera))
            return
        self.status.emit(t("ready"))

        prev, stable, missing, done = None, 0, 0, False
        while self.running:
            ok, frame = cap.read()
            if not ok:
                self.status.emit(t("no_frame"))
                self.msleep(200)
                continue
            if self.rescan.is_set():
                self.rescan.clear()
                done, stable = False, 0

            quad = find_card(frame)
            sharpness = -1.0
            if quad is not None:
                missing = 0
                gray = cv2.cvtColor(warp_card(frame, quad), cv2.COLOR_BGR2GRAY)
                sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                move = np.abs(quad - prev).max() if prev is not None else 1e9
                stable = stable + 1 if move < STABLE_MAX_MOVE_PX else 0
                prev = quad
                if stable >= STABLE_FRAMES and not done:
                    done = True
                    card = warp_card(frame, quad)
                    cands = matcher.match(card)
                    if cands[0].confidence < AUTO_ACCEPT_CONFIDENCE:
                        save_debug(frame, card, cands)
                    self.scanned.emit(cands, card)
            else:
                missing += 1
                stable, prev = 0, None
                if missing > 8:  # Karte weggenommen -> bereit für die nächste
                    done = False

            view = frame.copy()
            if quad is not None:
                color = (80, 200, 80) if done or stable >= STABLE_FRAMES else (0, 200, 230)
                cv2.polylines(view, [quad.astype(np.int32)], True, color, 5, cv2.LINE_AA)
            view = self._zoomed(view, quad)
            # Vorschau verkleinern, damit die Oberfläche flüssig bleibt
            scale = 1280 / view.shape[1]
            small = cv2.resize(view, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            self.frame_ready.emit(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy(), sharpness)
        cap.release()

    def _zoomed(self, frame: np.ndarray, quad) -> np.ndarray:
        """Ausschnitt für die Vorschau; folgt sanft der Karte, wenn eine erkannt ist."""
        h, w = frame.shape[:2]
        target = quad.mean(axis=0) if quad is not None else np.array([w / 2, h / 2])
        self._center = target if self._center is None else 0.8 * self._center + 0.2 * target
        if self.zoom <= 1.0:
            return frame
        cw, ch = int(w / self.zoom), int(h / self.zoom)
        x = int(np.clip(self._center[0] - cw / 2, 0, w - cw))
        y = int(np.clip(self._center[1] - ch / 2, 0, h - ch))
        return frame[y:y + ch, x:x + cw]


def save_debug(frame: np.ndarray, card: np.ndarray, cands: list[Candidate]) -> None:
    """Unsichere Scans speichern, um die Erkennung später verbessern zu können."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    stem = DEBUG_DIR / f"{dt.datetime.now():%Y%m%d_%H%M%S}"
    cv2.imwrite(f"{stem}_frame.jpg", frame)
    cv2.imwrite(f"{stem}_card.jpg", card)
    with open(f"{stem}.txt", "w", encoding="utf-8") as f:
        for c in cands:
            f.write(f"{c.confidence:.2f}  {c.score:.3f}  {c.name}\n")


# --------------------------------------------------------------------------- Hintergrund-Lader
class ImageLoader(QObject):
    loaded = Signal(int, QImage)    # image_id, Bild (QImage, weil QPixmap nur im GUI-Thread erlaubt ist)

    def __init__(self):
        super().__init__()
        FULL_DIR.mkdir(parents=True, exist_ok=True)
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.cache: dict[int, QImage] = {}

    def request(self, card: dict, image_id: int):
        if image_id in self.cache:
            self.loaded.emit(image_id, self.cache[image_id])
            return
        url = next((i["image_url"] for i in card["card_images"] if i["id"] == image_id), None)
        self.pool.submit(self._load, image_id, url)

    def _load(self, image_id: int, url: str | None):
        path = FULL_DIR / f"{image_id}.jpg"
        try:
            if not path.exists() and url:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                path.write_bytes(r.content)
            img = QImage(str(path))
        except Exception:  # noqa: BLE001 - ohne Internet: Artwork als Ersatz
            img = QImage(str(ART_DIR / f"{image_id}.jpg"))
        if not img.isNull():
            self.cache[image_id] = img
            self.loaded.emit(image_id, img)


class LiveLoader(QObject):
    ready = Signal(str, object)     # Kartenname, Drucke
    failed = Signal(str, str)       # Kartenname, Fehlercode

    def __init__(self, live: LivePrices):
        super().__init__()
        self.live = live
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending: set[str] = set()

    def request(self, name: str):
        hit = self.live.cached(name)
        if hit is not None:
            self.ready.emit(name, hit)
        elif name not in self.pending:
            self.pending.add(name)
            self.pool.submit(self._load, name)

    def _load(self, name: str):
        try:
            self.ready.emit(name, self.live.fetch(name))
        except PriceError as e:
            self.failed.emit(name, str(e))
        finally:
            self.pending.discard(name)


class PriceUpdater(QObject):
    """Aktualisiert Cardmarket-"ab"-Preise (YGOPRODeck) und TCGplayer-Tagespreise (tcgcsv)."""
    progress = Signal(str, int, int)
    finished = Signal(bool, str, object)    # ok, Fehlermeldung, neue Kartendaten (oder None)

    def start(self, with_cards: bool):
        threading.Thread(target=self._run, args=(with_cards,), daemon=True).start()

    def _run(self, with_cards: bool):
        fresh = None
        try:
            if with_cards:
                fresh = {c["id"]: c for c in database.download_cards(progress=lambda *a: None)}
            offline_prices.update(log=lambda *a: None, progress=self.progress.emit)
            self.finished.emit(True, "", fresh)
        except Exception as e:  # noqa: BLE001
            self.finished.emit(False, str(e), fresh)


# --------------------------------------------------------------------------- Einstellungen
class SettingsDialog(QDialog):
    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(600)
        self.update_db_requested = False
        form = QFormLayout(self)
        form.setSpacing(12)
        form.setContentsMargins(18, 18, 18, 18)

        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(max(self.language.findData(settings.get("language")), 0))
        form.addRow(t("language"), self.language)
        self.lang_hint = QLabel(t("language_restart"), objectName="sub")
        self.lang_hint.hide()
        self.language.currentIndexChanged.connect(lambda _: self.lang_hint.show())
        form.addRow("", self.lang_hint)

        # Kamera: Namen von Windows abfragen, Reihenfolge = Kamera-Nummer
        self.camera = QComboBox()
        try:
            from PySide6.QtMultimedia import QMediaDevices
            names = [d.description() for d in QMediaDevices.videoInputs()]
        except Exception:  # noqa: BLE001
            names = []
        for i in range(max(len(names), 1)):
            self.camera.addItem(f"{i}: {names[i]}" if i < len(names) else t("camera_n", n=i), i)
        self.camera.setCurrentIndex(max(self.camera.findData(settings.get("camera", 0)), 0))
        form.addRow(t("camera"), self.camera)

        key_row = QHBoxLayout()
        self.api_key = QLineEdit(settings.get("tcgpricelookup_api_key") or "")
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText(t("api_key_placeholder"))
        show = QCheckBox(t("show"))
        show.toggled.connect(lambda on: self.api_key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        key_row.addWidget(self.api_key, 1)
        key_row.addWidget(show)
        form.addRow(t("api_key"), key_row)
        hint = QLabel(t("api_help"), objectName="sub", wordWrap=True)
        hint.setTextFormat(Qt.RichText)
        hint.setOpenExternalLinks(True)
        form.addRow("", hint)

        self.live_min = QDoubleSpinBox()
        self.live_min.setRange(0.0, 1000.0)
        self.live_min.setDecimals(2)
        self.live_min.setSingleStep(0.25)
        self.live_min.setSuffix(" € (Cardmarket)")
        self.live_min.setValue(float(settings.get("live_price_min_eur", 0.85)))
        form.addRow(t("live_min"), self.live_min)

        db_btn = QPushButton(t("update_db_btn"))
        db_btn.clicked.connect(self._request_db_update)
        form.addRow(t("card_db"), db_btn)
        form.addRow("", QLabel(t("update_db_hint"), objectName="sub", wordWrap=True))

        about = QLabel(f"{APP_NAME} {APP_VERSION}  ·  " + t("disclaimer", app=APP_NAME), objectName="sub",
                       wordWrap=True)
        form.addRow("", about)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(t("save"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _request_db_update(self):
        self.update_db_requested = True
        self.accept()

    def values(self) -> dict:
        return {"language": self.language.currentData(),
                "camera": self.camera.currentData(),
                "tcgpricelookup_api_key": self.api_key.text().strip() or None,
                "live_price_min_eur": self.live_min.value()}


# --------------------------------------------------------------------------- Hauptfenster
class MainWindow(QMainWindow):
    def __init__(self, settings: dict, camera: int | None = None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 900)
        self.settings = settings
        if camera is not None:
            self.settings["camera"] = camera
        self.collection = Collection()
        self.images = ImageLoader()
        self.images.loaded.connect(self._on_image)
        self.live = LivePrices(self.settings.get("tcgpricelookup_api_key"))
        self.live_loader = LiveLoader(self.live)
        self.live_loader.ready.connect(self._on_live)
        self.live_loader.failed.connect(self._on_live_failed)
        self.live_data: dict[str, list] = {}   # Kartenname -> Drucke mit Live-Preisen
        self.offline = offline_prices.OfflinePrices()
        self.price_updater = PriceUpdater()
        self.price_updater.progress.connect(
            lambda _s, d, n: self.set_status(t("status_prices_progress", done=d, total=n)))
        self.price_updater.finished.connect(self._on_prices_updated)
        self._cards_by_id = {c["id"]: c for c in database.load_cards()}

        self.candidates: list[Candidate] = []
        self.chosen: int | None = None        # gewählter Kandidat der aktuellen Karte
        self.in_list = False                   # aktuelle Karte steht schon in der Scan-Liste
        self.scan_list: list[Candidate] = []
        self.best_sharp = 0.0

        self._build_ui()
        self._build_shortcuts()
        if self.offline.needs_update():   # Tagespreise älter als 24 h -> im Hintergrund erneuern
            self._start_price_update(with_cards=False)
        self.update_quota()
        self.refresh_collection()

        self.worker: ScannerWorker | None = None
        self.start_worker()

    def start_worker(self):
        if self.worker is not None:
            self.worker.running = False
            self.worker.wait(3000)
        self.worker = ScannerWorker(self.settings.get("camera", 0))
        self._zoom_changed(self.zoom_slider.value())
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.scanned.connect(self._on_scanned)
        self.worker.status.connect(self.set_status)
        self.worker.start()

    # ---------------------------------------------------------------- Aufbau
    def _build_ui(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        self.alarm_check = QCheckBox(t("alarm_from"))
        self.alarm_check.setChecked(self.settings["alarm_enabled"])
        self.alarm_value = QDoubleSpinBox()
        self.alarm_value.setRange(0.0, 10000.0)
        self.alarm_value.setDecimals(2)
        self.alarm_value.setSingleStep(0.5)
        self.alarm_value.setSuffix(" € (Cardmarket)")
        self.alarm_value.setValue(self.settings["alarm_threshold_eur"])
        self.auto_coll = QCheckBox(t("auto_collection"))
        self.auto_coll.setChecked(self.settings["auto_collection"])
        for w in (self.alarm_check, self.alarm_value, self.auto_coll):
            tb.addWidget(w)
        for sig in (self.alarm_check.toggled, self.alarm_value.valueChanged, self.auto_coll.toggled):
            sig.connect(self._save_settings)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self.refresh_btn = QPushButton(t("refresh_btn"))
        self.refresh_btn.setToolTip(t("refresh_tooltip"))
        self.refresh_btn.clicked.connect(lambda: self._start_price_update(with_cards=True))
        export_btn = QPushButton(t("export_btn"))
        export_btn.clicked.connect(self.export_csv)
        settings_btn = QPushButton(t("settings_btn"))
        settings_btn.clicked.connect(self.open_settings)
        for b in (self.refresh_btn, export_btn, settings_btn):
            b.setFocusPolicy(Qt.NoFocus)
            tb.addWidget(b)

        # Zweite Zeile: Kamera-Infos und API-Kontingent
        self.addToolBarBreak()
        tb2 = QToolBar()
        tb2.setMovable(False)
        self.addToolBar(tb2)
        tb2.addWidget(QLabel(t("zoom")))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 40)          # 1,0x bis 4,0x
        self.zoom_slider.setValue(int(self.settings.get("preview_zoom", 1.0) * 10))
        self.zoom_slider.setFixedWidth(140)
        self.zoom_slider.setFocusPolicy(Qt.NoFocus)
        self.zoom_text = QLabel()
        self.zoom_slider.valueChanged.connect(self._zoom_changed)
        tb2.addWidget(self.zoom_slider)
        tb2.addWidget(self.zoom_text)
        tb2.addSeparator()
        self.sharp_label = QLabel(t("sharp_none"))
        tb2.addWidget(self.sharp_label)
        tb2.addSeparator()
        self.quota_label = QLabel()
        self.quota_label.setToolTip(t("quota_tooltip"))
        tb2.addWidget(self.quota_label)

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(14)

        # Links: Kamera
        left = QVBoxLayout()
        self.camera_label = QLabel(objectName="camera", alignment=Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 360)
        self.camera_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.status_label = QLabel(t("starting"), objectName="status")
        left.addWidget(self.camera_label, 1)
        left.addWidget(self.status_label)
        lay.addLayout(left, 3)

        # Rechts: Ergebnis, Kandidaten, Listen
        right = QVBoxLayout()
        right.setSpacing(10)
        self.result = QFrame(objectName="result")
        outer = QVBoxLayout(self.result)
        outer.setContentsMargins(14, 14, 14, 14)
        rl = QHBoxLayout()
        outer.addLayout(rl)
        self.card_img = QLabel(alignment=Qt.AlignCenter)
        self.card_img.setFixedSize(190, 277)
        rl.addWidget(self.card_img)
        info = QVBoxLayout()
        self.name_label = QLabel(t("no_card_yet"), objectName="name", wordWrap=True)
        self.name_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.name_label.setOpenExternalLinks(True)
        self.sub_label = QLabel("", objectName="sub", wordWrap=True)
        self.price_badge = QLabel("", objectName="badge")
        self.price_badge.hide()
        self.cm_label = QLabel("", objectName="price")
        self.tcg_label = QLabel("", objectName="price")
        for lbl in (self.cm_label, self.tcg_label):
            lbl.setOpenExternalLinks(True)
            lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.alarm_label = QLabel("", objectName="alarm")
        self.coll_label = QLabel("", objectName="sub")
        badge_row = QHBoxLayout()
        badge_row.addWidget(self.price_badge)
        badge_row.addStretch()
        info.addWidget(self.name_label)
        info.addWidget(self.sub_label)
        info.addLayout(badge_row)
        for w in (self.cm_label, self.tcg_label, self.alarm_label, self.coll_label):
            info.addWidget(w)
        info.addStretch()
        cond_row = QHBoxLayout()
        cond_row.setSpacing(6)
        cond_row.addWidget(QLabel(t("condition"), objectName="raritytitle"))
        self.cond_buttons: dict[str, QPushButton] = {}
        for cond in CONDITIONS:
            b = QPushButton(CONDITION_SHORT[cond], objectName="cond")
            b.setCheckable(True)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, cnd=cond: self.choose_condition(cnd))
            cond_row.addWidget(b)
            self.cond_buttons[cond] = b
        cond_row.addStretch()
        self.live_btn = QPushButton(t("live_btn"), objectName="cond")
        self.live_btn.setFocusPolicy(Qt.NoFocus)
        self.live_btn.clicked.connect(self.load_live)
        live_row = QHBoxLayout()
        live_row.addWidget(self.live_btn)
        live_row.addStretch()
        info.addLayout(cond_row)
        info.addLayout(live_row)
        rl.addLayout(info, 1)
        self.rarity_title = QLabel("", objectName="raritytitle")
        self.rarity_title.setWordWrap(True)
        outer.addWidget(self.rarity_title)
        self.rarity_grid = QGridLayout()
        self.rarity_grid.setSpacing(6)
        outer.addLayout(self.rarity_grid)
        self.rarity_buttons: list[QPushButton] = []
        right.addWidget(self.result)

        self.cand_buttons = []
        for i in range(3):
            b = QPushButton(objectName="cand")
            b.setIconSize(QSize(48, 48))
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, i=i: self.choose(i))
            b.hide()
            right.addWidget(b)
            self.cand_buttons.append(b)

        row = QHBoxLayout()
        accept_btn = QPushButton(t("accept_btn"), objectName="primary")
        accept_btn.clicked.connect(lambda: self.choose(self.chosen if self.chosen is not None else 0))
        collect_btn = QPushButton(t("collect_btn"), objectName="collect")
        collect_btn.clicked.connect(self.add_to_collection)
        rescan_btn = QPushButton(t("rescan_btn"))
        rescan_btn.clicked.connect(self.rescan)
        for b in (accept_btn, collect_btn, rescan_btn):
            b.setFocusPolicy(Qt.NoFocus)
            row.addWidget(b)
        right.addLayout(row)

        self.tabs = QTabWidget()
        self.scan_table = self._make_table([t("col_card"), t("col_rarity"), "Cardmarket", "TCGplayer",
                                            t("confidence")])
        self.scan_total = QLabel(objectName="sub")
        self.coll_table = self._make_table([t("col_card"), t("col_rarity"), t("col_count"), "Cardmarket",
                                            "TCGplayer", t("col_value")])
        self.coll_total = QLabel(objectName="sub")
        for table, total, title in ((self.scan_table, self.scan_total, t("tab_scan")),
                                    (self.coll_table, self.coll_total, t("tab_coll"))):
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(6, 6, 6, 6)
            v.addWidget(table)
            v.addWidget(total)
            self.tabs.addTab(w, title)
        self.scan_table.cellClicked.connect(lambda r, c: self._open_price(self.scan_list[r], c, 2, 3))
        self.coll_table.cellClicked.connect(self._coll_clicked)
        self.tabs.setMinimumHeight(220)
        right.addWidget(self.tabs, 1)

        right.addWidget(QLabel(t("hint_keys"), objectName="sub", wordWrap=True))
        rw = QWidget(objectName="root")
        rw.setLayout(right)
        scroll = QScrollArea()          # scrollbar, damit bei kleinen Fenstern nichts übereinander rutscht
        scroll.setWidget(rw)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(580)
        lay.addWidget(scroll)
        self.update_scan_table()

    def _make_table(self, headers: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.verticalHeader().hide()
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, len(headers)):
            tbl.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        return tbl

    def _build_shortcuts(self):
        for key, fn in (("1", lambda: self.choose(0)), ("2", lambda: self.choose(1)), ("3", lambda: self.choose(2)),
                        ("Space", lambda: self.choose(self.chosen if self.chosen is not None else 0)),
                        ("S", self.add_to_collection), ("R", self.rescan), ("L", self.load_live),
                        ("Ctrl+Z", self.undo), ("Delete", self.remove_from_collection)):
            QShortcut(QKeySequence(key), self, activated=fn)

    # ---------------------------------------------------------------- Ereignisse
    def set_status(self, text: str):
        self.status_label.setText(text)

    def _on_frame(self, img: QImage, sharpness: float):
        pm = QPixmap.fromImage(img).scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(pm)
        if sharpness < 0:
            self.sharp_label.setText(t("sharp_nocard"))
            return
        self._sharp = sharpness if not hasattr(self, "_sharp") else 0.85 * self._sharp + 0.15 * sharpness
        self.best_sharp = max(self.best_sharp, self._sharp)
        # Grobe Einordnung (Laplace-Varianz der entzerrten Karte, abhängig vom Motiv)
        verdict, color = ((t("sharp_good"), "#51cf66") if self._sharp >= 80 else
                          (t("sharp_ok"), "#fcc419") if self._sharp >= 30 else (t("sharp_blurry"), "#ff6b6b"))
        value = f'<b style="color:{color}">{self._sharp:.0f} ({verdict})</b>'
        self.sharp_label.setText(t("sharp_fmt", value=value, best=f"{self.best_sharp:.0f}"))

    def _zoom_changed(self, v: int):
        if self.worker is not None:
            self.worker.zoom = v / 10
        self.zoom_text.setText(f"{v / 10:.1f}×")
        self.settings["preview_zoom"] = v / 10
        save_settings(self.settings)

    def _on_scanned(self, cands: list[Candidate], _card_img):
        self.candidates, self.chosen, self.in_list = cands, None, False
        for i, b in enumerate(self.cand_buttons):
            if i < len(cands):
                c = cands[i]
                b.setIcon(QIcon(QPixmap(str(ART_DIR / f"{c.image_id}.jpg"))))
                b.setText(f"  [{i + 1}]  {c.confidence:4.0%}   {amp(c.name)}   ·   "
                          f"{eur(price(c.card, 'cardmarket_price'))}")
                b.show()
            else:
                b.hide()
        if cands[0].confidence >= AUTO_ACCEPT_CONFIDENCE:
            self.choose(0, auto=True)
        else:
            self.show_card(cands[0], tentative=True)
            self.set_status(t("status_uncertain"))
            play_sound(False)
        self._mark_chosen()

    def _on_image(self, image_id: int, img: QImage):
        c = self._current()
        if c is not None and c.image_id == image_id:
            self.card_img.setPixmap(QPixmap.fromImage(img).scaled(self.card_img.size(), Qt.KeepAspectRatio,
                                                                  Qt.SmoothTransformation))

    # ---------------------------------------------------------------- Aktionen
    def _current(self) -> Candidate | None:
        if not self.candidates:
            return None
        return self.candidates[self.chosen if self.chosen is not None else 0]

    def choose(self, i: int, auto: bool = False):
        if i is None or i >= len(self.candidates):
            return
        c = self.candidates[i]
        if self.in_list:
            self.scan_list[-1] = c   # Wahl für diese Karte korrigieren
        else:
            self.scan_list.append(c)
            self.in_list = True
        self.chosen = i
        self.update_scan_table()
        alarm = self.show_card(c)
        self._mark_chosen()
        self.set_status(t("status_recognized" if auto else "status_accepted", name=c.name))
        play_sound(alarm)
        if self.auto_coll.isChecked() and auto:
            self.add_to_collection()

    def add_to_collection(self):
        if not self.candidates:
            return
        if self.chosen is None:
            self.choose(0)
        c = self.candidates[self.chosen]
        n = self.collection.add(c.card, c.image_id, c.rarity, c.rarity_price,
                                CONDITION_SHORT[c.condition] if c.name in self.live_data else None)
        self.coll_label.setText(t("in_collection_n", n=n))
        self.set_status(t("status_added", name=c.name, n=n))
        self.refresh_collection()

    def remove_from_collection(self):
        rows = self.coll_table.selectionModel().selectedRows()
        if not rows:
            self.set_status(t("status_select_remove"))
            return
        card_id, rarity = self.coll_table.item(rows[0].row(), 0).data(Qt.UserRole)
        self.collection.remove_one(card_id, rarity)
        self.refresh_collection()
        self.set_status(t("status_removed_one"))

    def rescan(self):
        if self.worker is not None:
            self.worker.rescan.set()
        self.set_status(t("status_rescanning"))

    def undo(self):
        if self.scan_list:
            removed = self.scan_list.pop()
            self.in_list = False
            self.update_scan_table()
            self.set_status(t("status_removed_list", name=removed.name))

    def export_csv(self):
        if not self.scan_list:
            self.set_status(t("status_list_empty"))
            return
        SCANS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCANS_DIR / f"scan_{dt.datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(t("csv_header").split(";"))
            for c in self.scan_list:
                w.writerow([c.name, c.card.get("type", ""), c.rarity or "", price(c.card, "cardmarket_price"),
                            c.rarity_price or price(c.card, "tcgplayer_price"), f"{c.confidence:.0%}"])
        self.set_status(t("status_saved", path=path))

    def choose_rarity(self, opt: dict):
        if self.chosen is None:
            return
        c = self.candidates[self.chosen]
        same = c.rarity == opt["rarity"]
        # nochmal klicken = abwählen
        c.rarity, c.rarity_price, c.rarity_url = ((None, 0.0, None) if same
                                                  else (opt["rarity"], opt["price"], opt.get("url")))
        for b in self.rarity_buttons:
            b.setChecked(not same and b.property("rarity") == opt["rarity"])
        self._set_tcg_label(c)
        self.update_scan_table()
        self.set_status(t("status_rarity", r=c.rarity) if c.rarity else t("status_rarity_cleared"))

    def choose_condition(self, cond: str):
        c = self._current()
        if c is None or self.chosen is None:
            return
        c.condition = cond
        if c.name not in self.live_data:
            self.load_live()   # kostet 1 Anfrage; die Preise kommen über _on_live
            return
        self._build_rarity_buttons(c, enabled=True)
        self._set_tcg_label(c)
        self.update_scan_table()

    def load_live(self):
        c = self._current()
        if c is None or self.chosen is None:
            return
        if not self.live.enabled:
            self.set_status(t("status_no_key"))
            return
        self.set_status(t("status_loading_live", name=c.name))
        self.live_loader.request(c.name)
        if c.name not in self.live_data:
            self._set_badge("loading")

    def _on_live(self, name: str, printings: list):
        self.live_data[name] = printings
        self.update_quota()
        c = self._current()
        if c is not None and c.name == name and self.chosen is not None:
            self._build_rarity_buttons(c, enabled=True)
            self._set_tcg_label(c)
            self.update_scan_table()
            rem = self.live.quota()[0]
            left = t("status_requests_left", n=rem) if rem is not None else ""
            self.set_status(t("status_live_loaded", n=len(printings)) + left)

    def _on_live_failed(self, name: str, code: str):
        self.update_quota()
        c = self._current()
        if c is not None and c.name == name and self.chosen is not None:
            self._build_rarity_buttons(c, enabled=True)
        self.set_status(t("status_live_failed", name=name, msg=t(code)))

    def _start_price_update(self, with_cards: bool):
        if not self.refresh_btn.isEnabled():
            return
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(t("refreshing"))
        self.set_status(t("status_updating_prices"))
        self.price_updater.start(with_cards)

    def _on_prices_updated(self, ok: bool, msg: str, fresh: dict | None):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(t("refresh_btn"))
        if fresh:
            # Neue Cardmarket-Preise in die bestehenden Kartendaten übernehmen (auch beim Erkenner)
            matcher_cards = self.worker.matcher.card_by_image.values() if self.worker and self.worker.matcher else []
            for c in list(self._cards_by_id.values()) + list(matcher_cards):
                if c["id"] in fresh:
                    c["card_prices"] = fresh[c["id"]].get("card_prices", c.get("card_prices"))
        if not ok:
            self.set_status(t("status_prices_failed", msg=msg))
            return
        self.offline.reload()
        self.set_status(t("status_prices_updated", date=self.offline.stand()))
        c = self._current()
        if c is not None and self.chosen is not None:
            self.show_card(c)
        self.update_scan_table()
        self.refresh_collection()

    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec() != QDialog.Accepted:
            return
        new = dlg.values()
        camera_changed = new["camera"] != self.settings.get("camera")
        self.settings.update(new)
        save_settings(self.settings)
        self.live.api_key = self.settings.get("tcgpricelookup_api_key") or None
        self.update_quota()
        c = self._current()
        if c is not None and self.chosen is not None:
            self._build_rarity_buttons(c, enabled=True)
        if dlg.update_db_requested:
            self.update_database()
        elif camera_changed:
            self.set_status(t("status_switch_camera"))
            self.start_worker()
        else:
            self.set_status(t("status_settings_saved"))

    def update_database(self):
        """Neue Karten + Bilder laden; danach Erkennung mit den neuen Indizes neu starten."""
        if SetupDialog(self, update=True).exec() == QDialog.Accepted:
            self._cards_by_id = {c["id"]: c for c in database.load_cards()}
            self.offline.reload()
            self.start_worker()
            self.refresh_collection()

    # ---------------------------------------------------------------- Anzeige
    def show_card(self, c: Candidate, tentative: bool = False) -> bool:
        cm = price(c.card, "cardmarket_price")
        url = c.card.get("ygoprodeck_url", "")
        self.name_label.setText(f'<a style="color:#e6e6eb;text-decoration:none" href="{url}">{c.name}</a>'
                                + (" ?" if tentative else ""))
        self.sub_label.setText(f"{c.card.get('type', '')}  ·  {t('confidence')} {c.confidence:.0%}"
                               + (f"  ·  {t('uncertain')}" if tentative else ""))
        self.cm_label.setText(f'{t("cm_from")} <a style="color:#74c0fc" href="{cardmarket_url(c.card)}">{eur(cm)}</a>')
        if not tentative and self.live.enabled and (
                c.name in self.live_data or self.live.cached(c.name) is not None
                or cm >= float(self.settings.get("live_price_min_eur", 0.85))):
            self.live_loader.request(c.name)
        self._set_tcg_label(c)
        self._build_rarity_buttons(c, enabled=not tentative)
        n = self.collection.count(c.card["id"])
        self.coll_label.setText(t("in_collection_n", n=n) if n else t("not_in_collection"))

        alarm = not tentative and self.alarm_check.isChecked() and cm >= self.alarm_value.value()
        self.alarm_label.setText(t("alarm_text", value=eur(self.alarm_value.value())) if alarm else "")
        self.result.setProperty("alarm", alarm)
        self.result.style().unpolish(self.result)
        self.result.style().polish(self.result)

        self.card_img.setPixmap(QPixmap(str(ART_DIR / f"{c.image_id}.jpg")).scaled(
            self.card_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.images.request(c.card, c.image_id)
        return alarm

    def _set_tcg_label(self, c: Candidate):
        link = c.rarity_url or tcgplayer_url(c.card)   # mit Seltenheit: direkt zum günstigsten Druck
        if c.rarity:
            val = usd(c.rarity_price) if c.rarity_price else t("no_price_known")
            cond = f" {CONDITION_SHORT[c.condition]}" if c.name in self.live_data else ""
            self.tcg_label.setText(f'TCGplayer · {c.rarity}{cond}: <a style="color:#74c0fc" href="{link}">{val}</a>')
        else:
            self.tcg_label.setText(f'{t("tcg_from")} <a style="color:#74c0fc" href="{link}">'
                                   f'{usd(price(c.card, "tcgplayer_price"))}</a>')

    def _rarity_options(self, c: Candidate) -> tuple[str, list[dict]]:
        """Preisquelle wählen: Live (mit Zustand) > TCGplayer-Tagespreise > YGOPRODeck."""
        live = self.live_data.get(c.name)
        if live:
            return "live", rarities_live(live, c.condition)
        daily = self.offline.printings(c.name)
        if daily:
            return "daily", rarities_live(daily, "market")
        return "ygo", rarities(c.card)

    def _build_rarity_buttons(self, c: Candidate, enabled: bool):
        for b in self.rarity_buttons:
            self.rarity_grid.removeWidget(b)
            b.hide()   # sonst flackert der alte Button kurz an falscher Stelle
            b.deleteLater()
        self.rarity_buttons = []
        source, options = self._rarity_options(c)
        live = source == "live"
        if source == "live":
            self.rarity_title.setText(t("rarity_title_live", cond=CONDITION_SHORT[c.condition]))
        elif source == "daily":
            self.rarity_title.setText(t("rarity_title_daily"))
        elif options:
            self.rarity_title.setText(t("rarity_title_ygo") + (t("rarity_hint_live") if self.live.enabled else ""))
        else:
            self.rarity_title.setText(t("no_rarities"))
        if c.rarity and c.rarity not in {o["rarity"] for o in options}:
            c.rarity, c.rarity_price, c.rarity_url = None, 0.0, None   # Seltenheit gibt es in dieser Quelle nicht
        if len(options) == 1 and not c.rarity:
            c.rarity = options[0]["rarity"]
        for o in options:
            if o["rarity"] == c.rarity:
                c.rarity_price, c.rarity_url = o["price"], o.get("url")
        for cond, b in self.cond_buttons.items():
            b.setChecked(live and cond == c.condition)
            b.setEnabled(enabled and (live or self.live.enabled))
            b.setToolTip("" if live else t("cond_tooltip"))
        self.live_btn.setVisible(self.live.enabled and not live)
        self.live_btn.setEnabled(enabled)
        if live:
            self._set_badge("live")
        elif c.name in self.live_loader.pending:
            self._set_badge("loading")
        else:
            self._set_badge(source)
        for k, opt in enumerate(options):
            p = usd(opt["price"]) if opt["price"] else t("no_price")
            b = QPushButton(f"{amp(opt['rarity'])}\n{p}", objectName="rarity")
            b.setProperty("rarity", opt["rarity"])
            b.setCheckable(True)
            b.setChecked(opt["rarity"] == c.rarity)
            b.setEnabled(enabled)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolTip("\n".join(f"{code}: {usd(pr) if pr else t('no_price')}" for code, pr in opt["sets"]))
            b.clicked.connect(lambda _=False, o=opt: self.choose_rarity(o))
            self.rarity_grid.addWidget(b, k // 3, k % 3)
            self.rarity_buttons.append(b)

    def _set_badge(self, state: str):
        if state == "live":
            text = t("badge_live")
        elif state == "daily":
            text = t("badge_daily", date=self.offline.stand())
        elif state == "loading":
            text = t("badge_loading")
        else:
            state = "ygo"
            text = t("badge_ygo") + (t("badge_ygo_L") if self.live.enabled else "")
        self.price_badge.setText(text)
        self.price_badge.setProperty("state", state)
        self.price_badge.style().unpolish(self.price_badge)
        self.price_badge.style().polish(self.price_badge)
        self.price_badge.show()

    def update_quota(self):
        if not self.live.enabled:
            self.quota_label.setText(t("quota_no_key"))
            return
        rem, lim, rst = self.live.quota()
        if rem is None:
            self.quota_label.setText(t("quota_unknown"))
            return
        color = "#69db7c" if rem > 30 else "#ffa94d" if rem > 10 else "#ff6b6b"
        text = t("quota_fmt", rem=f'<b style="color:{color}">{rem}</b>', lim=lim or "?")
        if rst and rem < (lim or 0):
            text += t("quota_reset", time=f"{dt.datetime.fromtimestamp(rst):%H:%M}")
        self.quota_label.setText(text)

    def _mark_chosen(self):
        for i, b in enumerate(self.cand_buttons):
            b.setProperty("chosen", i == self.chosen)
            b.style().unpolish(b)
            b.style().polish(b)

    def update_scan_table(self):
        tbl = self.scan_table
        tbl.setRowCount(len(self.scan_list))
        total_cm = total_tcg = 0.0
        for r, c in enumerate(self.scan_list):
            cm = price(c.card, "cardmarket_price")
            tcg = c.rarity_price or price(c.card, "tcgplayer_price")
            total_cm += cm
            total_tcg += tcg
            self._set_row(tbl, r, [c.name, c.rarity or "–", eur(cm), usd(tcg), f"{c.confidence:.0%}"],
                          link_cols=(2, 3), gold=self.alarm_check.isChecked() and cm >= self.alarm_value.value())
        tbl.scrollToBottom()
        self.scan_total.setText(t("scan_total", n=len(self.scan_list), cm=eur(total_cm), tcg=usd(total_tcg)))

    def refresh_collection(self):
        rows = self.collection.grouped()
        tbl = self.coll_table
        tbl.setRowCount(len(rows))
        total = count = 0
        self._coll_cards = []
        for r, (card_id, name, rarity, n, _last) in enumerate(rows):
            card = self._cards_by_id.get(card_id, {"id": card_id, "name": name})
            cm = price(card, "cardmarket_price")
            daily = self.offline.printings(name)
            opts = rarities_live(daily, "market") if daily else rarities(card)
            opt = next((d for d in opts if d["rarity"] == rarity), None) if rarity else None
            tcg = (opt["price"] if opt else 0.0) or price(card, "tcgplayer_price")
            total += cm * n
            count += n
            self._coll_cards.append((card, opt.get("url") if opt else None))
            self._set_row(tbl, r, [name, rarity or "–", str(n), eur(cm), usd(tcg), eur(cm * n)], link_cols=(3, 4),
                          gold=self.alarm_check.isChecked() and cm >= self.alarm_value.value())
            tbl.item(r, 0).setData(Qt.UserRole, (card_id, rarity))
        self.coll_total.setText(t("coll_total", n=count, k=len(rows), value=eur(total)))

    def _set_row(self, tbl: QTableWidget, r: int, values: list[str], link_cols=(), gold=False):
        for col, v in enumerate(values):
            it = QTableWidgetItem(v)
            if col in link_cols:
                it.setForeground(QColor("#74c0fc"))
                it.setToolTip(t("click_opens"))
            elif gold and col == 0:
                it.setForeground(QColor(GOLD))
            if col > 0:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tbl.setItem(r, col, it)

    def _open_price(self, c: Candidate, col: int, cm_col: int, tcg_col: int):
        if col == cm_col:
            QDesktopServices.openUrl(QUrl(cardmarket_url(c.card)))
        elif col == tcg_col:
            QDesktopServices.openUrl(QUrl(c.rarity_url or tcgplayer_url(c.card)))

    def _coll_clicked(self, r: int, col: int):
        card, url = self._coll_cards[r]
        if col == 3:
            QDesktopServices.openUrl(QUrl(cardmarket_url(card)))
        elif col == 4:
            QDesktopServices.openUrl(QUrl(url or tcgplayer_url(card)))

    def _save_settings(self, *_):
        self.settings.update(alarm_enabled=self.alarm_check.isChecked(),
                             alarm_threshold_eur=self.alarm_value.value(),
                             auto_collection=self.auto_coll.isChecked())
        save_settings(self.settings)
        self.update_scan_table()
        self.refresh_collection()

    def closeEvent(self, e):
        if self.worker is not None:
            self.worker.running = False
            self.worker.wait(3000)
        if self.scan_list:
            self.export_csv()
        super().closeEvent(e)


def run(camera: int | None = None) -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(ASSETS_DIR / "icon.png")))
    app.setStyleSheet(STYLE)
    settings = load_settings()
    if not settings.get("language"):
        settings["language"] = system_language()
        save_settings(settings)
    set_language(settings["language"])

    # Erster Start: Daten fehlen noch -> Einrichtungs-Assistent
    if not database.is_ready():
        if SetupDialog().exec() != QDialog.Accepted or not database.is_ready():
            return
    win = MainWindow(settings, camera)
    win.show()
    sys.exit(app.exec())
