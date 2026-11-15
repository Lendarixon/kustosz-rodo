@echo off
cd /d "%~dp0"
echo === Instalacja Linda Kustosz RODO ===
python tools\setup_kustosz.py %*
if errorlevel 1 (
    echo Blad instalacji. Sprawdz czy Python 3.10+ jest zainstalowany.
    pause
    exit /b 1
)
echo.
echo Uruchamiam aplikacje...
python app.py
pause
