import cv2
import math
import numpy as np
import time
import sqlite3
import os
from collections import deque
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from mailer import send_violation_email
from async_camera import SmartCamera



class PedestrianEngine:
    def __init__(self, camera_id, camera_name, source, model=None):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source = source
        
        if model:
            self.model = model
        else:
            print(f"[{self.camera_name}] YOLO VisDrone Model yükleniyor...")
            model_path = hf_hub_download(repo_id="mshamrai/yolov8n-visdrone", filename="best.pt")
            self.model = YOLO(model_path)
        
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
        self.last_global_violation_time = 0 # ID değişse bile mükerrer kaydı önlemek için global cooldown
        self.last_violation_time = 0    # Spam önleme için cooldown
        self.violation_cooldown_sec = 20 # Aynı kameradan 20 saniyede 1 kayıt (ID'den bağımsız)
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
        is_spam = (current_time - self.last_global_violation_time) < self.violation_cooldown_sec
        if is_spam:
            return
        
        self.last_global_violation_time = current_time
        
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
            
            email_info = {
                "cam_name": self.camera_name,
                "violation_type": "Yaya İhlali",
                "vehicle_id": person_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "image_path": img_path,
                "video_path": vid_path,
                "crop_path": crop_path
            }
            
            self.active_writers.append({
                'writer': writer, 
                'frames_left': int(self.fps * 10), # İhlalden sonra 10 saniye kayıt
                'email_info': email_info
            })
        
        db_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect('violations.db', timeout=20)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (person_id, self.camera_name, "Yaya İhlali", db_timestamp, img_filename, vid_filename))
        violation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[{self.camera_name}] YAYA IHLALI: ID {person_id} kaydedildi!")

        # E-posta gönderimi video kaydı tamamlanınca (active_writers içinde) tetiklenecek.

        if self.on_violation:
            self.on_violation({
                "id": violation_id,
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "vehicle_id": person_id,
                "type": "Yaya Ihlali",
                "image_path": img_path,
                "timestamp": db_timestamp,
                "video_path": vid_path
            })

    def process(self):
        cap = SmartCamera(self.source, simulate_live=True)
        # Dakika 4.27'ye atla (4*60+27 = 267 saniye = 267000 ms)
        cap.set(cv2.CAP_PROP_POS_MSEC, 267000)
        cap.start()
            
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
        
        results = None
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
            cv2.putText(display_frame, "YAYA YASAK ALAN", (self.roi_polygon[0][0], self.roi_polygon[0][1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)

            # Hız ve Akıcılık Modu (320px)
            results = self.model.track(frame, persist=True, classes=[0, 1], conf=0.30, iou=0.45, max_det=1000, imgsz=320, tracker="botsort.yaml", verbose=False)
            
            if results is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                
                for box, track_id in zip(boxes, track_ids):
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Fiziksel Oran Filtresi (Aspect Ratio)
                    # İnsan boyu eninden uzundur. Direkleri ve kutuları eliyoruz.
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    if aspect_ratio < 0.1 or aspect_ratio > 1.2:
                        continue  # Bu bir direk veya makine olabilir
                        
                    in_roi = False
                    
                    # Bounding Box'ın Alt-Orta Noktası (Kişinin ayaklarının bastığı yer)
                    bottom_center = (float((x1 + x2) / 2), float(y2))
                    cv2.circle(display_frame, (int(bottom_center[0]), int(bottom_center[1])), 5, (255, 255, 0), -1) # Sarı nokta
                    
                    if cv2.pointPolygonTest(self.roi_polygon, bottom_center, False) >= 0:
                        in_roi = True
                            
                    # İhlal Kontrolü
                    if in_roi:
                        self.person_in_roi_frames[track_id] = self.person_in_roi_frames.get(track_id, 0) + 1
                        
                        # 2 frame üst üste bölgedeyse ihlal say (Hızlı Tepki)
                        if self.person_in_roi_frames[track_id] >= 2:
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
            
            # CPU yükünü dengele ve akışı sabitle
            time.sleep(0.01)
            
            # Geriye dönük video için tampona at
            self.frame_buffer.append(preview)
            
            # Kayıt devam ediyorsa yeni frame'i yaz (Tüm aktif yazıcılara)
            if hasattr(self, 'active_writers'):
                for rec in self.active_writers[:]:
                    rec['writer'].write(preview)
                    rec['frames_left'] -= 1
                    if rec['frames_left'] <= 0:
                        rec['writer'].release()
                        if 'email_info' in rec:
                            info = rec['email_info']
                            send_violation_email(
                                cam_name=info['cam_name'],
                                violation_type=info['violation_type'],
                                vehicle_id=info['vehicle_id'],
                                timestamp=info['timestamp'],
                                image_path=info['image_path'],
                                video_path=info['video_path'],
                                crop_path=info.get('crop_path')
                            )
                        self.active_writers.remove(rec)
            
            # Sadece tekli test modunda pencereyi göster
            if __name__ == "__main__":
                cv2.imshow(f"{self.camera_name} - Yaya Tespiti", preview)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
            
        cap.release()
        if hasattr(self, 'active_writers'):
            for rec in self.active_writers:
                rec['writer'].release()
                if 'email_info' in rec:
                    info = rec['email_info']
                    send_violation_email(
                        cam_name=info['cam_name'],
                        violation_type=info['violation_type'],
                        vehicle_id=info['vehicle_id'],
                        timestamp=info['timestamp'],
                        image_path=info['image_path'],
                        video_path=info['video_path'],
                        crop_path=info['crop_path']
                    )
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
