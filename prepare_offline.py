import os
import subprocess
import sys

def prepare():
    print("=== OFFLINE HAZIRLIK ARACI ===")
    print("Bu araç tüm bağımlılıkları 'paketler' klasörüne indirecektir.")
    print("İnternet olan bu bilgisayarda çalıştırın, sonra tüm klasörü diğer PC'ye taşıyın.\n")

    # 1. Python paketlerini indir
    os.makedirs("paketler", exist_ok=True)
    print("1. Python kütüphaneleri indiriliyor (paketler/ içine)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-t", "paketler"])
        print("✅ Python kütüphaneleri hazır.")
    except Exception as e:
        print(f"❌ Python kütüphaneleri indirilirken hata: {e}")

    # 2. Dashboard (NPM) kontrolü
    print("\n2. Kontrol Paneli (NPM) kontrolü...")
    if os.path.exists("dashboard/node_modules"):
        print("✅ 'dashboard/node_modules' zaten mevcut. Taşırken bu klasörü de dahil ettiğinizden emin olun.")
    else:
        print("⚠️ 'dashboard/node_modules' bulunamadı! Lütfen 'cd dashboard && npm install' komutunu çalıştırın.")

    print("\n=== İŞLEM TAMAM ===")
    print("Şimdi 'SafetySense' klasörünü tamamen kopyalayıp diğer bilgisayara taşıyabilirsiniz.")
    print("Diğer bilgisayarda 'baslat.bat' dosyasına tıklamanız yeterli olacaktır.")

if __name__ == "__main__":
    prepare()
