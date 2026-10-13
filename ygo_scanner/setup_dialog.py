"""Einrichtungs-Assistent: lädt Kartendaten, Bilder, Indizes und Preise mit Fortschrittsanzeige.

Wird beim ersten Start automatisch gezeigt und später über die Einstellungen
("Neue Karten & Bilder herunterladen") zum Aktualisieren verwendet.
"""
import threading
import time

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from . import database
from .config import APP_NAME
from .i18n import t


class _Signals(QObject):
    progress = Signal(str, int, int)
    finished = Signal(str, str)      # Ergebnis ("done" | "cancelled" | "failed"), Fehlermeldung


class SetupDialog(QDialog):
    def __init__(self, parent=None, update: bool = False):
        super().__init__(parent)
        self.update_mode = update
        self.setWindowTitle(f"{APP_NAME} – {t('setup_title')}")
        self.setMinimumWidth(560)
        self.cancel_event = threading.Event()
        self.running = False
        self.result_state = ""
        self._stage_start: dict[str, tuple[float, int]] = {}

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(22, 22, 22, 22)
        title = QLabel(t("setup_welcome", app=APP_NAME) if not update else t("update_db_btn"), objectName="name")
        intro = QLabel(t("setup_update_intro") if update else t("setup_intro"), wordWrap=True)
        intro.setTextFormat(Qt.RichText)
        self.stage = QLabel("", objectName="sub", wordWrap=True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.hide()
        disclaimer = QLabel(t("disclaimer", app=APP_NAME), objectName="sub", wordWrap=True)
        for w in (title, intro, self.bar, self.stage, disclaimer):
            lay.addWidget(w)

        row = QHBoxLayout()
        row.addStretch()
        self.start_btn = QPushButton(t("setup_start"), objectName="primary")
        self.cancel_btn = QPushButton(t("cancel"))
        self.start_btn.clicked.connect(self.start)
        self.cancel_btn.clicked.connect(self._cancel_clicked)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.start_btn)
        lay.addLayout(row)

        self.sig = _Signals()
        self.sig.progress.connect(self._on_progress)
        self.sig.finished.connect(self._on_finished)

    # ---------------------------------------------------------------- Ablauf
    def start(self):
        if self.result_state == "done":
            self.accept()
            return
        self.running = True
        self.cancel_event.clear()
        self.start_btn.setEnabled(False)
        self.bar.show()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            database.setup(progress=self.sig.progress.emit, cancel=self.cancel_event)
            self.sig.finished.emit("done", "")
        except database.Cancelled:
            self.sig.finished.emit("cancelled", "")
        except Exception as e:  # noqa: BLE001
            self.sig.finished.emit("failed", str(e))

    def _on_progress(self, stage: str, done: int, total: int):
        steps = len(database.STAGES)
        step = database.STAGES.index(stage) + 1 if stage in database.STAGES else 1
        frac = done / total if total else 1.0
        self.bar.setValue(int(((step - 1) + frac) / steps * 1000))
        text = t("stage_progress", step=step, steps=steps, stage=t(f"stage_{stage}"), done=done, total=total)
        # Restzeit für die laufende Etappe schätzen
        now = time.time()
        if stage not in self._stage_start or done < self._stage_start[stage][1]:
            self._stage_start[stage] = (now, done)
        t0, d0 = self._stage_start[stage]
        if total and done > d0 and now - t0 > 5:
            rate = (done - d0) / (now - t0)
            minutes = max(1, round((total - done) / rate / 60))
            text += "  ·  " + t("eta", min=minutes)
        self.stage.setText(text)

    def _on_finished(self, state: str, msg: str):
        self.running = False
        self.result_state = state
        self.start_btn.setEnabled(True)
        if state == "done":
            self.bar.setValue(1000)
            self.stage.setText(t("setup_done"))
            self.start_btn.setText(t("setup_open_app") if not self.update_mode else t("close"))
            self.cancel_btn.hide()
        elif state == "cancelled":
            self.stage.setText(t("setup_cancelled"))
            self.start_btn.setText(t("setup_start"))
        else:
            self.stage.setText(t("setup_failed", msg=msg))
            self.start_btn.setText(t("setup_start"))

    def _cancel_clicked(self):
        if self.running:
            self.cancel_event.set()
            self.stage.setText(t("setup_cancelling"))
        else:
            self.reject()

    def closeEvent(self, e):
        if self.running:
            self.cancel_event.set()
        super().closeEvent(e)
