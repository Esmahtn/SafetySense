import cv2
import numpy as np
import os

VIDEO_PATH = "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"
# Original: [(38, 446), (171, 346), (289, 258), (372, 199), (442, 148), (485, 124), (521, 96), (533, 86), (576, 91), (552, 192), (502, 329), (456, 448)]
# New (excluding junction):
roi_polygon = np.array([
    (171, 346), (289, 258), (372, 199), 
    (442, 148), (485, 124), (521, 96), (533, 86), 
    (576, 91), (552, 192), (502, 329)
], dtype=np.int32)

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 30 * 1000)
ret, frame = cap.read()
cap.release()

if ret:
    frame = cv2.resize(frame, (800, 450))
    overlay = frame.copy()
    cv2.fillPoly(overlay, [roi_polygon], (0, 0, 255)) # Red for new
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    cv2.polylines(frame, [roi_polygon], True, (0, 0, 255), 2)
    
    cv2.imwrite("new_roi_check.jpg", frame)
    print("Saved new_roi_check.jpg")
else:
    print("Could not read video")
