import cv2
import time
import os
import sqlite3
import random
import numpy as np
from datetime import datetime
from collections import deque
from ultralytics import YOLO
from async_camera import SmartCamera

class SpeedEngine:
    def __init__(self, cam_id, name, source, model=None):
        self.cam_id, self.name, self.source = cam_id, name, source
        self.model_name = "yolo11n.pt" if not model else None
        self.model = model
        self.cap = SmartCamera(source, simulate_live=False)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 233 * 1000) # 3:53
        self.cap.start()
        
        self.current_frame = None
        self.violators, self.vehicle_logged = set(), set()
        self.track_history, self.entry_times, self.prev_positions = {}, {}, {}
        
        # 15 Saniye KATI GLOBAL COOLDOWN
        self.last_global_violation_time = 0
        self.violation_cooldown_sec = 15
        
        self.on_violation = None
        self.VIOLATIONS_DIR = "ihlal_kayitlari"
        self.DB_PATH = "violations.db"
        
        self.ped_roi_polygon = np.array([(491, 130), (552, 140), (413, 448), (4, 431)], dtype=np.int32)
        self.roi_distance, self.roi_scaled, self.ref_width, self.ref_height, self.middle_y = 30, False, 800, 450, None

    def log_violation(self, vehicle_id, frame, speed=None, box=None, violation_type=None):
        current_time = time.time()
        if (current_time - self.last_global_violation_time) < self.violation_cooldown_sec: return
        self.last_global_violation_time = current_time
        
        # Kullanıcının istediği spesifik isimlendirme
        v_type = violation_type or (f"HIZ IHLALI ({speed:.1f} KM/H)" if speed else "IHLAL")
        
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_file = datetime.now().strftime("%H%M%S_%f")
        img_name = f"speed_{self.cam_id}_{ts_file}_{random.randint(1000,9999)}.jpg"
        crop_name = f"crop_{img_name}"
        
        # SS ÜZERİNE BÜYÜK YAZI YAZ (KANIT)
        evidence = frame.copy()
        if box is not None:
            cv2.rectangle(evidence, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 10)
            y1, y2 = max(0, int(box[1]-50)), min(frame.shape[0], int(box[3]+50))
            x1, x2 = max(0, int(box[0]-50)), min(frame.shape[1], int(box[2]+50))
            cv2.imwrite(os.path.join(self.VIOLATIONS_DIR, crop_name), frame[y1:y2, x1:x2])
        else:
            cv2.imwrite(os.path.join(self.VIOLATIONS_DIR, crop_name), frame)
            
        # Siyah bant ve büyük yazı
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 100), (0, 0, 0), -1)
        cv2.putText(evidence, f"IHLAL: {v_type.upper()}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(evidence, f"KAMERA: {self.name.upper()} | ID: {vehicle_id}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imwrite(os.path.join(self.VIOLATIONS_DIR, img_name), evidence)
        
        conn = sqlite3.connect(self.DB_PATH, timeout=20); cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(vehicle_id), self.name, v_type, ts_str, img_name, ""))
        conn.commit(); last_id = cursor.lastrowid; conn.close()
        
        if self.on_violation:
            self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": v_type, "time": ts_str, "img": img_name})

    def process(self):
        while True:
            if self.model is None and hasattr(self, 'model_name') and self.model_name:
                self.model = YOLO(self.model_name); self.model_name = None
            if not self.cap.isOpened(): time.sleep(1); continue
            ret, frame = self.cap.read()
            if not ret: time.sleep(0.01); continue
            
            h_orig, w_orig = frame.shape[:2]
            if not self.roi_scaled:
                sx, sy = w_orig / self.ref_width, h_orig / self.ref_height
                self.ped_roi_polygon = np.array([(int(px*sx), int(py*sy)) for px, py in self.ped_roi_polygon], dtype=np.int32); self.roi_scaled = True
            if self.middle_y is None: self.middle_y = int(h_orig * 0.5)
            
            display_frame = frame.copy()
            cv2.line(display_frame, (0, self.middle_y), (w_orig, self.middle_y), (0, 255, 255), 2)
            cv2.polylines(display_frame, [self.ped_roi_polygon], True, (255, 0, 255), 2)

            if self.model:
                results = self.model.track(frame, persist=True, classes=[0, 2, 3, 5, 7], imgsz=640, conf=0.40, tracker="botsort.yaml", verbose=False)
                if results and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    ids = results[0].boxes.id.cpu().numpy().astype(int)
                    clss = results[0].boxes.cls.cpu().numpy().astype(int)
                    confs = results[0].boxes.conf.cpu().numpy()
                    
                    for box, id, cls, conf in zip(boxes, ids, clss, confs):
                        cx, cy, base_y = int((box[0]+box[2])/2), int((box[1]+box[3])/2), int(box[3])
                        
                        # 1. YAYA TESPİTİ
                        if cls == 0 and conf > 0.50:
                            if cv2.pointPolygonTest(self.ped_roi_polygon, (float(cx), float(base_y)), False) >= 0:
                                self.log_violation(id, frame, box=box, violation_type="Yaya İhlali")
                            cv2.rectangle(display_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 2)
                            continue
                            
                        # 2. ARAÇ TESPİTİ (Hız veya Ters Yön)
                        if cls in [2, 3, 5, 7]:
                            # Hız Ölçümü
                            is_in_roi = cv2.pointPolygonTest(self.ped_roi_polygon, (float(cx), float(base_y)), False) >= 0
                            if is_in_roi and id not in self.entry_times: self.entry_times[id] = time.time()
                            elif not is_in_roi and id in self.entry_times:
                                duration = time.time() - self.entry_times[id]
                                if duration > 0.5:
                                    speed = (self.roi_distance / duration) * 3.6
                                    if speed > 20: 
                                        self.log_violation(id, frame, speed=speed, box=box) # Default: Hız İhlali
                                del self.entry_times[id]
                                
                            # Ters Yön Kontrolü (Hız Koridoru için özel isim)
                            if id in self.prev_positions and self.prev_positions[id] > self.middle_y and base_y <= self.middle_y:
                                self.log_violation(id, frame, box=box, violation_type="Hız Ters Yön")
                            
                            self.prev_positions[id] = base_y
                            cv2.rectangle(display_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)

            preview = cv2.resize(display_frame, (800, 450))
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            time.sleep(0.01)

    def get_frame(self): return self.current_frame
