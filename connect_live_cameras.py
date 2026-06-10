#!/usr/bin/env python3
import requests
import json
from urllib.parse import quote

API_BASE = "http://localhost:5000"

# Güncellenecek kameralar
cameras_config = {
    "1": {
        "name": "Kamera 1 - Kanal 125",
        "ip": "192.168.12.129",
        "channel": "125",
        "username": "admin",
        "password": "admin123",
        "path": "live.sdp"
    },
    "2": {
        "name": "Kamera 2 - Kanal 130",
        "ip": "192.168.12.129",
        "channel": "130",
        "username": "admin",
        "password": "admin123",
        "path": "live.sdp"
    }
}

def generate_rtsp(ip, channel, username, password, path):
    """RTSP URL oluştur - Port sabit 554"""
    user_encoded = quote(username, safe='')
    pass_encoded = quote(password, safe='')
    return f"rtsp://{user_encoded}:{pass_encoded}@{ip}:554/{channel}/{path}"

def update_cameras():
    """Kameraları canlı RTSP akışlarına bağla"""
    try:
        print("📡 Mevcut konfigürasyon yükleniyor...\n")
        res = requests.get(f"{API_BASE}/api/config", timeout=5)
        config = res.json()
        
        # Kameraları güncelle
        for cam_id, cam_info in cameras_config.items():
            if cam_id not in config['cameras']:
                print(f"⚠️  Kamera {cam_id} bulunamadı. Atlanıyor...")
                continue
            
            rtsp_url = generate_rtsp(
                cam_info["ip"],
                cam_info["channel"],
                cam_info["username"],
                cam_info["password"],
                cam_info["path"]
            )
            
            # Görevleri koru, kaynağı güncelle
            old_tasks = config['cameras'][cam_id].get('tasks', [])
            
            config['cameras'][cam_id] = {
                "name": cam_info["name"],
                "source": rtsp_url,
                "tasks": old_tasks
            }
            
            print(f"✅ Kamera {cam_id} güncellendi:")
            print(f"   📝 Ad: {cam_info['name']}")
            print(f"   🌐 IP: {cam_info['ip']}:554")
            print(f"   📺 Kanal: {cam_info['channel']}")
            print(f"   👤 Kullanıcı: {cam_info['username']}")
            print(f"   🔒 Şifre: {'*' * len(cam_info['password'])}")
            print(f"   📹 RTSP: {rtsp_url}")
            print(f"   💾 Görev sayısı: {len(old_tasks)} (korundu)")
            print()
        
        # Güncellenmiş konfigürasyonu kaydet
        print("💾 Sunucuya kaydediliyor...")
        save_res = requests.post(f"{API_BASE}/api/config", json=config, timeout=5)
        
        if save_res.status_code == 200:
            print("\n✅ Tüm kameralar başarıyla güncellendi!")
            print("\n🎥 Kameralar artık canlı akış için hazır!")
        else:
            print(f"❌ Kaydedilirken hata: {save_res.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Hata: Server bağlantısı kurulamadı!")
        print(f"   Server adres: {API_BASE}")
        print("   Lütfen server'ın çalıştığını kontrol edin.")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎥 SafetySense - Canlı IP Kamera Bağlantısı")
    print("=" * 60)
    print()
    update_cameras()
