import cv2
import numpy as np
import json
import os
from config import get_source

# Pedestrian kamerasının video yolu
VIDEO_PATH = get_source("GUVENSIZ_BOLGE")
SAVE_PATH = "pedestrian_mask.json"

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
        cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], (0, 0, 0))
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 0, 255), 2)
    for i, p in enumerate(pts):
        cv2.circle(frame, p, 4, (0, 0, 255), -1)
    return frame

if not os.path.exists(VIDEO_PATH):
    print(f"HATA: Video bulunamadı: {VIDEO_PATH}")
    exit()

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 10 * 1000)
ret, base_frame = cap.read()
cap.release()

if not ret:
    print("Video okunamadı!")
    exit()

base_frame = cv2.resize(base_frame, (800, 450))

win_name = "MASKE SECICI - Siyaha boyanacak alani secin"
cv2.namedWindow(win_name)
cv2.setMouseCallback(win_name, mouse_callback)

print("\n=== MASKE SEÇİCİ ===")
print("Sol tık ile SİYAHA BOYANACAK (okunmayacak) bölgeyi işaretle.")
print("ENTER -> Kaydet ve Çık | ESC -> İptal")

while True:
    display = base_frame.copy()
    display = draw_overlay(display, points)

    cv2.imshow(win_name, display)
    key = cv2.waitKey(30) & 0xFF

    if key == 13 and len(points) >= 3:  # ENTER
        with open(SAVE_PATH, "w") as f:
            json.dump(points, f)
        print(f"\n✅ Maske kaydedildi: {SAVE_PATH}")
        cv2.destroyAllWindows()
        break
    elif key == 27:  # ESC
        print("İptal edildi.")
        cv2.destroyAllWindows()
        break
