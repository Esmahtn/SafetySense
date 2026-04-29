import os
import cv2
import time
import threading
import numpy as np
import random
import sqlite3
import json
from datetime import datetime
from collections import deque
from queue import Queue
from flask import Flask, Response, jsonify, send_from_directory, request
from flask_cors import CORS
from ultralytics import YOLO
from pedestrian_engine import PedestrianEngine
from mailer import send_violation_email
from speed_engine import SpeedEngine
from async_camera import SmartCamera

app = Flask(__name__)
CORS(app)

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
if not os.path.exists(VIOLATIONS_DIR):
    os.makedirs(VIOLATIONS_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            cam_name TEXT,
            type TEXT,
            timestamp DATETIME,
            image_path TEXT,
            video_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def cleanup_old_files(days=3):
    """3 günden eski ihlal kayıtlarını diskten siler."""
    try:
        now = time.time()
        retention_sec = days * 24 * 3600
        count = 0
        if os.path.exists(VIOLATIONS_DIR):
            for f in os.listdir(VIOLATIONS_DIR):
                f_path = os.path.join(VIOLATIONS_DIR, f)
                if os.path.getmtime(f_path) < now - retention_sec:
                    if os.path.isfile(f_path):
                        os.remove(f_path)
                        count += 1
        if count > 0:
            print(f"[TEMİZLİK] {count} adet eski dosya temizlendi ({days} gün kuralı).")
    except Exception as e:
        print(f"[TEMİZLİK HATA] {e}")

def retention_worker():
    while True:
        cleanup_old_files(days=3)
        time.sleep(3600) # Her saat başı kontrol et

init_db()
threading.Thread(target=retention_worker, daemon=True).start()
sse_clients = []
cameras = {}

class CameraEngine:
    def __init__(self, cam_id, name, source, model=None, lock=None):
        self.cam_id = cam_id
        self.name = name
        self.source = source
        if model:
            self.model = model
        else:
            print(f"[{self.name}] YOLO VisDrone Model yükleniyor (Tamamen Çevrimdışı)...")
            self.model = YOLO("yolov8n-visdrone.pt")
        self.cap = SmartCamera(source, simulate_live=True)
        # Dakika 4.27'ye atla (267000 ms)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 267000)
        self.cap.start()
        self.current_frame = None
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.frame_buffer = deque(maxlen=int(self.fps * 4))
        self.active_writers = []
        self.violators = set()
        self.prev_positions = {}
        self.start_points = {}
        self.violation_scores = {}
        self.vehicle_logged = set()
        self.track_age = {}
        self.downward_streak = {}
        self.pos_history = {}
        self.post_reset_grace = {}
        self.last_alert_time = 0
        self.last_global_violation_time = 0
        self.violation_cooldown_sec = 20 # 20 saniye cooldown
        self.on_violation = None
        
        # Polygon ROI (User defined for ch49)
        self.roi_polygon = np.array([(381, 34), (298, 148), (213, 289), (563, 283), (403, 35)], dtype=np.int32)
        # Reference resolution for ROI was 800x450
        self.ref_width = 800
        self.ref_height = 450
        self.roi_scaled = False

    def log_violation(self, vehicle_id, frame, box=None):
        current_time = time.time()
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_file = datetime.now().strftime("%H%M%S_%f")
        rand_suffix = random.randint(1000, 9999)
        
        evidence_frame = frame.copy()
        if box is not None:
            cv2.rectangle(evidence_frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 8)
        
        cv2.putText(evidence_frame, f"TARIH: {timestamp_str}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 4)
        cv2.putText(evidence_frame, f"IHLAL: {self.name}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)

        img_name = f"ters_full_{timestamp_file}_{rand_suffix}.jpg"
        crop_name = f"ters_crop_{timestamp_file}_{rand_suffix}.jpg"
        vid_name = f"ters_vid_{timestamp_file}_{rand_suffix}.mp4"
        
        cv2.imwrite(os.path.join(VIOLATIONS_DIR, img_name), evidence_frame)
        if box is not None:
            try:
                y1, y2 = max(0, int(box[1]-100)), min(frame.shape[0], int(box[3]+100))
                x1, x2 = max(0, int(box[0]-100)), min(frame.shape[1], int(box[2]+100))
                cv2.imwrite(os.path.join(VIOLATIONS_DIR, crop_name), evidence_frame[y1:y2, x1:x2])
            except: cv2.imwrite(os.path.join(VIOLATIONS_DIR, crop_name), evidence_frame)
        
        # Video Kaydı: Bağımsız writer kullan
        vid_path = os.path.join(VIOLATIONS_DIR, vid_name)
        writer = cv2.VideoWriter(vid_path, self.fourcc, self.fps, (800, 450))
        email_info = {
            'cam_name': self.name,
            'violation_type': "Ters Yön İhlali",
            'vehicle_id': int(vehicle_id),
            'timestamp': timestamp_str,
            'image_path': os.path.join(VIOLATIONS_DIR, img_name),
            'video_path': vid_path,
            'crop_path': os.path.join(VIOLATIONS_DIR, crop_name)
        }
        if writer.isOpened():
            for buf_frame in self.frame_buffer:
                writer.write(buf_frame)
            self.active_writers.append({
                'writer': writer, 
                'frames_left': int(self.fps * 10), # 10 saniyelik tam kayit
                'email_info': email_info
            })
        
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(vehicle_id), self.name, "Ters Yön İhlali", timestamp_str, img_name, vid_name))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()

        if self.on_violation:
            self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": "Ters Yön İhlali", "time": timestamp_str, "img": img_name, "crop": crop_name, "video": vid_name})
        self.last_alert_time = current_time

    def process(self):
        frame_counter = 0
        results = None
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success: break
            h, w = frame.shape[:2]
            
            # ROI Ölçeklendirme (Gerekliyse)
            if not self.roi_scaled:
                scale_x = w / self.ref_width
                scale_y = h / self.ref_height
                scaled_points = []
                for px, py in self.roi_polygon:
                    scaled_points.append((int(px * scale_x), int(py * scale_y)))
                self.roi_polygon = np.array(scaled_points, dtype=np.int32)
                self.roi_scaled = True

            # GÖRÜNTÜ GÜNCELLEME (Turbo Akış)
            display_frame = frame.copy()
            
            # ROI Alanını çiz (Şeffaf Mavi)
            overlay = display_frame.copy()
            cv2.fillPoly(overlay, [self.roi_polygon], (255, 255, 0))
            cv2.addWeighted(overlay, 0.15, display_frame, 0.85, 0, display_frame)
            cv2.polylines(display_frame, [self.roi_polygon], True, (255, 255, 0), 2)

            frame_counter += 1
            # Stabilite ve Hız Modu (320px + 0.25 conf)
            results = self.model.track(frame, persist=True, classes=[3, 4, 5, 8, 9], imgsz=320, conf=0.25, iou=0.45, max_det=1000, tracker="botsort.yaml", verbose=False)
            
            if results and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                for box, id in zip(boxes, ids):
                    cx, cy = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
                    
                    # Görselleştirme (BÖLGE DIŞINDA OLSA BİLE ÇİZ)
                    color = (0, 255, 0)
                    label = f"Arac ID:{id}"
                    if id in self.violators: 
                        color = (0, 0, 255)
                        label = "!!! TERS YON IHLAL !!!"
                    cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), color, 4)
                    cv2.putText(display_frame, label, (box[0], box[1]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

                    # ROI Kontrolü (Aracın alt orta noktası - Tampon ucu için daha hassas)
                    base_x, base_y = cx, box[3] 
                    if cv2.pointPolygonTest(self.roi_polygon, (float(base_x), float(base_y)), False) < 0:
                        continue
                    
                    self.track_age[id] = self.track_age.get(id, 0) + 1
                    # Başlangıç noktasını sabitle (Eğer yoksa)
                    if id not in self.start_points:
                        self.start_points[id] = (cx, cy)
                    
                    if id not in self.prev_positions:
                        self.prev_positions[id] = cy
                        continue
                        
                    dy = cy - self.prev_positions[id]
                    total_dy = cy - self.start_points.get(id, (cx, cy))[1]
                    total_dx = abs(cx - self.start_points.get(id, (cx, cy))[0])

                    # ── AKILLI YÖN FİLTRESİ ──
                    if dy > 10: # Ciddi bir asagi gidis yoksa sifirlama (Sarsinti onleyici)
                        self.violation_scores[id] = 0
                        self.start_points[id] = (cx, cy)
                    
                    is_upward = total_dy < -3 # Sadece 3 piksel dikey hareket yetti (Iskence Hassasiyeti)
                    is_vertical_dominant = abs(total_dy) > (total_dx * 0.2) # En ufak yukari egilimi yakalae eder
                    
                    if is_upward and is_vertical_dominant:
                        current_time = time.time()
                        is_spam = (current_time - self.last_global_violation_time) < self.violation_cooldown_sec
                        
                        if not is_spam and id not in self.vehicle_logged:
                            if self.track_age.get(id, 0) >= 1: # İLK KAREDE YAKALA (Gecikme Sıfır)
                                self.last_global_violation_time = current_time
                                self.vehicle_logged.add(id)
                                self.violators.add(id)
                                self.log_violation(id, frame, box)
                    
                    self.prev_positions[id] = cy

            preview = cv2.resize(display_frame, (800, 450))
            self.frame_buffer.append(preview)
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            
            # CPU yükünü dengele ve akışı sabitle
            time.sleep(0.01)
            
            if hasattr(self, 'active_writers'):
                for rec in self.active_writers[:]:
                    rec['writer'].write(preview)
                    rec['frames_left'] -= 1
                    if rec['frames_left'] <= 0: 
                        rec['writer'].release()
                        self.active_writers.remove(rec)
        self.cap.release()
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
                        crop_path=info.get('crop_path')
                    )

    def get_frame(self): return self.current_frame

# --- Engine Setup ---
# ÖRNEK: rtsp://kullanici:sifre@ip_adresi:port/yol
# Kendi bilgilerinizle değiştirmek için aşağıdaki satırları kullanabilirsiniz:

# engine1 = CameraEngine(1, "Ana Koridor", "rtsp://admin:Sifre123@192.168.1.50:554/Streaming/Channels/101")
# engine2 = PedestrianEngine(2, "Güvensiz Bölge", "rtsp://admin:Sifre123@192.168.1.51:554/Streaming/Channels/101")
# engine3 = SpeedEngine(3, "Hız Koridoru", "rtsp://admin:Sifre123@192.168.1.52:554/Streaming/Channels/101")

# Not: Test için video dosyası kullanmak isterseniz eski satırlar aşağıdadır:
# engine1 = CameraEngine(1, "Ana Koridor", "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi")
engine2 = PedestrianEngine(2, "Güvensiz Bölge", "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi")
# engine3 = SpeedEngine(3, "Hız Koridoru", "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi")

cameras = {2: engine2}

def notify(data):
    msg = json.dumps(data)
    for q in sse_clients: q.put(msg)
    # E-posta gönderimi artık her engine'in kendi içindeki deferred logic'i (active_writers) ile yapılıyor.

# engine1.on_violation = notify
engine2.on_violation = notify
# engine3.on_violation = notify

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM violations ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    history = []
    for r in rows:
        vid = r['vehicle_id']
        if isinstance(vid, bytes):
            vid = int.from_bytes(vid, byteorder='little')
        history.append({"id": r['id'], "vehicle_id": vid, "cam_name": r['cam_name'], "type": r['type'], "time": r['timestamp'], "img": r['image_path'], "crop": r['image_path'].replace("full", "crop"), "video": None})
    cursor.execute('SELECT COUNT(*) FROM violations'); total = cursor.fetchone()[0]
    conn.close()
    return jsonify({"total": total, "history": history})

@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id):
    def generate():
        engine = cameras.get(cam_id)
        while True:
            if engine:
                frame = engine.get_frame()
                if frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.02)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vehicle_stream')
def vs(): return video_feed(1)
@app.route('/pedestrian_stream')
def ps(): return video_feed(2)
@app.route('/speed_stream')
def ss(): return video_feed(3)

@app.route('/screenshots/<path:filename>')
def get_screenshot(filename): return send_from_directory(VIOLATIONS_DIR, filename)

@app.route('/stream')
def stream():
    def event_stream():
        q = Queue()
        sse_clients.append(q)
        try:
            while True:
                msg = q.get()
                yield f"data: {msg}\n\n"
        except GeneratorExit:
            sse_clients.remove(q)

    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/delete_violation/<int:id>', methods=['DELETE'])
def delete_violation(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM violations WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/delete_multiple', methods=['POST'])
def delete_multiple():
    data = request.json
    ids = data.get('ids', [])
    if ids:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(ids))
        cursor.execute(f'DELETE FROM violations WHERE id IN ({placeholders})', ids)
        conn.commit()
        conn.close()
    return jsonify({"status": "success"})

@app.route('/videos/<path:filename>')
def get_video(filename):
    return send_from_directory(VIOLATIONS_DIR, filename)

if __name__ == '__main__':
    for e in cameras.values():
        threading.Thread(target=e.process, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
