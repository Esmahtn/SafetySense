@echo off
echo =========================================
echo    FABRIKA GUVENLIK AI SISTEMI BASLIYOR
echo =========================================
echo.
echo 1. Kutuphaneler kontrol ediliyor...
pip install -r requirements.txt >nul 2>&1
echo Kutuphaneler tamam.
echo.
echo 2. Yapay Zeka Sunucusu (Arka Plan) Baslatiliyor...
start "AI Sunucusu" cmd /c "python server.py"

echo 3. Arayuz (Kontrol Paneli) Baslatiliyor...
cd dashboard
start "Kontrol Paneli" cmd /c "npm install && npm run dev"

echo.
echo Sistem hazirlaniyor... Lutfen bekleyin...
timeout /t 5 >nul
echo.
echo Tarayici otomatik olarak aciliyor... Acilan siyah ekranlari KAPATMAYIN!
start http://localhost:5173
pause
