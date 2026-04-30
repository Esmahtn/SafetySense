# 🛡️ SafetySense: AI-Powered Factory Safety Monitoring

SafetySense, endüstriyel tesislerde iş güvenliğini artırmak için geliştirilmiş, gerçek zamanlı nesne tespiti ve ihlal analizi yapan yapay zeka tabanlı bir izleme sistemidir. YOLOv11 mimarisi kullanılarak optimize edilen sistem, kritik bölgelerdeki insan ve araç hareketlerini anlık olarak denetler.

![SafetySense Dashboard](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.14%2B-blue?style=for-the-badge&logo=python)
![YOLOv11](https://img.shields.io/badge/AI-YOLOv11--Large-red?style=for-the-badge)

## 🚀 Öne Çıkan Özellikler

- **Ters Yön Algılama:** Belirlenen koridorlarda araçların sürüş yönünü kontrol eder, hatalı yönelimleri saniyeler içinde tespit eder.
- **Güvenli Bölge İhlali (Pedestrian ROI):** Yasaklı alanlara giren yayaları anlık olarak yakalar ve kırmızı kutularla işaretler.
- **Hız Koridoru Analizi:** Araçların fabrika içi hız sınırlarını aşma durumlarını (km/h) ölçer ve kaydeder.
- **Asenkron Mimari:** Kamera bağlantıları ve model yükleme işlemleri arka planda gerçekleşir; dashboard anında açılır, sistem asla donmaz.
- **Otomatik Bildirim Sistemi:** İhlal anında 10 saniyelik video kaydı oluşturur, ekran görüntüsü alır ve ilgili birimlere otomatik e-posta gönderir.
- **Modern Dashboard:** React ve Vite ile geliştirilmiş, canlı yayın akışını ve ihlal geçmişini gösteren kullanıcı dostu arayüz.

## 🛠️ Teknik Altyapı

- **Görüntü İşleme:** OpenCV, Ultralytics YOLOv11 (Large)
- **Backend:** Flask, Python Threading
- **Frontend:** React, Vite, Tailwind CSS (Dashboard)
- **Veritabanı:** SQLite (İhlal kayıtları ve istatistikler için)
- **Kamera Yönetimi:** Asenkron RTSP akış yönetimi ve otomatik yeniden bağlanma desteği.

## 📦 Kurulum ve Çalıştırma

### 1. Gereksinimler
Sistem Python 3.14+ ve Node.js gerektirir. Gerekli kütüphaneleri kurmak için:

```bash
pip install -r requirements.txt
```

### 2. Canlı Yayını Başlatma
Sistemi tek tıkla ayağa kaldırmak için `baslat.bat` dosyasını kullanabilir veya manuel olarak şu komutları çalıştırabilirsiniz:

```bash
# Backend ve Analiz Motoru
python server.py

# Frontend Dashboard (Dashboard klasörü içinde)
npm run dev
```

## 🎥 Görselleştirme ve Analiz
Sistem her kamera için özel **ROI (Region of Interest)** bölgelerini destekler:
- **Mavi/Sarı Alan:** Araçların trafik kurallarını denetler.
- **Mor/Kırmızı Alan:** Yayaların girmemesi gereken tehlikeli bölgeleri denetler.
- **Maskeleme (Blind Spots):** Yanlış alarmları önlemek için kullanıcı tarafından fare ile seçilen bölgeleri tamamen kapatma özelliği.

## 📜 Lisans
Bu proje endüstriyel güvenlik standartlarına uygun olarak **SafetySense** ekibi tarafından geliştirilmiştir.

---
*SafetySense - Fabrikalar Artık Daha Güvenli.*
