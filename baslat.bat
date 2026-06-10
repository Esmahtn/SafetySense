@echo off
setlocal
title SafetySense AI - Canli Yayin
echo ===================================================
echo    SAFETY SENSE AI - CANLI YAYIN SISTEMI
echo ===================================================
echo.

:: Dosyanin bulundugu dizini baz al (USB ile tasinsada calisir)
cd /d %~dp0

:: Python yolu belirle: önce python_bin, sonra sistem PATH
set "PYTHON_EXE="
if exist "python_bin\python.exe" (
    set "PYTHON_EXE=python_bin\python.exe"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYTHON_EXE=python.exe"
        echo [UYARI] python_bin klasoru bulunamadi, sistem Python kullaniliyor.
    ) else (
        echo [HATA] python_bin klasoru bulunamadi!
        echo Lutfen sistem yoneticinizle iletisime gecin.
        echo Python yuklu degilse https://www.python.org/downloads/ adresinden Python 3.x indirip kurun.
        pause
        exit /b
    )
)

:: React/Vite dashboard build var mi? Yoksa bir kereye mahsus kur ve derle.
if not exist "dashboard\dist\index.html" (
    echo [UYARI] dashboard/dist bulunamadi; once frontend build ediliyor...
    where npm >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [HATA] Node.js veya npm bulunamadi.
        echo Lütfen sadece once Node.js'i yukleyin ve PATH'e ekleyin.
        echo https://nodejs.org adresinden Node.js 18+ indirip kurun.
        pause
        exit /b
    )
    cd dashboard
    if not exist "node_modules" (
        echo [UYARI] node_modules klasoru bulunamadi; paketler yukleniyor...
        npm install
        if %ERRORLEVEL% neq 0 (
            echo [HATA] npm install basarisiz oldu.
            pause
            exit /b
        )
    )
    npm run build
    if %ERRORLEVEL% neq 0 (
        echo [HATA] frontend build islemi basarisiz oldu.
        pause
        exit /b
    )
    cd ..
)

echo [1/2] Yapay Zeka Sunucusu Baslatiliyor...
echo       Lutfen bekleyin, modeller yukleniyor (~10 saniye)...
echo.

:: Python ile server.py calistir
start "SafetySense Sunucusu" cmd /k "%PYTHON_EXE% server.py"

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
