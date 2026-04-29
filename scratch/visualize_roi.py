import cv2
import numpy as np
import os

VIDEO_PATH = "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"
roi_polygon = np.array([
    (38, 446), (171, 346), (289, 258), (372, 199), 
    (442, 148), (485, 124), (521, 96), (533, 86), 
    (576, 91), (552, 192), (502, 329), (456, 448)
], dtype=np.int32)

cap = cv2.VideoCapture(VIDEO_PATH)
cap.set(cv2.CAP_PROP_POS_MSEC, 30 * 1000)
ret, frame = cap.read()
cap.release()

if ret:
    frame = cv2.resize(frame, (800, 450))
    overlay = frame.copy()
    cv2.fillPoly(overlay, [roi_polygon], (0, 255, 255))
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    cv2.polylines(frame, [roi_polygon], True, (0, 200, 200), 2)
    
    # Save current ROI
    cv2.imwrite("current_roi_check.jpg", frame)
    print("Saved current_roi_check.jpg")
else:
    print("Could not read video")
