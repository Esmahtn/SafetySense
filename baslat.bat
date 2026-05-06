@echo off
setlocal
echo =========================================
echo    FABRIKA GUVENLIK AI SISTEMI (OFFLINE)
echo =========================================
echo.

:: Paketler klasörünü kütüphane yoluna ekle
set PYTHONPATH=%CD%;%CD%\paketler;%PYTHONPATH%

echo 1. Ortam kontrol ediliyor...
if exist "paketler" (
    echo [BILGI] 'paketler' klasoru bulundu, yerel kutuphaneler kullaniliyor.
) else (
    echo [UYARI] 'paketler' klasoru bulunamadi! Internet varsa yukleme yapiliyor...
    pip install -r requirements.txt -t paketler
)

echo.
echo 2. Yapay Zeka Sunucusu Baslatiliyor...
start "AI Sunucusu" cmd /c "set PYTHONPATH=%CD%;%CD%\paketler && python server.py"

echo 3. Arayuz (Kontrol Paneli) Baslatiliyor...
cd dashboard
if exist "node_modules" (
    echo [BILGI] 'node_modules' bulundu, NPM yuklemesi atlaniyor.
    start "Kontrol Paneli" cmd /c "npm run dev"
) else (
    echo [UYARI] 'node_modules' bulunamadi! Internet varsa yukleme yapiliyor...
    start "Kontrol Paneli" cmd /c "npm install && npm run dev"
)

echo.
echo Sistem hazirlaniyor... Lutfen bekleyin...
timeout /t 8 >nul
echo.
echo Tarayici otomatik olarak aciliyor...
start http://localhost:5173
pause
