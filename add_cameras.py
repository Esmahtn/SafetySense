#!/usr/bin/env python3
import requests
import json

API_BASE = "http://localhost:5000"

# Eklenecek kameralar
cameras_to_add = [
    {
        "id": "1",
        "name": "Kamera 1 - Port 125",
        "ip": "192.168.12.129",
        "port": "125",
        "username": "admin",
        "password": "admin123",
        "path": "live.sdp"
    },
    {
        "id": "2",
        "name": "Kamera 2 - Port 130",
        "ip": "192.168.12.129",
        "port": "130",
        "username": "admin",
        "password": "admin123",
        "path": "live.sdp"
    }
]

def generate_rtsp(cam):
    """RTSP URL oluştur"""
    from urllib.parse import quote
    username = quote(cam["username"], safe='')
    password = quote(cam["password"], safe='')
    return f"rtsp://{username}:{password}@{cam['ip']}:{cam['port']}/{cam['path']}"

def add_cameras():
    """Kameraları sisteme ekle"""
    try:
        # Mevcut konfigürasyonu al
        print("📡 Mevcut konfigürasyon yükleniyor...")
        res = requests.get(f"{API_BASE}/api/config", timeout=5)
        config = res.json()
        
        print(f"✓ Config yüklendi. Mevcut kameralar: {list(config['cameras'].keys())}")
        
        # Yeni kameraları ekle
        for cam in cameras_to_add:
            cam_id = cam["id"]
            
            if cam_id in config['cameras']:
                print(f"⚠️  Kamera {cam_id} zaten mevcut. Atlanıyor...")
                continue
            
            rtsp_url = generate_rtsp(cam)
            
            config['cameras'][cam_id] = {
                "name": cam["name"],
                "source": rtsp_url,
                "tasks": []
            }
            
            print(f"✓ Kamera {cam_id} eklendi: {cam['name']}")
            print(f"  RTSP: {rtsp_url}")
        
        # Güncellenmiş konfigürasyonu kaydet
        print("\n💾 Konfigürasyon kaydediliyor...")
        save_res = requests.post(f"{API_BASE}/api/config", json=config, timeout=5)
        
        if save_res.status_code == 200:
            print("✅ Tüm kameralar başarıyla eklendi!")
            print(f"\nEklenen kameralar:")
            for cam_id in [c["id"] for c in cameras_to_add]:
                if cam_id in config['cameras']:
                    cam_info = config['cameras'][cam_id]
                    print(f"  • {cam_id}: {cam_info['name']}")
        else:
            print(f"❌ Kaydedilirken hata: {save_res.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Hata: Server bağlantısı kurulamadı!")
        print(f"   Lütfen {API_BASE} adresine erişilebildiğini kontrol edin.")
        print("   Server çalışmıyor olabilir.")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    print("🎥 SafetySense - Kamera Ekleme Aracı")
    print("=" * 50)
    add_cameras()
