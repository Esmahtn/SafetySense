@echo off
setlocal
title SafetySense AI - Canli Yayin
echo ===================================================
echo    SAFETY SENSE AI - CANLI YAYIN SISTEMI
echo ===================================================
echo.

:: Dosyanin bulundugu dizini baz al (USB ile tasinsada calisir)
cd /d %~dp0

:: Tasinabilir Python yoksa hata ver
if not exist "python_bin\python.exe" (
    echo [HATA] python_bin klasoru bulunamadi!
    echo Lutfen sistem yoneticinizle iletisime gecin.
    pause
    exit /b
)

echo [1/2] Yapay Zeka Sunucusu Baslatiliyor...
echo       Lutfen bekleyin, modeller yukleniyor (~10 saniye)...
echo.

:: python_bin icindeki Python ile server.py calistir
start "SafetySense Sunucusu" cmd /k "python_bin\python.exe server.py"

echo [2/2] Arayuz hazirlaniyor...
timeout /t 10 >nul

:: Flask uzerinden sunulan arayuzu ac
start http://localhost:5000

echo.
echo ===================================================
echo  Sistem Calisiyor!
echo  - Siyah sunucu penceresini KAPATMAYIN.
echo  - Kamera IP/sifre ayari: config.py
echo  - AI hassasiyet ayari:   ai_config.py
echo ===================================================
