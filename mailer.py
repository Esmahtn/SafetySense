import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ---------------------------------------------------------
# E-POSTA AYARLARI (Burayı kendi mailinize göre doldurun)
# ---------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "sizin_mailiniz@gmail.com"
SENDER_PASSWORD = "gmail_uygulama_sifresi" # Normal şifre değil, 16 haneli uygulama şifresi
TARGET_EMAIL = "isg_uzmani@sirket.com" # Bildirimin gideceği e-posta adresi
# ---------------------------------------------------------

def send_violation_email(cam_name, violation_type, vehicle_id, timestamp, image_path):
    """İhlal durumunda e-posta gönderen fonksiyon."""
    
    # Ayarlar girilmediyse gönderme işlemini atla (test/geliştirme aşaması için)
    if SENDER_EMAIL == "sizin_mailiniz@gmail.com":
        print(f"[MAILER] E-posta ayarları yapılmadığı için bildirim gönderilmedi: {violation_type}")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = f"🚨 DİKKAT: İSG İhlali Tespit Edildi ({violation_type})"
        
        body = f"""
        Merhaba,
        
        Sistem otomatik olarak yeni bir İş Sağlığı ve Güvenliği (İSG) ihlali tespit etti.
        
        Detaylar:
        - Kamera / Bölge: {cam_name}
        - İhlal Türü: {violation_type}
        - Araç / Kişi ID: {vehicle_id}
        - Tarih ve Zaman: {timestamp}
        
        İhlal anına ait kanıt fotoğrafı ektedir. Lütfen kontrol ediniz.
        
        İyi çalışmalar,
        Otomatik İSG Gözlem Sistemi
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Fotoğrafı Ekle
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            msg.attach(image)
        else:
            print(f"[MAILER] Ek dosyası bulunamadı: {image_path}")
            
        # Gönderim işlemi
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"[MAILER] E-posta başarıyla gönderildi: {TARGET_EMAIL}")
        return True
        
    except Exception as e:
        print(f"[MAILER] E-posta gönderilirken hata oluştu: {str(e)}")
        return False

# Test için (Bu dosyayı tek başına çalıştırırsanız çalışır)
if __name__ == "__main__":
    print("Test e-postası gönderiliyor...")
    send_violation_email("Test Kamera", "Test İhlali", 99, "2026-04-24 15:00", "test_foto.jpg")
