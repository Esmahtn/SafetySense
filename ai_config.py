# =========================================================
# AI VE HIZ KALİBRASYON AYARLARI (ai_config.py)
# =========================================================

# 0. MODEL SEÇİMİ
# ---------------------------------------------------------
# yolo11n.pt (Nano) - En hızlı, en düşük doğruluk
# yolo11s.pt (Small) - Hızlı, orta doğruluk
# yolo11m.pt (Medium) - Orta hız, yüksek doğruluk
MODEL_NAME = "yolo11n.pt"

# 1. HIZ TESPİT AYARLARI
# ---------------------------------------------------------
SPEED_ROI_DISTANCE = 27.0  # Ekranda çizilen pembe alanın gerçek uzunluğu (Metre)
MIN_SPEED_LIMIT = 20.0     # İhlal sayılması için gereken minimum hız (KM/H)
SPEED_CALC_MIN_DURATION = 1.0 # Hız hesabı için gereken minimum süre (Saniye). Kısa süreli hatalı tespitleri eler.
SPEED_CORRECTION_FACTOR = 1.0 # Hız düzeltme katsayısı (Hızlar hep 2 katıysa 0.5 yapın)
ENABLE_SPEED_DETECTION = False # Hız tespitini aç/kapat

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
