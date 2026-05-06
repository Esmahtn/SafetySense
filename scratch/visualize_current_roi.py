import cv2
import numpy as np

VIDEO_PATH = "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"
OUTPUT_PATH = "scratch/current_roi_preview.jpg"

roi_polygon = np.array([(381, 34), (298, 148), (213, 289), (563, 283), (403, 35)], dtype=np.int32)
ref_width = 800
ref_height = 450

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 159000)
ret, frame = cap.read()
cap.release()

if ret:
    h, w = frame.shape[:2]
    
    # Scale ROI
    scale_x = w / ref_width
    scale_y = h / ref_height
    scaled_points = [(int(px * scale_x), int(py * scale_y)) for px, py in roi_polygon]
    scaled_roi = np.array(scaled_points, dtype=np.int32)
    
    middle_y = h // 2
    
    overlay = frame.copy()
    cv2.fillPoly(overlay, [scaled_roi], (255, 255, 0)) # Cyan fill
    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
    cv2.polylines(frame, [scaled_roi], True, (255, 255, 0), 2)
    
    cv2.line(frame, (0, middle_y), (w, middle_y), (0, 255, 255), 4) # Yellow line
    cv2.putText(frame, "TERS YON CIZGISI", (20, middle_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
    
    # Save the frame
    cv2.imwrite(OUTPUT_PATH, frame)
    print(f"Saved preview to {OUTPUT_PATH}")
else:
    print("Failed to read video")
