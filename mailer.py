import smtplib
import os
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders

# ---------------------------------------------------------
# E-POSTA AYARLARI — .env dosyasından okunur
# ---------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv kurulu değilse ortam değişkenlerini doğrudan okur

SMTP_SERVER   = os.getenv("SMTP_SERVER",   "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL  = os.getenv("SENDER_EMAIL",  "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
TARGET_EMAIL  = os.getenv("TARGET_EMAIL",  "")
# ---------------------------------------------------------


def send_violation_email(cam_name, violation_type, vehicle_id, timestamp, image_path, video_path=None, crop_path=None):
    """İhlal durumunda resim, crop (yakınlaştırma) ve video ekli e-posta gönderir (arka planda çalışır)."""
    thread = threading.Thread(
        target=_send,
        args=(cam_name, violation_type, vehicle_id, timestamp, image_path, video_path, crop_path),
        daemon=True
    )
    thread.start()


def _send(cam_name, violation_type, vehicle_id, timestamp, image_path, video_path, crop_path):
    if SENDER_EMAIL == "sizin_mailiniz@gmail.com":
        print(f"[MAILER] E-posta ayarları yapılmadı, gönderilmedi.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = f"🚨 İSG İhlali: {violation_type} - {cam_name}"

        body = f"""Merhaba,

Sistem bir İSG ihlali tespit etti.

📍 Kamera   : {cam_name}
⚠️  İhlal    : {violation_type}
🆔 ID        : {vehicle_id}
🕐 Zaman    : {timestamp}

İhlal anı fotoğrafı ve kısa video kaydı ektedir.

Otomatik İSG Gözlem Sistemi
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Fotoğraf ekle
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img = MIMEImage(f.read(), name=os.path.basename(image_path))
            msg.attach(img)
            
        # Yakınlaştırılmış Fotoğraf (Crop) ekle
        if crop_path and os.path.exists(crop_path):
            with open(crop_path, 'rb') as f:
                crop = MIMEImage(f.read(), name=os.path.basename(crop_path))
            msg.attach(crop)

        # Video ekle
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as f:
                vid = MIMEBase('application', 'octet-stream')
                vid.set_payload(f.read())
            encoders.encode_base64(vid)
            vid.add_header('Content-Disposition', 'attachment',
                           filename=os.path.basename(video_path))
            msg.attach(vid)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"[MAILER] OK E-posta gönderildi -> {TARGET_EMAIL}")

    except Exception as e:
        print(f"[MAILER] HATA: {e}")


if __name__ == "__main__":
    print("Test e-postası gönderiliyor...")
    send_violation_email("Test Kamera", "Test İhlali", 99, "2026-04-29 09:18", "test_foto.jpg")
