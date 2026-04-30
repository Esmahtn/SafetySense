# 🛡️ Fabrika İş Güvenliği İzleme Sistemi (AI Safety)

Bu proje, fabrikalardaki güvenlik kameralarını "akıllı" hale getiren bir yapay zeka sistemidir. Basitçe anlatmak gerekirse; kameraları 7/24 izleyen yapay zeka tabanlı bir dijital göz gibi çalışır ve tehlikeli bir durum gördüğünde anında uyarı verir.

## 🤔 Bu Sistem Ne İşe Yarar?

Fabrika ortamında her an her şey olabilir. Bu yazılım şu 3 ana tehlikeyi otomatik olarak takip eder:

1.  **Yanlış Yöne Giden Araçlar:** Forklift veya kamyonlar girmemesi gereken bir yöne giderse sistem bunu anında fark eder.
2.  **Yasaklı Bölgeye Giren İnsanlar:** İşçilerin girmesinin tehlikeli olduğu (makine parkurları vb.) alanlara birisi girdiğinde sistem kırmızı kutuyla o kişiyi işaretler ve alarm verir.
3.  **Hız İhlali:** Fabrika içinde hız sınırını aşan araçları tespit eder.

## 🌟 Neden Bu Sistemi Kullanmalıyız?

-   **Yorulmaz:** İnsan gözü bir süre sonra ekrana bakarken yorulur ama bu yapay zeka asla uyumaz, dikkati dağılmaz.
-   **Anında Kanıt Sunar:** Bir ihlal olduğunda o anın 10 saniyelik videosunu ve fotoğrafını çeker, e-posta ile yöneticiye gönderir.
-   **Görünmez Kazaları Önler:** İnsanların ve araçların birbirine çok yakın olduğu kör noktaları denetler.

## 🚀 Nasıl Çalıştırılır?

Hiç bilmeyen biri için kurulum adımları:

1.  Bilgisayarınıza gerekli kütüphaneleri kurun: `pip install -r requirements.txt`
2.  Sistemi başlatmak için ana klasördeki `baslat.bat` dosyasına çift tıklayın.
3.  Karşınıza çıkan panel üzerinden kameraları canlı olarak izlemeye başlayın.

## 🛠️ Teknik Detaylar (Meraklısına)

-   **Göz (Yapay Zeka):** YOLOv11 mimarisi kullanıldı (Nesneleri tanıyan beyin).
-   **Hız:** Saniyede onlarca kareyi analiz edebilen yüksek performanslı bir yapı.
-   **Kayıt:** Tüm ihlaller bir veritabanında saklanır ve panel üzerinden geçmişe dönük izlenebilir.

---
*Bu proje, fabrikalarda iş kazalarını sıfıra indirmek ve daha güvenli bir çalışma ortamı oluşturmak amacıyla geliştirilmiştir.*
