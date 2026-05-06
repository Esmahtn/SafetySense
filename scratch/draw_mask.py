import cv2
import numpy as np
import os

# Video yolu (Ters Yön videosu için güncellendi)
video_path = "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"
if not os.path.exists(video_path):
    print(f"HATA: Video dosyası bulunamadı: {video_path}")
    exit()

points = []

def draw_polygon(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"Nokta eklendi: [{x}, {y}]")

cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
if not ret:
    print("HATA: Görüntü okunamadı.")
    exit()

# Görüntüyü biraz küçültelim ki ekrana sığsın (isteğe bağlı)
h, w = frame.shape[:2]
scale = 0.7
frame_small = cv2.resize(frame, (int(w*scale), int(h*scale)))

cv2.namedWindow("Alan Secici - Tiklayin, Bitince Q'ya Basin")
cv2.setMouseCallback("Alan Secici - Tiklayin, Bitince Q'ya Basin", draw_polygon)

print("\nTALIMATLAR:")
print("1. Kapatmak istediğiniz alanın köşelerine sırayla tıklayın.")
print("2. Yanlış tıklarsanız 'C' tuşuna basıp temizleyin.")
print("3. Seçim bitince 'Q' tuşuna basarak çıkın.")

while True:
    temp_frame = frame_small.copy()
    if len(points) > 0:
        # Noktaları çiz
        for pt in points:
            cv2.circle(temp_frame, tuple(pt), 5, (0, 0, 255), -1)
        # Çizgileri birleştir
        if len(points) > 1:
            cv2.polylines(temp_frame, [np.array(points)], False, (0, 255, 0), 2)
    
    cv2.imshow("Alan Secici - Tiklayin, Bitince Q'ya Basin", temp_frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    if key == ord('c'): points = []

# Koordinatları orijinal ölçeğe geri çeviriyoruz
original_points = [[int(x/scale), int(y/scale)] for x, y in points]

print("\n--- SECTIGINIZ KOORDINATLAR (Kopyalayıp Engine içine yapıştırın) ---")
print(f"self.mask_polygon = np.array({original_points}, dtype=np.int32)")
print("------------------------------------------------------------------\n")

cap.release()
cv2.destroyAllWindows()
