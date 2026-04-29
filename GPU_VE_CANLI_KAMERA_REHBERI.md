# 🚀 SafetySense: GPU ve Canlı Kamera Kurulum Rehberi

Bu rehber, projenin GPU (NVIDIA Ekran Kartı) olan bir bilgisayara taşınması ve gerçek IP kameralara bağlanması için gereken adımları içerir.

## 1. Donanım Hazırlığı (GPU Aktivasyonu)
Yeni bilgisayarda ekran kartının gücünü kullanmak için terminale şu komutu yazarak GPU destekli Torch kütüphanesini kurun:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 2. Canlı Kameralara Bağlanma
`server.py` dosyasının en altındaki (satır ~300) kamera tanımlarını gerçek IP kamera adreslerinizle (RTSP) değiştirin:

```python
# Örnek Kullanım:
engine1 = CameraEngine(1, "Ana Koridor", "rtsp://admin:sifre@192.168.1.50:554/stream1")
engine2 = PedestrianEngine(2, "Yaya Yolu", "rtsp://admin:sifre@192.168.1.51:554/stream1")
engine3 = SpeedEngine(3, "Hiz Bolgesi", "rtsp://admin:sifre@192.168.1.52:554/stream1")
```

## 3. Performans ve Kalite Ayarları (GPU İçin)
Ekran kartınız olduğu için çözünürlüğü ve model kalitesini artırabilirsiniz. 

### A. Çözünürlüğü Artırma (imgsz)
`server.py`, `pedestrian_engine.py` ve `speed_engine.py` içindeki `imgsz=320` değerlerini şu şekilde yükseltin:
- **Orta Kalite:** `imgsz=640`
- **Yüksek Kalite:** `imgsz=960` veya `1280`

### B. Modeli Güçlendirme (Daha iyi tespit)
Daha keskin tespitler için `yolo11n.pt` yerine şu modelleri kullanabilirsiniz:
- `yolo11s.pt` (Small - Çok iyi denge)
- `yolo11m.pt` (Medium - Profesyonel tespit)

**Değiştirilecek yer:** `__init__` fonksiyonu içindeki `YOLO("yolo11n.pt")` satırı.

### C. Her Kareyi İşleme (Kayıpsız Takip)
GPU hızlı olduğu için kare atlamasına gerek yoktur. Tüm motorlardaki şu satırı güncelleyin:
```python
# simulate_live=True -> False yapın
self.cap = SmartCamera(source, simulate_live=False)
```

## 4. ROI (Alan) Kalibrasyonu
Kamera açısı değiştiği için `server.py` içindeki `self.roi_polygon` koordinatlarını yeni görüntüye göre güncellemeniz gerekecektir.
- Görüntüden screenshot alın.
- Paint ile koordinatları (x, y) bulun.
- Koddaki listeye yazın.

---
**Önemli Not:** Değişiklik yaptıktan sonra her zaman `baslat.bat` ile sistemi yeniden başlatın.
