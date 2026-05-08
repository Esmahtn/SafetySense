import cv2
import time
import os
import sqlite3
import random
import math
import numpy as np
from threading import Lock
from datetime import datetime
from collections import deque
from ultralytics import YOLO
from .async_camera import SmartCamera
from .mailer import send_violation_email
import ai_config

class SpeedEngine:
    def __init__(self, cam_id, name, source, roi=None, model=None):
        self.cam_id, self.name, self.source = cam_id, name, source
        self.model_name = ai_config.MODEL_NAME if not model else None
        self.model = model
        self.cap = SmartCamera(source, simulate_live=False)
        self.cap.start()
        
        self.entry_times, self.track_history = {}, {}
        self.violation_buffer = {}     # ID: [is_in_roi, ...] (son 15 kare)
        
        # ⭐ Mekansal Soğuma (Alarm Ledger)
        self.alarm_ledger = []
        self.spatial_threshold = 150 # piksel
        self.temporal_threshold = 15 # saniye
        
        self.running = True
        self.current_frame = None
        self.frame_count = 0  
        self.violators, self.vehicle_logged = set(), set()
        self.track_history, self.entry_times, self.prev_positions = {}, {}, {}
        
        # ID bazlı + kameralar arası cooldown
        self.violation_cooldown_sec = 300  
        self.shared_violation_log = {}   
        self.shared_violation_lock = Lock()  
        
        # ⭐ Konum bazlı cooldown
        self._recent_violation_positions = [] 
        self.position_cooldown_radius = 150    
        self.position_cooldown_sec = 10         
        
        self.on_violation = None
        self.VIOLATIONS_DIR = "ihlal_kayitlari"
        self.DB_PATH = "violations.db"
        
        self.ped_roi_polygon = np.array(roi if roi else [(491, 130), (552, 140), (413, 448), (4, 431)], dtype=np.int32)
        self.roi_distance = ai_config.SPEED_ROI_DISTANCE
        self.roi_scaled, self.ref_width, self.ref_height, self.middle_y = False, 800, 450, None

    def update_config(self, cam_data):
        new_source = cam_data.get("source")
        new_roi = cam_data.get("roi")
        
        if new_source and new_source != self.source:
            print(f"[HIZ] {self.name} Kaynak güncelleniyor...")
            self.source = new_source
            self.cap.release()
            self.cap = SmartCamera(new_source, simulate_live=False)
            self.cap.start()
            
        if new_roi:
            print(f"[HIZ] {self.name} ROI güncelleniyor...")
            self.ped_roi_polygon = np.array(new_roi, dtype=np.int32)
            self.roi_scaled = False
        
        # ⭐ Hareketsiz Nesne Filtresi
        self.stationary_counters = {}  # ID: frame_count
        self.stationary_pixel_threshold = ai_config.STATIONARY_PIXEL_LIMIT
        self.stationary_frame_limit = ai_config.STATIONARY_FRAME_LIMIT
        self.conf_threshold = ai_config.YOLO_CONF_THRESHOLD

    def get_current_timestamp(self):
        """Hibrit Zaman Damgası: Video dosyasıysa video süresini, canlıysa gerçek saati kullanır."""
        ts_msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        if ts_msec > 0:
            return ts_msec / 1000.0
        
        # Eğer video dosyası olmasına rağmen POS_MSEC 0 ise (bazı AVI hataları), 
        # frame_count ve FPS üzerinden simüle et.
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps > 0 and self.frame_count > 0:
            return self.frame_count / fps
            
        return time.time()

    def _is_position_in_cooldown(self, cx, cy):
        """Verilen merkez noktası yakın zamanda ihlal kaydedilen bir konuma yakın mı?"""
        now = time.time()
        # Eski kayıtları temizle
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

    def _is_spatial_duplicate(self, cx, cy, v_type):
        """⭐ Mekansal Soğuma: Aynı bölgede yakın zamanda benzer bir ihlal raporlandı mı?"""
        now = time.time()
        self.alarm_ledger = [a for a in self.alarm_ledger if (now - a[0]) < 30]
        v_cat = v_type.split('(')[0].strip() # "HIZ IHLALI" veya "YAYA IHLALI" vb.
        for ts, ax, ay, atype in self.alarm_ledger:
            a_cat = atype.split('(')[0].strip()
            if a_cat == v_cat:
                dist = ((cx - ax)**2 + (cy - ay)**2)**0.5
                if dist < self.spatial_threshold and (now - ts) < self.temporal_threshold:
                    return True
        return False

    def log_violation(self, vehicle_id, frame, speed=None, box=None, violation_type=None):
        current_time = time.time()
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        v_type = violation_type or (f"HIZ IHLALI ({speed:.1f} KM/H)" if speed else "IHLAL")
        
        if box is not None:
            cx, cy = int((box[0] + box[2]) / 2), int(box[3])
            if self._is_spatial_duplicate(cx, cy, v_type):
                return
            self.alarm_ledger.append((time.time(), cx, cy, v_type))
            
        # ⭐ 1. Konum bazlı kontrol (ID'den bağımsız)
        if box is not None:
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            if self._is_position_in_cooldown(cx, cy):
                return
        v_cat = v_type.split('(')[0].strip()
        # 2. Thread-safe ID + Kategori bazlı kontrol
        with self.shared_violation_lock:
            key = f"{vehicle_id}_{v_cat}"
            last_time = self.shared_violation_log.get(key, 0)
            if (current_time - last_time) < self.violation_cooldown_sec:
                return
            self.shared_violation_log[key] = current_time
        # ⭐ Konum kaydını yap
        if box is not None:
            self._register_violation_position(int((box[0]+box[2])/2), int((box[1]+box[3])/2))
        
        v_type = violation_type or (f"HIZ IHLALI ({speed:.1f} KM/H)" if speed else "IHLAL")
        
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_file = datetime.now().strftime("%H%M%S_%f")
        img_name = f"speed_{self.cam_id}_{ts_file}_{random.randint(1000,9999)}.jpg"
        crop_name = f"crop_{img_name}"
        img_path = os.path.join(self.VIOLATIONS_DIR, img_name)
        crop_path = os.path.join(self.VIOLATIONS_DIR, crop_name)
        
        # SS ÜZERİNE BÜYÜK YAZI YAZ (KANIT)
        evidence = frame.copy()
        if box is not None:
            cv2.rectangle(evidence, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 10)
            y1, y2 = max(0, int(box[1]-50)), min(frame.shape[0], int(box[3]+50))
            x1, x2 = max(0, int(box[0]-50)), min(frame.shape[1], int(box[2]+50))
            cv2.imwrite(crop_path, frame[y1:y2, x1:x2])
        else:
            cv2.imwrite(crop_path, frame)
            
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 100), (0, 0, 0), -1)
        cv2.putText(evidence, f"IHLAL: {v_type.upper()}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(evidence, f"KAMERA: {self.name.upper()} | ID: {vehicle_id}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(img_path, evidence)
        
        conn = sqlite3.connect(self.DB_PATH, timeout=20); cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(vehicle_id), self.name, v_type, ts_str, img_name, ""))
        conn.commit(); last_id = cursor.lastrowid; conn.close()
        
        # 4️⃣ E-posta bildirimi (arka planda)
        send_violation_email(self.name, v_type, int(vehicle_id), ts_str, img_path, crop_path=crop_path)
        
        if self.on_violation:
            self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": v_type, "time": ts_str, "img": img_name})

    def _cleanup_stale_ids(self, active_ids):
        """5️⃣ Artık takip edilmeyen ID'leri sözlüklerden temizler (bellek sızıntısı önleme)."""
        active_set = set(active_ids)
        for d in [self.prev_positions, self.entry_times, self.track_history, self.stationary_counters]:
            stale = [k for k in d if k not in active_set]
            for k in stale:
                del d[k]

    def process(self):
        while True:
            try:
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

                self.frame_count += 1
                should_process = not ai_config.ENABLE_FRAME_SKIPPING or (self.frame_count % ai_config.FRAME_SKIP_INTERVAL == 0)
                
                if self.model and should_process: 
                    current_ts = self.get_current_timestamp()
                    results = self.model.track(frame, persist=True, classes=[0, 2, 3, 5, 7], imgsz=ai_config.YOLO_IMG_SIZE, conf=self.conf_threshold, tracker="botsort_custom.yaml", verbose=False)
                    active_ids = []
                    if results and results[0].boxes.id is not None:
                        boxes = results[0].boxes.xyxy.cpu().numpy()
                        ids = results[0].boxes.id.cpu().numpy().astype(int)
                        clss = results[0].boxes.cls.cpu().numpy().astype(int)
                        confs = results[0].boxes.conf.cpu().numpy()
                        active_ids = ids
                        
                        # Bellek temizliği
                        if self.frame_count % 100 == 0: self._cleanup_stale_ids(ids)
                        
                        for box, id, cls, conf in zip(boxes, ids, clss, confs):
                            x1, y1, x2, y2 = map(int, box)
                            cx, cy = int((x1+x2)/2), int((y1+y2)/2) # ⭐ Aracın tam orta noktası
                            
                            # 1️⃣ ROI Kontrolü (Merkez Nokta)
                            is_in_roi = cv2.pointPolygonTest(self.ped_roi_polygon, (float(cx), float(cy)), False) >= 0
                            
                            # 2️⃣ Histerezis (M-out-of-N)
                            if id not in self.violation_buffer: self.violation_buffer[id] = []
                            self.violation_buffer[id].append(is_in_roi)
                            if len(self.violation_buffer[id]) > 8: self.violation_buffer[id].pop(0)
                            
                            # Onay: Son 8 karenin 3'ünde bölgede olması şart
                            roi_confirmed = sum(self.violation_buffer[id]) >= 3
                            
                            # 3️⃣ Hareket Kontrolü (Hareketsiz nesneleri filtrele)
                            is_moving = True
                            if id in self.prev_positions:
                                px, py = self.prev_positions[id]
                                dist = math.sqrt((cx - px)**2 + (cy - py)**2)
                                if dist < self.stationary_pixel_threshold:
                                    self.stationary_counters[id] = self.stationary_counters.get(id, 0) + 1
                                else:
                                    self.stationary_counters[id] = 0
                            
                            if self.stationary_counters.get(id, 0) >= self.stationary_frame_limit:
                                is_moving = False

                            if cls == 0 and conf > self.conf_threshold:
                                if is_in_roi and roi_confirmed and is_moving:
                                    self.log_violation(id, frame, box=box, violation_type="Yaya İhlali")
                                
                                # Yaya İkazı: Bölgede onaylandıysa KIRMIZI, değilse SARI
                                color = (0, 0, 255) if (is_in_roi and roi_confirmed and is_moving) else (0, 255, 255)
                                if not is_moving: color = (128, 128, 128)
                                
                                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                                status = "(YAYA!)" if is_moving else "(SABIT NESNE)"
                                cv2.putText(display_frame, f"ID: {id} {status}", (x1, y1 - 10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                self.prev_positions[id] = (cx, cy)
                                continue
                                
                            if cls in [2, 3, 5, 7]:
                                if is_in_roi and id not in self.entry_times and is_moving: 
                                    self.entry_times[id] = current_ts
                                elif not is_in_roi and id in self.entry_times:
                                    duration = current_ts - self.entry_times[id]
                                    if duration > ai_config.SPEED_CALC_MIN_DURATION and ai_config.ENABLE_SPEED_DETECTION:
                                        speed = (self.roi_distance / duration) * 3.6 * ai_config.SPEED_CORRECTION_FACTOR
                                        if speed > ai_config.MIN_SPEED_LIMIT and roi_confirmed: 
                                            self.log_violation(id, frame, speed=speed, box=box)
                                    del self.entry_times[id]
                                    
                                # Ters Yön Kontrolü: Basit çizgi geçişi (aşağıdan yukarı)
                                if id in self.prev_positions and roi_confirmed and is_moving:
                                    # Eski py değerine ulaşmak için:
                                    _, old_py = self.prev_positions[id]
                                    if old_py > self.middle_y and cy <= self.middle_y:
                                        self.log_violation(id, frame, box=box, violation_type="Hız Ters Yön")
                                    
                                self.prev_positions[id] = (cx, cy)
                                # Araç İkazı: Bölgede onaylandıysa SARI, değilse YEŞİL
                                color = (0, 255, 255) if (is_in_roi and roi_confirmed and is_moving) else (0, 255, 0)
                                if not is_moving: color = (128, 128, 128)
                                
                                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                                status = "" if is_moving else " (SABIT)"
                                cv2.putText(display_frame, f"ID: {id}{status}", (x1, y1 - 10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    # Buffer Temizliği
                    for rid in list(self.violation_buffer.keys()):
                        if rid not in active_ids: 
                            # ID kaybolduğunda hatalı ölçüm yapmamak için kaydı siliyoruz
                            if rid in self.entry_times:
                                del self.entry_times[rid]
                            del self.violation_buffer[rid]

                # ⭐ Görüntüyü her frame'de güncelle
                preview = cv2.resize(display_frame, (800, 450)); _, buffer = cv2.imencode('.jpg', preview); self.current_frame = buffer.tobytes()
                time.sleep(0.01)
            except Exception as e:
                print(f"SpeedEngine Hatası: {e}")
                time.sleep(1)

    def get_frame(self): return self.current_frame
