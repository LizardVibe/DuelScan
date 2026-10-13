@echo off
rem DuelScan - Einrichtung der Python-Umgebung (einmalig)
rem Sucht ein passendes Python (3.10 - 3.12), legt .venv an und installiert alle Pakete.
setlocal
cd /d "%~dp0"

set "PY="
for %%V in (3.11 3.12 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo  [!] Python 3.10, 3.11 oder 3.12 wurde nicht gefunden.
    echo      Bitte installieren: https://www.python.org/downloads/  ^(Version 3.11 empfohlen^)
    echo      Beim Installieren "Add python.exe to PATH" anhaken.
    echo.
    echo  [!] Python 3.10, 3.11 or 3.12 not found. Please install it from python.org ^(3.11 recommended^).
    echo.
    pause
    exit /b 1
)

echo Verwende / using: %PY%
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv || goto :error
)
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
rem PyTorch in der CPU-Version (deutlich kleiner, keine Grafikkarte noetig)
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error

echo.
echo  Fertig! Starte DuelScan mit start.bat  /  Done! Launch DuelScan with start.bat
echo.
pause
exit /b 0

:error
echo.
echo  [!] Installation fehlgeschlagen / installation failed. Siehe Meldungen oben / see messages above.
pause
exit /b 1
