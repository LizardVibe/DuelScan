@echo off
rem Startet DuelScan, egal aus welchem Ordner (oder per Doppelklick).
rem Beim allerersten Mal wird automatisch install.bat ausgefuehrt.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    call install.bat || exit /b 1
)
".venv\Scripts\python.exe" scan.py %*
if errorlevel 1 pause
