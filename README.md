# 🛡️ SafetySense: Yapay Zeka Destekli Endüstriyel Güvenlik Sistemi

<p align="center">
  <img src="https://img.shields.io/badge/AI-YOLOv11-eb1616?style=for-the-badge&logo=pytorch" alt="YOLOv11">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

**SafetySense**, endüstriyel tesislerde iş kazalarını minimize etmek ve operasyonel güvenliği otonom hale getirmek için geliştirilmiş, gerçek zamanlı bir bilgisayarlı görü (Computer Vision) çözümüdür. 

Bu proje, bir staj programı kapsamında **1 ay gibi kısa bir sürede** sıfırdan mimari tasarımı yapılmış, AI motorları optimize edilmiş ve uçtan uca (end-to-end) bir ürün haline getirilmiştir.

---

## 🚀 Öne Çıkan Özellikler

### 🏎️ Akıllı Hız Takibi (Speed Detection)
Belirlenen koridorlarda araçların (forklift, kamyon vb.) hızlarını anlık hesaplar. Perspektif düzeltme katsayıları ve ROI (Region of Interest) kontrolü ile yüksek doğruluk sağlar.

### 🚶 Yasaklı Bölge Denetimi (Pedestrian Entry)
İş makinelerinin çalıştığı tehlikeli alanlara yaya girişlerini anında tespit eder. **Custom Masking** özelliği ile sadece kritik alanları izleyerek yanlış alarmları önler.

### 🔄 Ters Yön İhlali (Wrong Way Detection)
Trafik akışının tek yönlü olduğu alanlarda, akışa zıt hareket eden nesneleri saniyeler içinde fark eder.

### 📧 Otomatik Kanıt ve Bildirim Sistemi
İhlal anında sistem:
- **Screenshot:** Tam ekran ihlal karesini kaydeder.
- **Auto-Crop:** İhlal yapan nesneyi otomatik yakınlaştırarak (yakın çekim) ayrı bir görsel oluşturur.
- **E-Posta:** Yetkililere görsellerle birlikte anlık SMTP bildirimi gönderir.
- **Database:** Tüm verileri SQLite üzerinde tarihsel olarak saklar.

---

## 🛠️ Teknik Mimari: "Altın Standart" Yaklaşımı

Sistem, endüstriyel sahalardaki zorlu koşullar (ışık değişimi, kalabalık, lag) düşünülerek şu tekniklerle güçlendirilmiştir:

1.  **Async Stream Management:** RTSP akışları ana işlem döngüsünü yavaşlatmadan asenkron olarak işlenir.
2.  **M-out-of-N Hysteresis:** Bir ihlalin doğrulanması için nesnenin belirli bir kare sayısı boyunca (örn: 8 kareden 3'ü) bölgede olması şart koşulur (Yanlış alarm filtresi).
3.  **Bottom-Center Triggering:** Nesne tespiti, kutunun (bbox) alt-orta noktasına göre yapılır; bu sayede kamera perspektifinden kaynaklanan hatalar minimize edilir.
4.  **Spatial Cooldown (Alarm Ledger):** Aynı bölgede kısa sürede mükerrer alarm oluşmasını engelleyen akıllı bekleme süresi algoritması.

---

## 📦 Taşınabilirlik ve Çevrimdışı Çalışma

SafetySense, fabrikaların kapalı devre (Air-Gapped) sistemleri düşünülerek tasarlanmıştır:
- **Portable Python:** Sisteme gömülü Python ortamı sayesinde kurulum gerektirmeden çalışır.
- **Offline Dashboard:** Tüm kütüphaneler ve fontlar yerelleştirilmiştir; internet bağlantısı gerektirmez.
- **Tek Tıkla Başlatma:** `baslat.bat` ile tüm servisler (Backend + Frontend) otomatik ayağa kalkar.

---

## 🏗️ Teknoloji Yığını

- **AI Framework:** Ultralytics YOLOv11 (Detection & Tracking)
- **Tracking:** BoT-SORT (Multi-Object Tracking)
- **Image Processing:** OpenCV
- **Backend:** Python Flask
- **Frontend:** React.js, Vite, TailwindCSS
- **Database:** SQLite

---

## ⚙️ Kurulum

```bash
# 1. Depoyu klonlayın
git clone https://github.com/Esmahtn/SafetySense.git

# 2. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 3. Sistemi başlatın
python server.py
```

---

## 🛠️ Yol Haritası (Roadmap)

Sistemin gelecekteki geliştirmeleri şunları içermektedir:
- **Dinamik Ayarlar Paneli:** Kamera IP'leri ve AI parametrelerinin web arayüzü üzerinden canlı olarak değiştirilmesi.
- **Görsel ROI Kalibrasyonu:** Kullanıcının dashboard üzerinden alan çizerek (polygon drawing) ihlal bölgelerini otomatik olarak güncellemesi.
- **Gelişmiş İstatistik Paneli:** Günlük/Haftalık ihlal trendlerinin grafiklerle görselleştirilmesi.

---
*Bu proje, iş sağlığı ve güvenliği (İSG) standartlarını yapay zeka ile bir üst seviyeye taşımak amacıyla geliştirilmiştir.*
