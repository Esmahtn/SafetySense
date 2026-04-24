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

app = Flask(__name__)
CORS(app)

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
if not os.path.exists(VIOLATIONS_DIR):
    os.makedirs(VIOLATIONS_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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

init_db()
sse_clients = []
cameras = {}

class CameraEngine:
    def __init__(self, cam_id, name, source, model=None):
        self.cam_id = cam_id
        self.name = name
        self.source = source
        self.model = model if model else YOLO("yolo11n.pt")
        self.cap = cv2.VideoCapture(source)
        # Zaman Ayarı: Ters Yön için 2:40 (160 saniye)
        if "ch49" in source or "ters" in source.lower():
            self.cap.set(cv2.CAP_PROP_POS_MSEC, 160 * 1000)
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
        
        vid_path = os.path.join(VIOLATIONS_DIR, vid_name)
        writer = cv2.VideoWriter(vid_path, self.fourcc, self.fps, (800, 450))
        if writer.isOpened():
            for buf_frame in self.frame_buffer:
                writer.write(buf_frame)
            self.active_writers.append({'writer': writer, 'frames_left': int(self.fps * 5)})
        
        conn = sqlite3.connect(DB_PATH)
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
            # Her karede analiz yap (Debug için en hassas mod)
            results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], imgsz=640, conf=0.15, verbose=False)
            
            if results and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                for box, id in zip(boxes, ids):
                    cx, cy = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
                    
                    # Görselleştirme (Stream için)
                    color = (0, 255, 0)
                    label = f"Arac ID:{id}"
                    
                    if id in self.violators: 
                        color = (0, 0, 255)
                        label = "!!! TERS YON IHLAL !!!"
                        
                    cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), color, 4)
                    cv2.putText(display_frame, label, (box[0], box[1]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

                    # ROI Kontrolü (Merkez noktası yerine taban-orta noktası daha sağlıklı olabilir ama cx,cy ile devam ediyoruz)
                    if cv2.pointPolygonTest(self.roi_polygon, (cx, cy), False) < 0:
                        continue
                    
                    self.track_age[id] = self.track_age.get(id, 0) + 1
                    if id not in self.prev_positions: self.prev_positions[id] = cy; continue

                    dy = cy - self.prev_positions[id]
                    total_dy = cy - self.start_points.get(id, (cx, cy))[1]
                    total_dx = abs(cx - self.start_points.get(id, (cx, cy))[0])

                    # ── AKILLI YÖN FİLTRESİ ──
                    if dy > 2:
                        self.violation_scores[id] = 0
                        self.start_points[id] = (cx, cy)
                    
                    is_upward = total_dy < -40
                    is_vertical_dominant = abs(total_dy) > (total_dx * 1.2) # Biraz esnetildi
                    
                    if is_upward and is_vertical_dominant and id not in self.vehicle_logged:
                        if self.track_age.get(id, 0) >= 10: # Biraz esnetildi
                            self.vehicle_logged.add(id)
                            self.violators.add(id)
                            self.log_violation(id, frame, box)
                    
                    self.prev_positions[id] = cy

            preview = cv2.resize(display_frame, (800, 450))
            self.frame_buffer.append(preview)
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            
            if hasattr(self, 'active_writers'):
                for rec in self.active_writers[:]:
                    rec['writer'].write(preview)
                    rec['frames_left'] -= 1
                    if rec['frames_left'] <= 0: rec['writer'].release(); self.active_writers.remove(rec)
        self.cap.release()

    def get_frame(self): return self.current_frame

# --- Engine Setup ---
shared_model = YOLO("yolo11n.pt")
engine1 = CameraEngine(1, "Ana Koridor", "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi", model=shared_model)
# Yaya için 4:30 (270 saniye)
engine2 = PedestrianEngine(2, "Güvensiz Bölge", "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi")
engine2.cap_start_time = 270 # PedestrianEngine içinde bunu kullanacağız

# Hız için 2:30 (150 saniye)
engine3 = SpeedEngine(3, "Hız Koridoru", "video/192.168.12.5_ch50_20260422112304_20260422113058_hız.avi")
engine3.cap.set(cv2.CAP_PROP_POS_MSEC, 150 * 1000)

cameras = {1: engine1, 2: engine2, 3: engine3}

def notify(data):
    msg = json.dumps(data)
    for q in sse_clients: q.put(msg)
    img_path = os.path.join(VIOLATIONS_DIR, data.get('img', ''))
    vid_path = os.path.join(VIOLATIONS_DIR, data.get('video', ''))
    threading.Thread(target=send_violation_email, args=(data['cam_name'], data['type'], data['id'], data['time'], img_path, vid_path), daemon=True).start()

engine1.on_violation = notify
engine2.on_violation = notify
engine3.on_violation = notify

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM violations ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    history = []
    for r in rows:
        history.append({"id": r['id'], "vehicle_id": r['vehicle_id'], "cam_name": r['cam_name'], "type": r['type'], "time": r['timestamp'], "img": r['image_path'], "crop": r['image_path'].replace("full", "crop"), "video": None})
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
        conn = sqlite3.connect(DB_PATH)
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
