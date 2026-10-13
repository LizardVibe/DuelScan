@echo off
rem Baut dist\DuelScan (PyInstaller) und daraus packaging\Output\DuelScan-Setup-x.y.z.exe (Inno Setup 6).
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\pyinstaller.exe" (
    ".venv\Scripts\python.exe" -m pip install pyinstaller || goto :error
)
".venv\Scripts\pyinstaller.exe" packaging\duelscan.spec --noconfirm --log-level WARN || goto :error

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [!] Inno Setup 6 nicht gefunden: https://jrsoftware.org/isdl.php  ^(oder: winget install JRSoftware.InnoSetup^)
    goto :error
)
"%ISCC%" packaging\duelscan.iss || goto :error

echo.
echo Fertig: packaging\Output\
exit /b 0

:error
echo Build fehlgeschlagen.
exit /b 1
