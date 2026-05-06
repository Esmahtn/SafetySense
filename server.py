import os
import cv2
import time
import math
import threading
from threading import Lock
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
from config import get_source

app = Flask(__name__)
CORS(app)

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
os.makedirs(VIOLATIONS_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20); cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;"); cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute('CREATE TABLE IF NOT EXISTS violations (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, cam_name TEXT, type TEXT, timestamp DATETIME, image_path TEXT, video_path TEXT)')
    conn.commit(); conn.close()

init_db()
sse_clients, cameras = [], {}

# Kameralar arası ortak ihlal kaydı: {track_id: son_ihlal_zamani}
# Aynı kişi hem hız hem yaya koridorunda tespit edilirse tekrar loglanmaz.
shared_violation_log = {}
shared_violation_lock = Lock()  # Thread-safe erişim için

class CameraEngine:
    def __init__(self, cam_id, name, source, model=None):
        self.cam_id, self.name, self.source = cam_id, name, source
        self.cam_id, self.name = cam_id, name
        self.source, self.name, self.roi_polygon, self.on_violation = source, name, [(383, 32), (92, 276), (630, 273), (402, 31)], None
        self.cap = SmartCamera(source, simulate_live=True); self.cap.start()
        self.model = None; self.model_name = "yolo11s.pt"
        self.ref_width, self.ref_height = 1920, 1080
        self.roi_scaled = False; self.middle_y = None
        self.prev_positions = {}
        self.frame_count = 0
        
        # ⭐ Histerezis ve Karar Birikimi (M-out-of-N)
        self.violation_buffer = {} # ID: [is_in_roi, is_in_roi, ...] (son 15 kare)
        
        # ⭐ Mekansal Soğuma (Alarm Ledger) - Global veya Sınıf bazlı
        self.alarm_ledger = [] # [(timestamp, cx, cy, type), ...]
        self.spatial_threshold = 150 # piksel (aynı bölge sayılması için mesafe)
        self.temporal_threshold = 15 # saniye (aynı bölgede alarm basmama süresi)
        
        self.shared_violation_log = {}; self.shared_violation_lock = threading.Lock()
        self.violation_cooldown_sec = 300 # ⭐ 5 Dakika soğuma
        self._recent_violation_positions = [] # (cx, cy, timestamp)
        self.position_cooldown_radius = 150    # ⭐ 150 piksel (Geri döndük)
        self.position_cooldown_sec = 10         # ⭐ 10 saniye (Konum bazlı)
        # Bellek temizliği
        self._last_cleanup = time.time()
        self._cleanup_interval = 60
        self.on_violation = None
        self.roi_polygon = np.array([(383, 32), (92, 276), (630, 273), (402, 31)], dtype=np.int32)
        self.ref_width, self.ref_height, self.roi_scaled, self.middle_y = 800, 450, False, None

    def _is_position_in_cooldown(self, cx, cy):
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

    def _is_spatial_duplicate(self, cx, cy, v_type):
        """⭐ Mekansal Soğuma: Aynı bölgede yakın zamanda alarm verildi mi?"""
        now = time.time()
        # Eski kayıtları temizle (30 saniyeden eski olanlar)
        self.alarm_ledger = [a for a in self.alarm_ledger if (now - a[0]) < 30]
        
        v_cat = v_type.split('(')[0].strip()
        for ts, ax, ay, atype in self.alarm_ledger:
            a_cat = atype.split('(')[0].strip()
            if a_cat == v_cat:
                dist = ((cx - ax)**2 + (cy - ay)**2)**0.5
                if dist < self.spatial_threshold and (now - ts) < self.temporal_threshold:
                    return True
        return False

    def log_violation(self, vehicle_id, frame, box=None, violation_type="Ters Yön İhlali"):
        current_time = time.time()
        
        if box is not None:
            cx, cy = int((box[0] + box[2]) / 2), int(box[3]) # BOTTOM-CENTER
            
            # 1. Mekansal Soğuma Kontrolü (ID bağımsız koruma)
            if self._is_spatial_duplicate(cx, cy, violation_type):
                return
                
        v_cat = violation_type.split('(')[0].strip()
        # 2. Thread-safe ID + Kategori bazlı kontrol
        with self.shared_violation_lock:
            key = f"{vehicle_id}_{v_cat}"
            last_time = self.shared_violation_log.get(key, 0)
            if (current_time - last_time) < self.violation_cooldown_sec:
                return
            self.shared_violation_log[key] = current_time
            
        # ⭐ Ledger'a kaydet
        if box is not None:
            self.alarm_ledger.append((current_time, cx, cy, violation_type))
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        img_name = f"ters_{datetime.now().strftime('%H%M%S')}_{random.randint(1000,9999)}.jpg"
        img_path = os.path.join(VIOLATIONS_DIR, img_name)
        evidence = frame.copy()
        if box is not None: cv2.rectangle(evidence, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 10)
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 100), (0, 0, 0), -1)
        cv2.putText(evidence, f"IHLAL: {violation_type.upper()}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(evidence, f"TARIH: {ts_str} | ID: {vehicle_id}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(img_path, evidence)
        conn = sqlite3.connect(DB_PATH, timeout=20); cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(vehicle_id), self.name, violation_type, ts_str, img_name, ""))
        conn.commit(); last_id = cursor.lastrowid; conn.close()
        # 4️⃣ E-posta bildirimi
        from mailer import send_violation_email
        send_violation_email(self.name, violation_type, int(vehicle_id), ts_str, img_path)
        if self.on_violation: self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": violation_type, "time": ts_str, "img": img_name})

    def process(self):
        while True:
            try:
                if self.model is None and hasattr(self, 'model_name') and self.model_name: self.model = YOLO(self.model_name); self.model_name = None
                if not self.cap.isOpened(): time.sleep(1); continue
                ret, frame = self.cap.read()
                if not ret: time.sleep(0.01); continue
                
                h, w = frame.shape[:2]
                if not self.roi_scaled:
                    sx, sy = w / self.ref_width, h / self.ref_height
                    self.roi_polygon = np.array([(int(px*sx), int(py*sy)) for px, py in self.roi_polygon], dtype=np.int32); self.roi_scaled = True
                if self.middle_y is None: self.middle_y = int(h * 0.5)
                
                display_frame = frame.copy()
                cv2.polylines(display_frame, [self.roi_polygon], True, (255, 255, 0), 2); cv2.line(display_frame, (0, self.middle_y), (w, self.middle_y), (0, 255, 255), 3)
                
                self.frame_count += 1
                if self.model: 
                    results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], imgsz=640, conf=0.35, tracker="botsort_custom.yaml", verbose=False)
                    active_ids = []
                    if results and results[0].boxes.id is not None:
                        boxes, ids = results[0].boxes.xyxy.cpu().numpy(), results[0].boxes.id.cpu().numpy().astype(int)
                        active_ids = ids
                        for box, id in zip(boxes, ids):
                            cx, cy = int((box[0]+box[2])/2), int(box[3]) # ⭐ BOTTOM-CENTER
                            
                            # 1️⃣ ROI Kontrolü (Bottom-Center üzerinden)
                            is_in_roi = cv2.pointPolygonTest(self.roi_polygon, (float(cx), float(cy)), False) >= 0
                            
                            # 2️⃣ Histerezis (Karar Birikimi)
                            if id not in self.violation_buffer: self.violation_buffer[id] = []
                            self.violation_buffer[id].append(is_in_roi)
                            if len(self.violation_buffer[id]) > 8: self.violation_buffer[id].pop(0)
                            
                            # Son 8 karenin en az 3'ünde ROI içindeyse "İhlal Durumu" onaylanır
                            roi_confirmed = sum(self.violation_buffer[id]) >= 3
                            
                            if not is_in_roi: 
                                self.prev_positions.pop(id, None); continue
                                
                            # 3️⃣ İhlal Kararı (Hız Koridoru ile aynı kararlı yapı)
                            if id in self.prev_positions and roi_confirmed:
                                p_y = self.prev_positions[id]
                                # Ters Yön: Aşağıdan Yukarı (Y değeri azalıyor)
                                if p_y > self.middle_y and cy <= self.middle_y:
                                    self.log_violation(id, frame, box)
                                
                            self.prev_positions[id] = cy
                            # Çizim (ID ve Durum)
                            label = f"ID: {id}"
                            if roi_confirmed:
                                color = (0, 0, 255) # Kırmızı (Bölgede onaylandı)
                            else:
                                color = (0, 255, 0) # Yeşil
                                
                            cv2.rectangle(display_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
                            cv2.putText(display_frame, label, (int(box[0]), int(box[1]) - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    # Buffer Temizliği (Artık görünmeyen ID'ler)
                    for rid in list(self.violation_buffer.keys()):
                        if rid not in active_ids: del self.violation_buffer[rid]
                
                # Görüntüyü güncelle
                preview = cv2.resize(display_frame, (800, 450)); _, buffer = cv2.imencode('.jpg', preview); self.current_frame = buffer.tobytes()
                time.sleep(0.01)
            except Exception as e:
                print(f"CameraEngine Hatası: {e}")
                time.sleep(1)
    def get_frame(self): return self.current_frame

def notify(data):
    msg = json.dumps(data)
    for q in sse_clients: q.put(msg)

def main():
    init_db()
    
    source1 = get_source("ANA_KORIDOR")
    source2 = get_source("GUVENSIZ_BOLGE")
    source3 = get_source("HIZ_KORIDORU")

    engine1 = CameraEngine(1, "Ana Koridor", source1)
    engine2 = PedestrianEngine(2, "Güvensiz Bölge", source2)
    engine3 = SpeedEngine(3, "Hız Koridoru", source3)
    # Hız ve yaya koridorları aynı ortak ihlal kaydını ve lock'ı paylaşır
    engine2.shared_violation_log = shared_violation_log
    engine2.shared_violation_lock = shared_violation_lock
    engine3.shared_violation_log = shared_violation_log
    engine3.shared_violation_lock = shared_violation_lock
    engine1.on_violation = engine2.on_violation = engine3.on_violation = notify
    cameras[1], cameras[2], cameras[3] = engine1, engine2, engine3
    for e in cameras.values(): threading.Thread(target=e.process, daemon=True).start()

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    cursor.execute('SELECT * FROM violations ORDER BY timestamp DESC'); rows = cursor.fetchall(); history = []
    for r in rows: history.append({"id": r['id'], "vehicle_id": r['vehicle_id'], "cam_name": r['cam_name'], "type": r['type'], "time": r['timestamp'], "img": r['image_path']})
    cursor.execute('SELECT COUNT(*) FROM violations'); total = cursor.fetchone()[0]; conn.close()
    return jsonify({"total": total, "history": history})

@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id):
    def generate():
        engine = cameras.get(cam_id)
        while True:
            if engine:
                frame = engine.get_frame()
                if frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03)
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
        q = Queue(); sse_clients.append(q)
        try:
            while True: yield f"data: {q.get()}\n\n"
        except GeneratorExit: sse_clients.remove(q)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/delete_violation/<int:id>', methods=['DELETE'])
def delete_violation(id):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor(); cursor.execute('DELETE FROM violations WHERE id = ?', (id,)); conn.commit(); conn.close(); return jsonify({"status": "success"})

@app.route('/delete_multiple', methods=['POST'])
def delete_multiple():
    ids = request.json.get('ids', [])
    if not ids: return jsonify({"status": "error", "message": "No IDs provided"}), 400
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute(f'DELETE FROM violations WHERE id IN ({",".join(["?"]*len(ids))})', ids)
    conn.commit(); conn.close()
    return jsonify({"status": "success"})

@app.route('/clear_all_violations', methods=['DELETE'])
def clear_all_violations():
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor(); cursor.execute('DELETE FROM violations'); conn.commit(); conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    main()  # main içinde zaten engine threadleri başlatılıyor
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
