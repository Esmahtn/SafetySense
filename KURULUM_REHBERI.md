# SafetySense: Fabrika Güvenlik Sistemi Kurulum ve Kullanım Kılavuzu

Bu belge, sistemin yeni bir bilgisayara taşınması, canlı kameralara bağlanması ve çalışma alanlarının (ROI) ayarlanması için hazırlanmıştır.

## 1. Yeni Bilgisayarda İlk Kurulum
1. **Python Kurulumu:** [python.org](https://www.python.org/) üzerinden en güncel Python'ı kurun. Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin.
2. **Node.js Kurulumu:** Arayüzün çalışması için [nodejs.org](https://nodejs.org/) üzerinden LTS sürümünü kurun.
3. **Sistemi Başlatma:** Klasör içindeki **`baslat.bat`** dosyasına çift tıklayın. Bu dosya eksik kütüphaneleri kuracak ve hem yapay zekayı hem de arayüzü başlatacaktır.
4. **Tarayıcı:** Arayüz otomatik olarak `http://localhost:5173` adresinde açılacaktır.

## 2. Canlı Kameralara Geçiş (Örn: Dahua Kameralar)
Sistemi canlı kamera yayınlarına (RTSP) bağlamak için `server.py` dosyasını en alta kaydırıp şu satırları kendi fabrikanızdaki Dahua kamera bilgilerinizle güncelleyin:

```python
# Dahua Kameralar İçin Standart RTSP Formatı:
# rtsp://kullanici:sifre@ip_adresi:554/cam/realmonitor?channel=1&subtype=0
engine1 = CameraEngine(1, "Ana Koridor", "rtsp://admin:sifre123@192.168.1.50:554/cam/realmonitor?channel=1&subtype=0")
engine2 = PedestrianEngine(2, "Güvensiz Bölge", "rtsp://admin:sifre123@192.168.1.51:554/cam/realmonitor?channel=1&subtype=0")
engine3 = SpeedEngine(3, "Hız Koridoru", "rtsp://admin:sifre123@192.168.1.52:554/cam/realmonitor?channel=1&subtype=0")
```

> **Not (VisDrone'a Geri Dönüş):** Yaya tespitinde şu an kalabalıklar için en iyisi olan `yolov8n-crowdhuman.pt` çalışmaktadır. Eğer eski (uzaktaki çok küçük nesneler için) modele geri dönmek isterseniz; `pedestrian_engine.py` dosyasını açıp 24. satırdaki `YOLO("yolov8n-crowdhuman.pt")` kısmını `YOLO("yolov8n-visdrone.pt")` olarak değiştirmeniz yeterlidir.

## 3. Çalışma Alanlarını (ROI) Ayarlama (Derin Anlatım)
ROI (Region of Interest), yapay zekanın sadece belirli bir alan içinde ihlal aramasını sağlar. Kamera açısı değiştiğinde bu koordinatları güncellemeniz gerekir.

### Koordinatları Nasıl Bulurum?
1. Kameranızdan bir ekran görüntüsü (screenshot) alın.
2. Bu görüntüyü **Paint** programında açın.
3. Farenizi belirlemek istediğiniz köşelerin üzerine getirin. Paint'in sol alt köşesinde `x, y` koordinatlarını göreceksiniz (Örn: 450, 600).

### Koordinatları Nereye Yazarım?
- **Ters Yön ve Hız İçin (`server.py`):** `self.roi_polygon` listesini güncelleyin.
- **Yaya İhlali İçin (`pedestrian_engine.py`):** `self.danger_zone` listesini güncelleyin.

**Örnek ROI Tanımı:**
```python
self.roi_polygon = [
    (100, 200), # Sol Üst
    (1100, 200), # Sağ Üst
    (1100, 700), # Sağ Alt
    (100, 700)   # Sol Alt
]
```
*Not: Alanı kapatmak için en az 3 veya 4 nokta belirlemelisiniz. Sistem bu noktaları birleştirerek bir kapalı alan oluşturur.*

## 4. E-posta Bildirim Ayarları
`mailer.py` dosyasını açarak şu alanları doldurun:
- `SENDER_EMAIL`: Gönderici Gmail adresi.
- `APP_PASSWORD`: Gmail ayarlarından alınan 16 haneli "Uygulama Şifresi".
- `RECEIVER_EMAIL`: Uyarıların gideceği adres.

## 5. Performans Notları (GPU Kullanımı)
Sistem varsayılan olarak işlemci (CPU) üzerinde çalışır. Eğer bilgisayarda NVIDIA ekran kartı varsa, performansı 10 kat artırmak için şu komutu çalıştırın:
`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

## 6. Temizlik ve Taşıma
Sistemi başka bir PC'ye taşırken `violations/` klasörünü ve `violations.db` dosyasını silebilirsiniz. Sistem ilk çalıştığında bunları tertemiz olarak yeniden oluşturacaktır.
