"""
Hız Koridoru — Yaya Yasak Bölge Tanımlama Aracı
Kullanım: python select_roi_hiz_yaya.py
  - Sol tık: köşe noktası ekle
  - Sağ tık: son noktayı sil
  - ENTER: koordinatları kopyala ve çık
  - ESC: iptal
"""
import cv2
import numpy as np
from config import get_source

# Hız kamerasının yerel video yolu
VIDEO_SOURCE = get_source("HIZ_KORIDORU")

points = []

def mouse_callback(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"  Nokta eklendi: ({x}, {y})")
    elif event == cv2.EVENT_RBUTTONDOWN and points:
        points.pop()
        print("  Son nokta silindi.")

def draw_overlay(frame, pts):
    overlay = frame.copy()
    if len(pts) >= 3:
        cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], (255, 0, 255))
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (255, 0, 255), 2)
    for i, p in enumerate(pts):
        cv2.circle(frame, p, 5, (0, 255, 255), -1)
    return frame

print(f"\nBağlanılıyor: {VIDEO_SOURCE}")
cap = cv2.VideoCapture(VIDEO_SOURCE)
ret, frame = cap.read()
cap.release()

if not ret:
    print("HATA: Kamera veya video okunamadı! Lütfen bağlantıyı kontrol edin.")
    exit()

# Standart çalışma boyutu
frame = cv2.resize(frame, (800, 450))

win_name = "HIZ KAMERASI - YAYA ROI SECIMI"
cv2.namedWindow(win_name)
cv2.setMouseCallback(win_name, mouse_callback)

print("\n=== HIZ KAMERASI YAYA ROI SEÇİCİ ===")
print("1. Sol tık ile yaya yasak bölgesinin köşelerini işaretle.")
print("2. İşlemin bittiğinde ENTER tuşuna bas.")
print("3. Çıkan koordinatları kopyalayıp speed_engine.py içine yapıştır.\n")

while True:
    display = frame.copy()
    display = draw_overlay(display, points)
    
    cv2.putText(display, f"Nokta: {len(points)} | ENTER: Kaydet | ESC: Cik", (10, 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    cv2.imshow(win_name, display)
    key = cv2.waitKey(30) & 0xFF
    
    if key == 13 and len(points) >= 3: # ENTER
        print("\n✅ YENİ ROI KOORDİNATLARI:")
        print("-" * 30)
        print(f"self.ped_roi_polygon = np.array({points}, dtype=np.int32)")
        print("-" * 30)
        print("\nBu satırı speed_engine.py içindeki __init__ metodundaki eski polygon ile değiştirin.")
        break
    elif key == 27: # ESC
        print("\nİptal edildi.")
        break

cv2.destroyAllWindows()
