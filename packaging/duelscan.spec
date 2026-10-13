# PyInstaller-Bauplan für DuelScan (Windows, Ordner-Variante)
#   .venv\Scripts\pyinstaller packaging\duelscan.spec --noconfirm
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))
from ygo_scanner.config import APP_NAME  # noqa: E402

# DINOv2 wird zur Laufzeit per torch.hub als Python-Code nachgeladen. Dieser Code nutzt Teile der
# Standardbibliothek/torch, die unser eigener Code nicht importiert -> vorsorglich mitnehmen.
hidden = collect_submodules("torch.nn") + ["logging", "enum", "functools", "math", "typing", "warnings",
                                           "urllib.request", "zipfile", "uuid", "importlib.util"]

a = Analysis(
    [str(ROOT / "scan.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "ygo_scanner" / "assets"), "ygo_scanner/assets")],
    hiddenimports=hidden,
    excludes=["torchvision", "tkinter", "matplotlib", "IPython", "pytest", "PySide6.QtWebEngineCore",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME, console=False,
          icon=str(ROOT / "ygo_scanner" / "assets" / "icon.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)
