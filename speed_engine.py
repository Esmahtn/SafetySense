import cv2
import time
import os
import sqlite3
import random
from datetime import datetime
from collections import deque
from ultralytics import YOLO

class SpeedEngine:
    def __init__(self, cam_id, name, source, model=None):
        self.cam_id = cam_id
        self.name = name
        self.source = source
        if model:
            self.model = model
        else:
            self.model = YOLO("yolo11n.pt")
        self.cap = cv2.VideoCapture(source)
        # Hız Koridoru Başlangıç: 2:30 (150 saniye)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 150 * 1000)
        
        # Kamera FPS değerini al
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not self.fps or self.fps < 10:
            self.fps = 25.0
            
        self.current_frame = None
        self.frame_buffer = deque(maxlen=int(self.fps * 4)) # Geriye dönük 4 saniyelik tampon
        self.active_writers = []
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Kalibrasyon: Pixels Per Meter (PPM)
        # Tünel derinliği için tahmini değer. Gerçek mesafe bilgisine göre güncellenmelidir.
        # Örneğin: 1 metre yolda yaklaşık 25 piksel yer değişimine denk geliyorsa PPM = 25
        self.ppm = 25 
        
        # Takip Verileri
        self.track_history = {} # id -> deque of (timestamp, cy)
        self.violators = set()
        self.last_alert_time = 0
        self.violation_count = 0
        self.alert_timer = 0
        self.vehicle_logged = set()
        
        self.on_violation = None
        self.VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
        self.DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
        
        if not os.path.exists(self.VIOLATIONS_DIR):
            os.makedirs(self.VIOLATIONS_DIR)

    def calculate_speed(self, history):
        if len(history) < 10:
            return 0
        
        # Son 10 karedeki yer değişimi
        first_time, first_y = history[0]
        last_time, last_y = history[-1]
        
        dist_pixels = abs(last_y - first_y)
        time_elapsed = last_time - first_time
        
        if time_elapsed <= 0:
            return 0
            
        # Hız Hesaplama (km/h)
        dist_meters = dist_pixels / self.ppm
        speed_mps = dist_meters / time_elapsed
        speed_kmh = speed_mps * 3.6
        
        return speed_kmh

    def log_violation(self, vehicle_id, frame, speed, box=None):
        current_time = time.time()
        # Spam Önleme
        is_spam = (current_time - self.last_alert_time) < 15
        if is_spam: return

        timestamp = datetime.now().strftime("%H%M%S_%f")
        rand_suffix = random.randint(1000, 9999)
        img_name = f"speed_cam{self.cam_id}_ID{vehicle_id}_{timestamp}_{rand_suffix}.jpg"
        vid_name = f"speed_cam{self.cam_id}_ID{vehicle_id}_{timestamp}_{rand_suffix}.mp4"
        
        # Screenshot Kaydet
        img_path = os.path.join(self.VIOLATIONS_DIR, img_name)
        cv2.imwrite(img_path, frame)
        
        # CROP (Yakınlaştırma)
        crop_name = f"crop_{img_name}"
        crop_path = os.path.join(self.VIOLATIONS_DIR, crop_name)
        if box is not None:
            try:
                y1, y2 = max(0, int(box[1]-80)), min(frame.shape[0], int(box[3]+80))
                x1, x2 = max(0, int(box[0]-80)), min(frame.shape[1], int(box[2]+80))
                crop_img = frame[y1:y2, x1:x2]
                cv2.imwrite(crop_path, crop_img)
            except: cv2.imwrite(crop_path, frame)
        else:
            cv2.imwrite(crop_path, frame)
            
        # Video Kaydı
        vid_path = os.path.join(self.VIOLATIONS_DIR, vid_name)
        h, w = 450, 800
        writer = cv2.VideoWriter(vid_path, self.fourcc, self.fps, (w, h))
        if not writer.isOpened():
            fourcc_alt = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(vid_path, cv2.CAP_FFMPEG, fourcc_alt, self.fps, (w, h))
            
        if writer.isOpened():
            for buf_frame in self.frame_buffer:
                resized_frame = cv2.resize(buf_frame, (w, h))
                writer.write(resized_frame)
            self.active_writers.append({'writer': writer, 'frames_left': int(self.fps * 5)})
        
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        violation_type = f"Hız İhlali ({speed:.1f} km/h)"
        
        # DB Kaydı
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (int(vehicle_id), self.name, violation_type, timestamp_str, img_name, vid_name))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()

        if self.on_violation:
            self.on_violation({
                "id": int(vehicle_id),
                "db_id": last_id,
                "cam_name": self.name,
                "type": violation_type,
                "time": timestamp_str,
                "img": img_name,
                "crop": crop_name,
                "video": vid_name,
                "speed": speed
            })

        self.last_alert_time = current_time
        self.violation_count += 1
        self.alert_timer = 35

    def process(self):
        frame_counter = 0
        results = None
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success: break
            
            h_orig, w_orig, _ = frame.shape
            frame_counter += 1
            
            # Çizim yapılacak kopya
            display_frame = frame.copy()

            # Her karede analiz yap
            results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], imgsz=640, conf=0.15, verbose=False)
                
            if results and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                
                for box, id in zip(boxes, ids):
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    
                    if id not in self.track_history:
                        self.track_history[id] = deque(maxlen=20)

                    # Video FPS'ine dayalı sanal zaman kullan (CPU kasması hızı bozmasın)
                    if not hasattr(self, 'frame_count'):
                        self.frame_count = 0
                    self.frame_count += 1
                    virtual_time = self.frame_count / self.fps
                    self.track_history[id].append((virtual_time, cy))
                    
                    # Hız Hesapla
                    speed = self.calculate_speed(self.track_history[id])
                    
                    # Görselleştirme (Stream için)
                    color = (0, 255, 0)
                    if speed > 20:
                        color = (0, 0, 255)
                        if id not in self.vehicle_logged:
                            self.vehicle_logged.add(id)
                            self.log_violation(id, frame, speed, box)
                            
                    cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), color, 3)
                    cv2.putText(display_frame, f"ID:{id} {speed:.1f} km/h", (box[0], box[1]-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Görsel efekt (ihlal anında kırmızı çerçeve)
            if self.alert_timer > 0:
                cv2.rectangle(display_frame, (0,0), (w_orig, h_orig), (0,0,255), 15)
                self.alert_timer -= 1

            preview = cv2.resize(display_frame, (800, 450))
            self.frame_buffer.append(preview)
            
            # Aktif video kayıtlarını güncelle
            for rec in self.active_writers[:]:
                rec['writer'].write(preview)
                rec['frames_left'] -= 1
                if rec['frames_left'] <= 0:
                    rec['writer'].release()
                    self.active_writers.remove(rec)

            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            
        self.cap.release()
        for rec in self.active_writers:
            rec['writer'].release()

    def get_frame(self):
        return self.current_frame
