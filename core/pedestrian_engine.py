import cv2
import math
import numpy as np
import time
import sqlite3
import os
from datetime import datetime
from threading import Lock
from collections import deque
from ultralytics import YOLO
from .async_camera import SmartCamera
from .mailer import send_violation_email
import ai_config
import json

class PedestrianEngine:
    def __init__(self, camera_id, camera_name, source, model=None):
        self.camera_id, self.camera_name, self.source = camera_id, camera_name, source
        self.model_name = ai_config.MODEL_NAME if not model else None
        self.model = model
        self.person_in_roi_frames = {} # ID: frame_count
        self.violation_buffer = {}     # ID: [is_in_roi, ...] (son 15 kare)
        
        # ⭐ Mekansal Soğuma (Alarm Ledger)
        self.alarm_ledger = []
        self.spatial_threshold = 150 # piksel
        self.temporal_threshold = 15 # saniye (yayalar daha yavaş hareket eder)
        
        self.running = True
        self.current_frame = None
        self.frame_count = 0 
        self.conf_threshold = ai_config.YOLO_CONF_THRESHOLD
        
        # ROI Alanı
        self.roi_polygon = np.array([(38, 446), (171, 346), (289, 258), (372, 199), (442, 148), (485, 124), (521, 96), (533, 86), (576, 91), (552, 192), (502, 329), (456, 448)], dtype=np.int32)
        self.ref_width, self.ref_height, self.roi_scaled = 800, 450, False
        self.mask_polygon = np.array([[91, 980], [1094, 295], [1130, 297], [1170, 272], [1160, 265], [1260, 208], [1275, 198], [1271, 104], [1124, 84], [927, 67], [798, 54], [631, 57], [477, 62], [282, 81], [114, 107], [10, 134], [11, 718], [82, 971]], dtype=np.int32)
        
        # Özel maske yükle (varsa)
        self.mask_path = "pedestrian_mask.json"
        if os.path.exists(self.mask_path):
            try:
                with open(self.mask_path, "r") as f:
                    custom_points = json.load(f)
                    if custom_points:
                        self.mask_polygon = np.array(custom_points, dtype=np.int32)
                        print(f"[YAYA] Özel maske yüklendi: {len(custom_points)} nokta.")
            except Exception as e:
                print(f"[YAYA] Maske yüklenirken hata: {e}")
        
        # ID bazlı + kameralar arası cooldown (server.py inject eder)
        self.violation_cooldown_sec = 300 # ⭐ 5 dakika ID bazlı soğuma
        self.shared_violation_log = {}   # Varsayılan boş — server.py inject eder
        self.shared_violation_lock = Lock()  # Varsayılan lock — server.py inject eder
        
        # ⭐ Konum bazlı cooldown
        self._recent_violation_positions = []  # [(cx, cy, timestamp)]
        self.position_cooldown_radius = 150    # ⭐ 150 piksel
        self.position_cooldown_sec = 10         # ⭐ 10 saniye (Konum bazlı)
        
        # Bellek temizliği
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # saniye
        self.DB_PATH = "violations.db"
        
        self.on_violation = None

    def _is_position_in_cooldown(self, cx, cy):
        import math
        now = time.time()
        self._recent_violation_positions = [
            (x, y, t) for x, y, t in self._recent_violation_positions
            if now - t < self.position_cooldown_sec
        ]
        for x, y, t in self._recent_violation_positions:
            if math.sqrt((cx - x) ** 2 + (cy - y) ** 2) < self.position_cooldown_radius:
                return True
        return False

    def _register_violation_position(self, cx, cy):
        self._recent_violation_positions.append((cx, cy, time.time()))

    def _is_spatial_duplicate(self, cx, cy):
        """⭐ Mekansal Soğuma: Aynı bölgede yakın zamanda yaya ihlali raporlandı mı?"""
        now = time.time()
        self.alarm_ledger = [a for a in self.alarm_ledger if (now - a[0]) < 30]
        for ts, ax, ay in self.alarm_ledger:
            dist = ((cx - ax)**2 + (cy - ay)**2)**0.5
            if dist < self.spatial_threshold and (now - ts) < self.temporal_threshold:
                return True
        return False

    def log_violation(self, person_id, frame, box=None):
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_time = time.time()
        
        if box is not None:
            cx, cy = int((box[0] + box[2]) / 2), int(box[3])
            if self._is_spatial_duplicate(cx, cy):
                return
            self.alarm_ledger.append((time.time(), cx, cy))
            
        # ⭐ 1. Konum bazlı kontrol (ID'den bağımsız)
        if box is not None:
            cx = int((int(box[0]) + int(box[2])) / 2)
            cy = int(box[3])  # Ayak noktası
            if self._is_position_in_cooldown(cx, cy):
                return
        v_cat = "Yaya İhlali"
        # 2. Thread-safe ID + Kategori bazlı kontrol
        with self.shared_violation_lock:
            key = f"{person_id}_{v_cat}"
            last_time = self.shared_violation_log.get(key, 0)
            if (current_time - last_time) < self.violation_cooldown_sec:
                return
            self.shared_violation_log[key] = current_time
        # ⭐ Konum kaydını yap
        if box is not None:
            self._register_violation_position(cx, cy)
        
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
            
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 100), (0, 0, 0), -1)
        cv2.putText(evidence, "IHLAL: YAYA YASAK ALAN", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(evidence, f"TARIH: {ts_str} | ID: {person_id}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(img_path, evidence)
        
        # 4️⃣ Veritabanına kaydet
        conn = sqlite3.connect(self.DB_PATH, timeout=20); cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(person_id), self.camera_name, "Yaya İhlali", ts_str, img_name, ""))
        conn.commit(); last_id = cursor.lastrowid; conn.close()

        # 5️⃣ E-posta bildirimi (arka planda)
        send_violation_email(self.camera_name, "Yaya İhlali", int(person_id), ts_str, img_path, crop_path=crop_path)
        
        if self.on_violation:
            self.on_violation({"id": int(person_id), "db_id": last_id, "cam_name": self.camera_name, "type": "Yaya İhlali", "time": ts_str, "img": img_name})

    def _cleanup_stale_ids(self, active_ids):
        """5️⃣ Artık görünmeyen kişilerin frame sayacını temizler."""
        active_set = set(active_ids)
        stale = [k for k in self.person_in_roi_frames if k not in active_set]
        for k in stale:
            del self.person_in_roi_frames[k]

    def process(self):
        cap = SmartCamera(self.source, simulate_live=False)
        cap.set(cv2.CAP_PROP_POS_MSEC, 250000)
        cap.start()
        
        # Döngü içinde ilk geçerli kareyi bekle ve çözünürlüğü al
        while self.running:
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                scale_x, scale_y = w / self.ref_width, h / self.ref_height
                self.roi_polygon = np.array([(int(x * scale_x), int(y * scale_y)) for x, y in self.roi_polygon], dtype=np.int32)
                self.mask_polygon = np.array([(int(x * scale_x), int(y * scale_y)) for x, y in self.mask_polygon], dtype=np.int32)
                self.roi_scaled = True
                print(f"[YAYA] Çözünürlük belirlendi: {w}x{h}, Maske ölçeklendi.")
                break
            time.sleep(0.1)
        
        while self.running:
            try:
                if self.model is None and hasattr(self, 'model_name') and self.model_name: self.model = YOLO(self.model_name); self.model_name = None
                if not cap.isOpened(): time.sleep(1); continue
                ret, frame = cap.read()
                if not ret: time.sleep(0.01); continue
                    
                display_frame = frame.copy()
                
                # Maskeyi hem analiz karesine (siyah) hem de görüntü karesine (yarı saydam siyah) uygula
                mask_overlay = display_frame.copy()
                cv2.fillPoly(mask_overlay, [self.mask_polygon], (0, 0, 0))
                cv2.addWeighted(mask_overlay, 0.5, display_frame, 0.5, 0, display_frame) # Görsel onay için %50 şeffaf
                
                cv2.fillPoly(frame, [self.mask_polygon], (0, 0, 0)) # Analiz için tam siyah
                cv2.polylines(display_frame, [self.roi_polygon], True, (0, 255, 255), 2)
                
                self.frame_count += 1
                should_process = not ai_config.ENABLE_FRAME_SKIPPING or (self.frame_count % ai_config.FRAME_SKIP_INTERVAL == 0)
                
                if self.model and should_process: 
                    results = self.model.track(frame, persist=True, classes=[0], conf=self.conf_threshold, imgsz=ai_config.YOLO_IMG_SIZE, tracker="botsort_custom.yaml", verbose=False)
                    active_ids = []
                    if results and results[0].boxes.id is not None:
                        boxes = results[0].boxes.xyxy.cpu().numpy()
                        ids = results[0].boxes.id.int().cpu().tolist()
                        active_ids = ids
                        
                        # 5️⃣ Periyodik bellek temizliği
                        if self.frame_count % 100 == 0: self._cleanup_stale_ids(ids)
                        
                        for box, track_id in zip(boxes, ids):
                            x1, y1, x2, y2 = map(int, box)
                            cx, cy = int((x1+x2)/2), int(y2)
                            
                            # 1️⃣ ROI Kontrolü (Bottom-Center)
                            is_in_roi = cv2.pointPolygonTest(self.roi_polygon, (float(cx), float(cy)), False) >= 0
                            
                            # 2️⃣ Histerezis (M-out-of-N)
                            if track_id not in self.violation_buffer: self.violation_buffer[track_id] = []
                            self.violation_buffer[track_id].append(is_in_roi)
                            if len(self.violation_buffer[track_id]) > 8: self.violation_buffer[track_id].pop(0)
                            
                            # Onay: Son 8 karenin 3'ünde bölgede olması şart
                            roi_confirmed = sum(self.violation_buffer[track_id]) >= 3
                            
                            if is_in_roi and roi_confirmed:
                                self.log_violation(track_id, frame, box=box)
                            
                            # Çizim (ID ve Durum)
                            label = f"ID: {track_id}"
                            if roi_confirmed:
                                label += " (YAYA!)"
                                color = (0, 0, 255) # KIRMIZI (İhlal)
                            else:
                                color = (0, 255, 255) # SARI (Bölgede)
                                
                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(display_frame, label, (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    # Buffer Temizliği
                    for rid in list(self.violation_buffer.keys()):
                        if rid not in active_ids: del self.violation_buffer[rid]
                
                # ⭐ Görüntüyü her zaman güncelle
                preview = cv2.resize(display_frame, (800, 450))
                _, buffer = cv2.imencode('.jpg', preview)
                self.current_frame = buffer.tobytes()
                time.sleep(0.01)
            except Exception as e:
                print(f"PedestrianEngine Hatası: {e}")
                time.sleep(1)
        cap.release()

    def get_frame(self): return self.current_frame
