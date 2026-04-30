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
os.makedirs(VIOLATIONS_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20); cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;"); cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute('CREATE TABLE IF NOT EXISTS violations (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, cam_name TEXT, type TEXT, timestamp DATETIME, image_path TEXT, video_path TEXT)')
    conn.commit(); conn.close()

init_db()
sse_clients, cameras = [], {}

class CameraEngine:
    def __init__(self, cam_id, name, source, model=None):
        self.cam_id, self.name, self.source = cam_id, name, source
        self.model_name = "yolo11n.pt" if not model else None
        self.model = model
        self.cap = SmartCamera(source, simulate_live=False)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 160000) # 2:40
        self.cap.start()
        self.current_frame = None
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.frame_buffer = deque(maxlen=int(self.fps * 4))
        self.violators, self.prev_positions, self.start_points = set(), {}, {}
        self.last_global_violation_time, self.violation_cooldown_sec = 0, 15
        self.on_violation = None
        self.roi_polygon = np.array([(383, 32), (92, 276), (630, 273), (402, 31)], dtype=np.int32)
        self.ref_width, self.ref_height, self.roi_scaled, self.middle_y = 800, 450, False, None

    def log_violation(self, vehicle_id, frame, box=None, violation_type="Ters Yön İhlali"):
        if (time.time() - self.last_global_violation_time) < self.violation_cooldown_sec: return
        self.last_global_violation_time = time.time()
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
        if self.on_violation: self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": violation_type, "time": ts_str, "img": img_name})

    def process(self):
        while True:
            if self.model is None and hasattr(self, 'model_name') and self.model_name: self.model = YOLO(self.model_name); self.model_name = None
            if not self.cap.isOpened(): time.sleep(1); continue
            ret, frame = self.cap.read()
            if not ret: time.sleep(0.01); continue
            h, w = frame.shape[:2]
            if not self.roi_scaled:
                sx, sy = w / self.ref_width, h / self.ref_height
                self.roi_polygon = np.array([(int(px*sx), int(py*sy)) for px, py in self.roi_polygon], dtype=np.int32); self.roi_scaled = True
            if self.middle_y is None: self.middle_y = int(h * 0.6)
            display_frame = frame.copy()
            cv2.polylines(display_frame, [self.roi_polygon], True, (255, 255, 0), 2); cv2.line(display_frame, (0, self.middle_y), (w, self.middle_y), (0, 255, 255), 3)
            if self.model:
                results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], imgsz=640, conf=0.35, tracker="botsort.yaml", verbose=False)
                if results and results[0].boxes.id is not None:
                    boxes, ids = results[0].boxes.xyxy.cpu().numpy(), results[0].boxes.id.cpu().numpy().astype(int)
                    for box, id in zip(boxes, ids):
                        cx, cy = int((box[0]+box[2])/2), int((box[1]+box[3])/2); base_y = int(box[3])
                        if cv2.pointPolygonTest(self.roi_polygon, (float(cx), float(cy)), False) < 0: continue
                        if id not in self.start_points: self.start_points[id] = (cx, base_y)
                        if id not in self.prev_positions: self.prev_positions[id] = base_y; continue
                        p_y, (s_x, s_y) = self.prev_positions[id], self.start_points[id]
                        dy, dx = s_y - base_y, abs(s_x - cx)
                        if dy > (dx * 1.5) and ((p_y > self.middle_y and base_y <= self.middle_y) or (base_y < self.middle_y and dy > 12)): self.log_violation(id, frame, box)
                        self.prev_positions[id] = base_y
                        cv2.rectangle(display_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)
            preview = cv2.resize(display_frame, (800, 450)); _, buffer = cv2.imencode('.jpg', preview); self.current_frame = buffer.tobytes(); time.sleep(0.01)
    def get_frame(self): return self.current_frame

def notify(data):
    msg = json.dumps(data)
    for q in sse_clients: q.put(msg)

def init_all_engines():
    global cameras; video_base = r"C:\Users\bplas\Desktop\video"
    engine1 = CameraEngine(1, "Ana Koridor", os.path.join(video_base, "192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"))
    engine2 = PedestrianEngine(2, "Güvensiz Bölge", os.path.join(video_base, "192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"))
    engine3 = SpeedEngine(3, "Hız Koridoru", os.path.join(video_base, "192.168.12.5_ch50_20260422112304_20260422113058_hız.avi"))
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
    threading.Thread(target=init_all_engines, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
