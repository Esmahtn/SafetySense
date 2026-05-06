"""
ROI Seçici — Yaya Yasak Bölge Tanımlama Aracı
Kullanım: python select_roi.py
  - Sol tık: köşe noktası ekle
  - Sağ tık: son noktayı sil
  - ENTER: koordinatları kaydet ve çık
  - ESC: iptal
"""
import cv2
import numpy as np
from config import get_source

VIDEO_PATH = get_source("GUVENSIZ_BOLGE")

points = []

def mouse_callback(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"  Nokta eklendi: ({x}, {y})  — Toplam: {len(points)}")
    elif event == cv2.EVENT_RBUTTONDOWN and points:
        removed = points.pop()
        print(f"  Silindi: {removed}")

def draw_overlay(frame, pts):
    overlay = frame.copy()
    if len(pts) >= 3:
        cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], (0, 255, 255))
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 220, 220), 2)
    for i, p in enumerate(pts):
        cv2.circle(frame, p, 6, (0, 0, 255), -1)
        cv2.putText(frame, str(i+1), (p[0]+8, p[1]-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    return frame

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 30 * 1000)  # 30. saniyeden başla
ret, base_frame = cap.read()
cap.release()

if not ret:
    print("Video okunamadı!")
    exit()

base_frame = cv2.resize(base_frame, (800, 450))

cv2.namedWindow("ROI Seç — Sol Tık: Nokta Ekle | Sağ Tık: Sil | ENTER: Kaydet | ESC: Çık")
cv2.setMouseCallback("ROI Seç — Sol Tık: Nokta Ekle | Sağ Tık: Sil | ENTER: Kaydet | ESC: Çık", mouse_callback)

print("\n=== ROI SEÇİCİ ===")
print("Sol tık ile yaya yasak bölgesinin köşelerini işaretle")
print("En az 3, en fazla 8 nokta ekle")
print("ENTER -> kaydet | ESC -> cik\n")

while True:
    display = base_frame.copy()
    display = draw_overlay(display, points)

    info = f"Nokta: {len(points)} | Sol Tik: Ekle | Sag Tik: Sil | ENTER: Kaydet"
    cv2.putText(display, info, (10, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow("ROI Seç — Sol Tık: Nokta Ekle | Sağ Tık: Sil | ENTER: Kaydet | ESC: Çık", display)
    key = cv2.waitKey(30) & 0xFF

    if key == 13 and len(points) >= 3:  # ENTER
        print("\n✅ ROI koordinatları:")
        print(f"ROI_POLYGON = {points}")
        print("\nBu koordinatları kopyalayıp pedestrian_engine.py'deki ROI_POLYGON satırına yapıştır.")
        cv2.destroyAllWindows()
        break
    elif key == 27:  # ESC
        print("İptal edildi.")
        cv2.destroyAllWindows()
        break

