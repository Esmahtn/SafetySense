# =========================================================
# AI VE HIZ KALİBRASYON AYARLARI (ai_config.py)
# =========================================================

# 0. MODEL SEÇİMİ
# ---------------------------------------------------------
# yolo11n.pt (Nano) - En hızlı, en düşük doğruluk
# yolo11s.pt (Small) - Hızlı, orta doğruluk
# yolo11m.pt (Medium) - Orta hız, yüksek doğruluk
MODEL_NAME = "yolo11n.pt"

# 1. HIZ TESPİT AYARLARI (HOMOGRAPHY TABANLI)
# ---------------------------------------------------------
# Homography için görüntü noktaları (piksel koordinatları) - KAMERANIZA GÖRE AYARLAYIN
# Sol-alt, Sağ-alt, Sağ-üst, Sol-üst sırasıyla
HOMOGRAPHY_IMAGE_POINTS = [
    [100, 450],   # Sol-alt
    [700, 450],   # Sağ-alt  
    [700, 100],   # Sağ-üst
    [100, 100]    # Sol-üst
]

# Homography için gerçek dünya noktaları (metre koordinatları)
# Sol-alt (0,0), Sağ-alt (genişlik,0), Sağ-üst (genişlik,uzunluk), Sol-üst (0,uzunluk)
HOMOGRAPHY_WORLD_POINTS = [
    [0, 0],       # Sol-alt (başlangıç noktası)
    [4, 0],       # Sağ-alt (4 metre genişlik)
    [4, 20],      # Sağ-üst (20 metre uzunluk)
    [0, 20]       # Sol-üst
]

MIN_SPEED_LIMIT = 25.0     # İhlal sayılması için gereken minimum hız (KM/H)
ENABLE_SPEED_DETECTION = True # Hız tespitini aç/kapat

# HESAPLAMA AYARLARI
MIN_TRACKING_FRAMES = 5     # Minimum takip frame sayısı (altı: güvenilmez) - DÜŞÜRÜLDÜ
CONFIDENT_TRACKING_FRAMES = 10  # Güvenilir hız için minimum frame - DÜŞÜRÜLDÜ
MAX_MISSING_FRAMES = 3      # Tespit kaybı toleransı (frame) - DÜŞÜRÜLDÜ
SPEED_SMOOTHING_WINDOW = 3  # Moving average pencere boyutu - DÜŞÜRÜLDÜ

# 2. DOĞRULUK VE TESPİT AYARLARI (YOLO)
# ---------------------------------------------------------
YOLO_CONF_THRESHOLD = 0.35 # Güven eşiği (0.0 - 1.0 arası). Artırırsanız yanlış alarm azalır.
YOLO_IMG_SIZE = 480      # İşleme çözünürlüğü. 640 standarttır, düşürürseniz hızlanır ama doğruluk azalır.
HYSTERESIS_FRAME_COUNT = 8 # Son kaç kareye bakılacağı
HYSTERESIS_CONFIRM_COUNT = 3 # Kaç karede nesne görülürse onaylanacağı

# 3. HAREKETSİZ NESNE FİLTRESİ (STATIONARY FILTER)
# ---------------------------------------------------------
STATIONARY_PIXEL_LIMIT = 5 # Nesne bu pikselden az hareket ediyorsa "duruyor" sayılır
STATIONARY_FRAME_LIMIT = 10 # Kaç frame boyunca durursa "Sabit Nesne" (Hata) kabul edilir

# 4. SOĞUMA SÜRELERİ (COOLDOWN)
# ---------------------------------------------------------
VIOLATION_COOLDOWN_SEC = 300 # Aynı ID için kaç saniye sonra tekrar ihlal üretilir (5 dk)
SPATIAL_COOLDOWN_SEC = 10    # Aynı koordinatta kaç saniye sonra tekrar ihlal üretilir
SPATIAL_RADIUS = 150         # Aynı koordinat sayılması için gereken yarıçap (Piksel)

# 5. PERFORMANS AYARLARI
# ---------------------------------------------------------
ENABLE_FRAME_SKIPPING = False  # Kare atlamayı aç/kapat (ID takibi düşerse False yapın)
FRAME_SKIP_INTERVAL = 1       # Kaç karede bir AI çalışsın (2 = her 2 kareden biri)
