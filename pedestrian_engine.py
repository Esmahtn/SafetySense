import cv2
import math
import numpy as np
import time
import sqlite3
import os
from collections import deque
from ultralytics import YOLO



class PedestrianEngine:
    def __init__(self, camera_id, camera_name, source):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source = source
        
        # YOLOv8 pose modeli (insan tespiti ve iskelet çıkarma)
        # Standart YOLOv8 nesne tespiti (HAFİF MODEL - KASMA YAPMAZ)
        print(f"[{self.camera_name}] YOLO standart model yukleniyor (Hafif)...")
        self.model = YOLO("yolo11n.pt")
        
        self.current_frame = None
        self.running = True
        
        # ROI Alanı (select_roi.py'den alınan koordinatlar)
        self.roi_polygon = np.array([
            (38, 446), (171, 346), (289, 258), (372, 199), 
            (442, 148), (485, 124), (521, 96), (533, 86), 
            (576, 91), (552, 192), (502, 329), (456, 448)
        ], dtype=np.int32)
        
        # Orijinal video çözünürlüğüne göre ölçeklendirme için referans çözünürlük (seçici 800x450'de çalıştı)
        self.ref_width = 800
        self.ref_height = 450
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.roi_scaled = False

        # State yönetimi
        self.person_in_roi_frames = {}  # ID -> ROI içinde geçirdiği frame sayısı
        self.pedestrian_logged = set()  # Zaten loglanan ID'ler
        self.last_violation_time = 0    # Spam önleme için cooldown
        self.violation_cooldown_sec = 30 # Aynı kameradan 30 saniyede 1 mail
        self.fps = 30
        
        # Video kayıt değişkenleri (avc1 - H264)
        self.fourcc = cv2.VideoWriter_fourcc(*'avc1')
        self.frame_buffer = deque(maxlen=int(self.fps * 4)) # 4 saniyelik geriye dönük tampon
        self.recording_frames_left = 0
        self.current_writer = None
        
        # Olay kayıt klasörü
        os.makedirs("ihlal_kayitlari", exist_ok=True)
        
        # SSE için callback
        self.on_violation = None

    def log_violation(self, person_id, frame, box=None):
        # Spam Önleme: Son 30 saniyede aynı kameradan uyarı gittiyse sadece DB'ye yaz, mail/sse atma
        current_time = time.time()
        is_spam = (current_time - self.last_violation_time) < self.violation_cooldown_sec
        
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        rand_suffix = np.random.randint(1000, 9999)
        img_filename = f"yaya_{self.camera_id}_{person_id}_{timestamp_str}_{rand_suffix}.jpg"
        vid_filename = f"yaya_{self.camera_id}_{person_id}_{timestamp_str}_{rand_suffix}.mp4"
        
        img_path = f"ihlal_kayitlari/{img_filename}"
        vid_path = f"ihlal_kayitlari/{vid_filename}"
        
        cv2.imwrite(img_path, frame)
        
        # CROP (Yakınlaştırma) Kaydet
        crop_name = f"crop_{img_filename}"
        crop_path = f"ihlal_kayitlari/{crop_name}"
        if box is not None:
            try:
                y1, y2 = max(0, int(box[1]-50)), min(frame.shape[0], int(box[3]+50))
                x1, x2 = max(0, int(box[0]-50)), min(frame.shape[1], int(box[2]+50))
                crop_img = frame[y1:y2, x1:x2]
                cv2.imwrite(crop_path, crop_img)
            except: cv2.imwrite(crop_path, frame)
        else:
            cv2.imwrite(crop_path, frame)
        
        # Video Kaydı: Bağımsız writer kullan
        vid_path = f"ihlal_kayitlari/{vid_filename}"
        h, w = 450, 800 # Sabitlenmiş preview boyutu
        writer = cv2.VideoWriter(vid_path, cv2.CAP_FFMPEG, self.fourcc, self.fps, (w, h))
        if not writer.isOpened():
            fourcc_alt = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(vid_path, cv2.CAP_FFMPEG, fourcc_alt, self.fps, (w, h))
            
        if writer.isOpened():
            for buf_frame in self.frame_buffer:
                # Tampondaki karelerin boyutu uyuşmayabilir (preview vs original), boyutlandır
                resized = cv2.resize(buf_frame, (w, h))
                writer.write(resized)
            if not hasattr(self, 'active_writers'): self.active_writers = []
            self.active_writers.append({'writer': writer, 'frames_left': int(self.fps * 5)})
        
        db_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect('violations.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (person_id, self.camera_name, "Yaya İhlali", db_timestamp, img_filename, vid_filename))
        violation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[{self.camera_name}] YAYA IHLALI: ID {person_id} kaydedildi!")
        
        if not is_spam:
            if self.on_violation:
                self.on_violation({
                    "id": violation_id,
                    "camera_id": self.camera_id,
                    "camera_name": self.camera_name,
                    "vehicle_id": person_id,
                    "type": "Yaya Ihlali",
                    "image_path": img_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "video_path": vid_path
                })
            self.last_violation_time = current_time

    def process(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"[{self.camera_name}] HATA: Video/Kamera acilamadi: {self.source}")
            return
            
        # Videoyu belirtilen süreden (Varsayılan 4:30) başlat
        start_sec = getattr(self, 'cap_start_time', 270)
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
            
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # ROI koordinatlarını gerçek video çözünürlüğüne uyarla
        self.scale_x = width / self.ref_width
        self.scale_y = height / self.ref_height
        
        scaled_roi = []
        for x, y in self.roi_polygon:
            scaled_roi.append((int(x * self.scale_x), int(y * self.scale_y)))
        self.roi_polygon = np.array(scaled_roi, dtype=np.int32)
        self.roi_scaled = True
        
        frame_count = 0
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            frame_count += 1
            
            # GÖRÜNTÜ GÜNCELLEME (Turbo): Analizden bağımsız olarak her kareyi ekrana bas
            display_frame = frame.copy()
            # ROI bölgesini çiz (Şeffaf Sarı)
            overlay = display_frame.copy()
            cv2.fillPoly(overlay, [self.roi_polygon], (0, 255, 255))
            cv2.addWeighted(overlay, 0.2, display_frame, 0.8, 0, display_frame)
            cv2.polylines(display_frame, [self.roi_polygon], True, (0, 200, 200), 2)
            
            preview = cv2.resize(display_frame, (800, 450))
            self.frame_buffer.append(preview)
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()

            # ANALİZ: Her 3 kareden sadece 1'inde yap
            if frame_count % 3 != 0:
                continue
            
            results = self.model.track(frame, persist=True, classes=[0], conf=0.15, imgsz=480, verbose=False)
            
            # Görselleştirme için kopya
            display_frame = frame.copy()
            
            # ROI bölgesini çiz (Şeffaf Sarı)
            overlay = display_frame.copy()
            cv2.fillPoly(overlay, [self.roi_polygon], (0, 255, 255))
            cv2.addWeighted(overlay, 0.2, display_frame, 0.8, 0, display_frame)
            cv2.polylines(display_frame, [self.roi_polygon], True, (0, 200, 200), 2)
            cv2.putText(display_frame, "YAYA YASAK ALAN", (self.roi_polygon[0][0], self.roi_polygon[0][1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)
            
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                
                for box, track_id in zip(boxes, track_ids):
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Fiziksel Oran Filtresi (Aspect Ratio)
                    # İnsan boyu eninden uzundur. Direkleri ve kutuları eliyoruz.
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    if aspect_ratio < 0.2 or aspect_ratio > 0.85:
                        continue  # Bu bir direk veya makine olabilir
                        
                    in_roi = False
                    
                    # Bounding Box'ın Alt-Orta Noktası (Kişinin ayaklarının bastığı yer)
                    bottom_center = (int((x1 + x2) / 2), int(y2))
                    cv2.circle(display_frame, bottom_center, 5, (255, 255, 0), -1) # Sarı nokta
                    
                    if cv2.pointPolygonTest(self.roi_polygon, bottom_center, False) >= 0:
                        in_roi = True
                            
                    # İhlal Kontrolü
                    if in_roi:
                        self.person_in_roi_frames[track_id] = self.person_in_roi_frames.get(track_id, 0) + 1
                        
                        # 5 frame üst üste bölgedeyse ihlal say
                        if self.person_in_roi_frames[track_id] >= 5:
                            if track_id not in self.pedestrian_logged:
                                self.pedestrian_logged.add(track_id)
                                self.log_violation(track_id, frame, box)
                            
                        # Bölgedeki kişiyi kırmızı çerçeve ile göster
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        cv2.putText(display_frame, f"YAYA! ID:{track_id}", (x1, y1-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        # Bölgede değilse sayacı sıfırla
                        if track_id in self.person_in_roi_frames:
                            self.person_in_roi_frames[track_id] = 0
                            
                        # Normal kişiyi yeşil çerçeve ile göster
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(display_frame, f"Person ID:{track_id}", (x1, y1-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Dashboard vs için anlık kareyi kaydet
            preview = cv2.resize(display_frame, (800, 450))
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            
            # Geriye dönük video için tampona at
            self.frame_buffer.append(preview)
            
            # Kayıt devam ediyorsa yeni frame'i yaz (Tüm aktif yazıcılara)
            if hasattr(self, 'active_writers'):
                for rec in self.active_writers[:]:
                    rec['writer'].write(preview)
                    rec['frames_left'] -= 1
                    if rec['frames_left'] <= 0:
                        rec['writer'].release()
                        self.active_writers.remove(rec)
            
            # Sunucu modunda pencereyi kapat (Kilitlenmeyi önler)
            # cv2.imshow(f"{self.camera_name} - Yaya Tespiti", preview)
            # if cv2.waitKey(1) & 0xFF == ord('q'): break
            
        cap.release()
        if self.current_writer is not None:
            self.current_writer.release()
        cv2.destroyWindow(f"{self.camera_name} - Yaya Tespiti")

    def get_frame(self):
        return self.current_frame

if __name__ == "__main__":
    print("=== Yaya Tespiti Tekli Test Modu ===")
    video_path = "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"
    if not os.path.exists(video_path):
        print(f"HATA: Video bulunamadi -> {video_path}")
    else:
        engine = PedestrianEngine(99, "Test Kamera", video_path)
        engine.process()
