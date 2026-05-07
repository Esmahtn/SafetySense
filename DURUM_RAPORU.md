# SafetySense - Mevcut Durum Raporu (2026-05-07)

Bu belge, projenin mevcut teknik durumunu ve tamamlanmış özelliklerini özetlemektedir.

## 🟢 Tamamlanan Özellikler
- **AI Tespit Motorları:**
  - **Ters Yön Tespiti:** Araçların akış yönüne zıt hareketleri başarıyla tespit ediliyor.
  - **Yaya İhlali:** Yasaklı bölgelere giren yayalar maskeleme ve ROI kontrolü ile izleniyor.
  - **Hız Takibi:** Araç hızları belirlenen koridorda hesaplanabiliyor.
- **Backend & Entegrasyon:**
  - **Flask Sunucusu:** Tüm motorları asenkron yönetiyor ve canlı yayın sağlıyor.
  - **E-Posta Bildirimi:** İhlal anında fotoğraf, kırpılmış görsel (crop) ve video ekli mailler gönderiliyor.
  - **Veritabanı:** İhlaller SQLite üzerinde kalıcı olarak saklanıyor.
- **Portabilite:**
  - `python_bin` klasörü ile bağımsız (portable) çalışma yeteneği.
  - `baslat.bat` ile tek tıkla başlatma.

## 🟡 Mevcut Yapılandırma
- Kamera kaynakları ve AI parametreleri `config.py` ve `ai_config.py` dosyaları üzerinden yönetilmektedir.
- Dashboard, `dashboard/dist` klasörü altındaki statik dosyalar üzerinden sunulmaktadır.

## 🔴 Gelecek Planları (TODO)
- **Ayarlar Paneli:** Kamera IP'leri ve ROI koordinatlarının dashboard üzerinden dinamik olarak değiştirilmesi.
- **Dinamik Kalibrasyon:** Kullanıcının arayüzden alan çizerek koordinatları otomatik güncellemesi.

---
*Bu rapor sistemin mevcut durumunu dökümante etmek amacıyla oluşturulmuştur.*
