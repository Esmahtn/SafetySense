"""
ROI Seçici — Ters Yön Bölgesi Tanımlama Aracı
Kullanım: python select_roi_ters.py
  - Sol tık: köşe noktası ekle
  - Sağ tık: son noktayı sil
  - ENTER: koordinatları kaydet ve çık
  - ESC: iptal
"""
import cv2
import numpy as np

VIDEO_PATH = "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"

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
        cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], (255, 255, 0))
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (255, 255, 0), 2)
    for i, p in enumerate(pts):
        cv2.circle(frame, p, 6, (0, 0, 255), -1)
        cv2.putText(frame, str(i+1), (p[0]+8, p[1]-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    return frame

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 170 * 1000)  # 170. saniyeden başla (ters yön videoda araçların olduğu yer)
ret, base_frame = cap.read()
cap.release()

if not ret:
    print("Video okunamadı!")
    exit()

# Orijinal boyutları koruyalım veya preview için resize edelim
# server.py 800x450'ye resize ediyor, biz de öyle yapalım ki koordinatlar uysun
base_frame = cv2.resize(base_frame, (800, 450))

cv2.namedWindow("Ters Yon ROI Sec - ENTER: Kaydet | ESC: Cik")
cv2.setMouseCallback("Ters Yon ROI Sec - ENTER: Kaydet | ESC: Cik", mouse_callback)

print("\n=== TERS YON ROI SEÇİCİ ===")
print("Sol tık ile ters yön takip bölgesinin (koridorun) köşelerini işaretle.")
print("Alt kısımdaki kavşağı (araçların sağa sola döndüğü yer) DIŞARIDA bırak.")
print("ENTER -> kaydet | ESC -> cik\n")

while True:
    display = base_frame.copy()
    display = draw_overlay(display, points)

    info = f"Nokta: {len(points)} | ENTER: Kaydet | ESC: Cik"
    cv2.putText(display, info, (10, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow("Ters Yon ROI Sec - ENTER: Kaydet | ESC: Cik", display)
    key = cv2.waitKey(30) & 0xFF

    if key == 13 and len(points) >= 3:  # ENTER
        print("\n✅ TERS YÖN ROI koordinatları:")
        print(f"TERS_YON_ROI = {points}")
        cv2.destroyAllWindows()
        break
    elif key == 27:  # ESC
        print("İptal edildi.")
        cv2.destroyAllWindows()
        break
