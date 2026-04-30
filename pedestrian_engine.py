import cv2
import math
import numpy as np
import time
import sqlite3
import os
from collections import deque
from ultralytics import YOLO
from async_camera import SmartCamera

class PedestrianEngine:
    def __init__(self, camera_id, camera_name, source, model=None):
        self.camera_id, self.camera_name, self.source = camera_id, camera_name, source
        self.model_name = "yolo11n.pt" if not model else None
        self.model = model
        self.current_frame, self.running = None, True
        
        # ROI Alanı
        self.roi_polygon = np.array([(38, 446), (171, 346), (289, 258), (372, 199), (442, 148), (485, 124), (521, 96), (533, 86), (576, 91), (552, 192), (502, 329), (456, 448)], dtype=np.int32)
        self.ref_width, self.ref_height, self.roi_scaled = 800, 450, False
        self.mask_polygon = np.array([[91, 980], [1094, 295], [1130, 297], [1170, 272], [1160, 265], [1260, 208], [1275, 198], [1271, 104], [1124, 84], [927, 67], [798, 54], [631, 57], [477, 62], [282, 81], [114, 107], [10, 134], [11, 718], [82, 971]], dtype=np.int32)
        
        self.person_in_roi_frames = {}
        # 15 Saniye KATI GLOBAL COOLDOWN
        self.last_global_violation_time = 0
        self.violation_cooldown_sec = 15
        
        self.on_violation = None

    def log_violation(self, person_id, frame, box=None):
        current_time = time.time()
        if (current_time - self.last_global_violation_time) < self.violation_cooldown_sec: return
        self.last_global_violation_time = current_time
        
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
        img_name = f"yaya_{self.camera_id}_{person_id}_{time.strftime('%H%M%S')}_{np.random.randint(1000,9999)}.jpg"
        img_path = f"ihlal_kayitlari/{img_name}"
        crop_name = f"crop_{img_name}"
        crop_path = f"ihlal_kayitlari/{crop_name}"
        
        # SS ÜZERİNE BÜYÜK YAZI YAZ
        evidence = frame.copy()
        if box is not None:
            cv2.rectangle(evidence, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 10)
            y1, y2 = max(0, int(box[1]-50)), min(frame.shape[0], int(box[3]+50))
            x1, x2 = max(0, int(box[0]-50)), min(frame.shape[1], int(box[2]+50))
            cv2.imwrite(crop_path, frame[y1:y2, x1:x2])
        else:
            cv2.imwrite(crop_path, frame)
            
        # Siyah bant ve beyaz yazı
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 100), (0, 0, 0), -1)
        cv2.putText(evidence, "IHLAL: YAYA YASAK ALAN", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(evidence, f"TARIH: {ts_str} | ID: {person_id}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imwrite(img_path, evidence)
        
        if self.on_violation:
            self.on_violation({"id": int(person_id), "cam_name": self.camera_name, "type": "Yaya İhlali", "time": ts_str, "img": img_name})

    def process(self):
        cap = SmartCamera(self.source, simulate_live=False)
        cap.set(cv2.CAP_PROP_POS_MSEC, 250000)
        cap.start()
        
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        scale_x, scale_y = width / self.ref_width, height / self.ref_height
        self.roi_polygon = np.array([(int(x * scale_x), int(y * scale_y)) for x, y in self.roi_polygon], dtype=np.int32); self.roi_scaled = True
        
        while self.running:
            if self.model is None and hasattr(self, 'model_name') and self.model_name: self.model = YOLO(self.model_name); self.model_name = None
            if not cap.isOpened(): time.sleep(1); continue
            ret, frame = cap.read()
            if not ret: time.sleep(0.01); continue
                
            display_frame = frame.copy()
            cv2.fillPoly(frame, [self.mask_polygon], (0, 0, 0))
            cv2.polylines(display_frame, [self.roi_polygon], True, (0, 255, 255), 2)
            
            if self.model:
                results = self.model.track(frame, persist=True, classes=[0], conf=0.45, imgsz=640, tracker="botsort.yaml", verbose=False)
                if results and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    ids = results[0].boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        x1, y1, x2, y2 = map(int, box)
                        if cv2.pointPolygonTest(self.roi_polygon, (float((x1+x2)/2), float(y2)), False) >= 0:
                            self.person_in_roi_frames[track_id] = self.person_in_roi_frames.get(track_id, 0) + 1
                            if self.person_in_roi_frames[track_id] >= 3: # 3 frame üst üste
                                self.log_violation(track_id, frame, box=box)
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

            preview = cv2.resize(display_frame, (800, 450))
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            time.sleep(0.01)
        cap.release()

    def get_frame(self): return self.current_frame
