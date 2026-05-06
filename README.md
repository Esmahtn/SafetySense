# 🛡️ SafetySense: Yapay Zeka Destekli Endüstriyel Güvenlik Sistemi

<p align="center">
  <img src="https://img.shields.io/badge/AI-YOLOv11-eb1616?style=for-the-badge&logo=pytorch" alt="YOLOv11">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

**SafetySense**, endüstriyel tesislerde ve fabrikalarda iş kazalarını minimize etmek, operasyonel güvenliği en üst düzeye çıkarmak için tasarlanmış, gerçek zamanlı bir bilgisayarlı görü (Computer Vision) çözümüdür. RTSP üzerinden canlı kamera akışlarını analiz ederek otonom bir denetim mekanizması sağlar.

---

## 🚀 Öne Çıkan Özellikler

### 🏎️ Akıllı Hız Takibi (Speed Detection)
Fabrika içi belirlenen koridorlarda araçların (forklift, kamyon vb.) hızlarını anlık olarak hesaplar. Belirlenen limit aşıldığında plaka/araç bazlı ihlal kaydı oluşturur.

### 🚶 Yasaklı Bölge İhlali (Pedestrian Entry)
İş makinelerinin çalıştığı veya tehlikeli olan "Girilmez" bölgelere yaya girişlerini anında tespit eder. ROI (Region of Interest) maskeleme ile sadece kritik alanları izler.

### 🔄 Ters Yön Denetimi (Wrong Way Detection)
Trafik akışının tek yönlü olduğu alanlarda, akışa zıt hareket eden araçları saniyeler içinde fark eder ve alarm tetikler.

### 📧 Anlık Bildirim ve Raporlama
İhlal anında otomatik olarak:
- Ekran görüntüsü (Screenshot) alır.
- 10 saniyelik ihlal videosu kaydeder.
- Yetkililere e-posta ile anlık bildirim gönderir.
- Veritabanına (SQLite) kalıcı olarak işler.

---

## 🛠️ Teknoloji Yığını

Sistem, modern ve yüksek performanslı teknolojiler üzerine inşa edilmiştir:

-   **Yapay Zeka Mimari:** [Ultralytics YOLOv11](https://github.com/ultralytics/ultralytics) (Nesne Tespiti ve Segmentasyon).
-   **Nesne Takibi:** [BoT-SORT](https://github.com/NirAharon/BoT-SORT) (ID tutarlılığı ve hareket analizi).
-   **Görüntü İşleme:** OpenCV (Yüksek performanslı frame işleme).
-   **Backend:** Python Flask & Flask-CORS (Veri API ve Stream yönetimi).
-   **Frontend:** React.js, Vite, TailwindCSS (Modern ve hızlı kullanıcı arayüzü).
-   **Veri Yönetimi:** SQLite (İhlal kayıtları ve sistem logları).
-   **İletişim:** SMTP (E-posta entegrasyonu).

---

## 🏗️ Sistem Mimarisi

Sistem, **"Altın Standart"** adını verdiğimiz bir stabilite mimarisiyle çalışır:

1.  **Async Camera Stream:** RTSP akışları ana işlem döngüsünü yavaşlatmadan asenkron olarak okunur.
2.  **Bottom-Center Triggering:** İhlal tetiklemeleri, nesne kutusunun alt-orta noktasına göre yapılır (Perspektif hatasını minimize eder).
3.  **M-out-of-N Hysteresis:** Yanlış alarmları önlemek için bir ihlalin doğrulanması için belirli bir kare sayısı (örn: 8 kareden 3'ü) şart koşulur.
4.  **Spatial Cooldown:** Aynı nesne için tekrar eden alarmları engelleyen akıllı bekleme süresi (Alarm Ledger).

---

## ⚙️ Kurulum ve Başlatma

Sistemi yerel makinenizde çalıştırmak için:

1.  **Bağımlılıkları Kurun:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Frontend Hazırlığı:**
    ```bash
    cd dashboard
    npm install
    npm run build
    cd ..
    ```

3.  **Sistemi Başlatın:**
    `baslat.bat` dosyasına çift tıklayın veya:
    ```bash
    python main.py
    ```

---

## 📊 Dashboard

Sistemle birlikte gelen web arayüzü üzerinden:
- Kameraları **canlı** olarak izleyebilir,
- Geçmiş ihlal kayıtlarını filtreleyebilir,
- İhlal anına ait görsellere ve videolara ulaşabilirsiniz.

---

*Bu proje, iş sağlığı ve güvenliği (İSG) standartlarını yapay zeka ile bir üst seviyeye taşımak için geliştirilmiştir.*
