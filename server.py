import os
os.environ["OPENCV_FFMPEG_THREADS"] = "1"
import cv2
import time
import math
import threading
from threading import Lock
import numpy as np
import random
import sqlite3
import json
import shutil
from datetime import datetime, timedelta
from collections import deque
from queue import Queue
from functools import wraps
from flask import Flask, Response, jsonify, send_from_directory, request, session, redirect, url_for
from flask_cors import CORS
from ultralytics import YOLO
from core.async_camera import SmartCamera
import ai_config

app = Flask(__name__, static_folder='dashboard/dist', static_url_path='/')
app.secret_key = "safetysense_pro_secret_key_123"
CORS(app)

USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "user": {"password": "user", "role": "user"}
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            return "Yetkisiz Erişim - Sadece Admin hesabı buraya girebilir.", 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        if username in USERS and USERS[username]['password'] == password:
            session['user'] = username
            session['role'] = USERS[username]['role']
            return jsonify({"status": "success", "role": session['role']})
        return jsonify({"status": "error", "message": "Geçersiz kullanıcı adı veya şifre"}), 401
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login_page'))

@app.route('/api/auth/status')
def auth_status():
    if 'user' in session:
        return jsonify({"logged_in": True, "role": session.get('role'), "user": session.get('user')})
    return jsonify({"logged_in": False})

@app.route('/')
@login_required
def index(): return send_from_directory(app.static_folder, 'index.html')

@app.route('/settings')
@admin_required
def settings(): return send_from_directory(app.static_folder, 'settings.html')

@app.route('/assets/<path:path>')
def send_assets(path): return send_from_directory(os.path.join(app.static_folder, 'assets'), path)

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
os.makedirs(VIOLATIONS_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime_config.json")

def load_runtime_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cameras": {}}

def save_runtime_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20); cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;"); cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute('CREATE TABLE IF NOT EXISTS violations (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, cam_name TEXT, type TEXT, timestamp DATETIME, image_path TEXT, video_path TEXT)')
    conn.commit(); conn.close()

init_db()
sse_clients, cameras = [], {}
shared_violation_log = {}
shared_violation_lock = Lock()

class HybridEngine:
    def __init__(self, cam_id, name, source, tasks=[]):
        self.cam_id, self.name, self.source = cam_id, name, source
        self.tasks = tasks 
        self.cap = SmartCamera(source, simulate_live=False)
        self.cap.start()
        self.running = True
        
        self.model = YOLO(ai_config.MODEL_NAME)
        self.ref_width, self.ref_height = 800, 450
        self.frame_count = 0
        self.middle_y = None
        
        # Core State
        self.prev_positions = {} 
        self.violation_buffer = {} 
        self.entry_times = {} 
        self.stationary_counters = {}
        self.alarm_ledger = []
        
        self.current_frame = None
        self.on_violation = None

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()
        print(f"Engine durduruldu: {self.name}")

    def update_config(self, cam_data):
        new_source = cam_data.get("source")
        if new_source and new_source != self.source:
            self.source = new_source
            self.cap.release(); self.cap = SmartCamera(new_source, simulate_live=False); self.cap.start()
        self.tasks = cam_data.get("tasks", [])
        self.prev_positions.clear(); self.violation_buffer.clear(); self.entry_times.clear()

    def log_violation(self, vehicle_id, frame, box, v_type):
        now = time.time()
        cx, cy = int((box[0]+box[2])/2), int(box[3])
        
        self.alarm_ledger = [a for a in self.alarm_ledger if (now - a[0]) < 30]
        v_cat = v_type.split('(')[0].strip()
        for ts, ax, ay, atype in self.alarm_ledger:
            if atype.split('(')[0].strip() == v_cat:
                if math.sqrt((cx-ax)**2 + (cy-ay)**2) < 150 and (now - ts) < 15: return

        with shared_violation_lock:
            key = f"{vehicle_id}_{v_cat}"
            if (now - shared_violation_log.get(key, 0)) < 300: return
            shared_violation_log[key] = now

        self.alarm_ledger.append((now, cx, cy, v_type))
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        img_name = f"violation_{datetime.now().strftime('%H%M%S')}_{random.randint(1000,9999)}.jpg"
        img_path = os.path.join(VIOLATIONS_DIR, img_name)
        
        evidence = frame.copy()
        cv2.rectangle(evidence, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 4)
        cv2.rectangle(evidence, (0, 0), (evidence.shape[1], 80), (0, 0, 0), -1)
        cv2.putText(evidence, f"IHLAL: {v_type.upper()}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        cv2.imwrite(img_path, evidence)
        
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute('INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                       (int(vehicle_id), self.name, v_type, ts_str, img_name, ""))
        conn.commit(); last_id = cursor.lastrowid; conn.close()
        
        if self.on_violation:
            self.on_violation({"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": v_type, "time": ts_str, "img": img_name})

    def _compute_perspective_matrix(self, polygon):
        if len(polygon) != 4: return None
        pts = np.array(polygon, dtype="float32")
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        dst = np.array([[0, 0], [4.0, 0], [4.0, ai_config.SPEED_ROI_DISTANCE], [0, ai_config.SPEED_ROI_DISTANCE]], dtype="float32")
        return cv2.getPerspectiveTransform(rect, dst)

    def _calculate_hybrid_distance(self, roi_polygon, p1, p2):
        M = self._compute_perspective_matrix(roi_polygon)
        if M is not None:
            pt1 = np.array([[[p1[0], p1[1]]]], dtype="float32")
            pt2 = np.array([[[p2[0], p2[1]]]], dtype="float32")
            w1 = cv2.perspectiveTransform(pt1, M)[0][0]
            w2 = cv2.perspectiveTransform(pt2, M)[0][0]
            return math.sqrt((w1[0] - w2[0])**2 + (w1[1] - w2[1])**2)
        else:
            pts = np.array(roi_polygon)
            min_y, max_y = np.min(pts[:, 1]), np.max(pts[:, 1])
            roi_px_len = max(1, max_y - min_y)
            px_dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            return (px_dist / roi_px_len) * ai_config.SPEED_ROI_DISTANCE

    def process(self):
        while self.running:
            try:
                if not self.cap.isOpened(): time.sleep(1); continue
                ret, frame = self.cap.read()
                if not ret: time.sleep(0.01); continue
                
                h, w = frame.shape[:2]
                sx, sy = w / self.ref_width, h / self.ref_height
                if self.middle_y is None: self.middle_y = int(h * 0.5)
                
                display_frame = frame.copy()
                self.frame_count += 1
                
                # Her zaman sabit çizgileri ve bölgeleri çiz
                for task in self.tasks:
                    roi = np.array([(int(px*sx), int(py*sy)) for px, py in task['roi']], dtype=np.int32)
                    cv2.polylines(display_frame, [roi], True, (0, 255, 0), 2)
                    if task['type'] == 'wrong_way':
                        cv2.line(display_frame, (0, self.middle_y), (w, self.middle_y), (0, 255, 255), 2)
                
                if self.frame_count % ai_config.FRAME_SKIP_INTERVAL == 0:
                    results = self.model.track(frame, persist=True, classes=[0, 2, 3, 5, 7], imgsz=ai_config.YOLO_IMG_SIZE, conf=ai_config.YOLO_CONF_THRESHOLD, verbose=False)
                    active_ids = []
                    if results and results[0].boxes.id is not None:
                        boxes, ids, clss = results[0].boxes.xyxy.cpu().numpy(), results[0].boxes.id.cpu().numpy().astype(int), results[0].boxes.cls.cpu().numpy().astype(int)
                        active_ids = ids
                        
                        for box, id, cls in zip(boxes, ids, clss):
                            cx, cy = int((box[0]+box[2])/2), int(box[3])
                            
                            # Hareketsiz Nesne Kontrolü
                            is_moving = True
                            if id in self.prev_positions:
                                px, py = self.prev_positions[id]
                                if math.sqrt((cx-px)**2 + (cy-py)**2) < ai_config.STATIONARY_PIXEL_LIMIT:
                                    self.stationary_counters[id] = self.stationary_counters.get(id, 0) + 1
                                else:
                                    self.stationary_counters[id] = 0
                                if self.stationary_counters.get(id, 0) >= ai_config.STATIONARY_FRAME_LIMIT: is_moving = False
                            
                            for idx, task in enumerate(self.tasks):
                                roi = np.array([(int(px*sx), int(py*sy)) for px, py in task['roi']], dtype=np.int32)
                                is_in_roi = cv2.pointPolygonTest(roi, (float(cx), float(cy)), False) >= 0
                                
                                # Histerezis (Karar Birikimi)
                                if id not in self.violation_buffer: self.violation_buffer[id] = {}
                                if idx not in self.violation_buffer[id]: self.violation_buffer[id][idx] = []
                                self.violation_buffer[id][idx].append(is_in_roi)
                                if len(self.violation_buffer[id][idx]) > 8: self.violation_buffer[id][idx].pop(0)
                                roi_confirmed = sum(self.violation_buffer[id][idx]) >= 3
                                
                                if is_in_roi and roi_confirmed and is_moving:
                                    t_type = task['type']
                                    if t_type == "wrong_way":
                                        if id in self.prev_positions:
                                            px, py = self.prev_positions[id]
                                            if py > self.middle_y and cy <= self.middle_y:
                                                self.log_violation(id, frame, box, "Ters Yön")
                                                
                                    elif t_type == "pedestrian" and cls == 0:
                                        self.log_violation(id, frame, box, "Yaya İhlali")
                                        
                                    elif t_type == "speed" and cls in [2,3,5,7]:
                                        if id not in self.entry_times: self.entry_times[id] = {}
                                        if idx not in self.entry_times[id]: self.entry_times[id][idx] = {'time': time.time(), 'pos': (cx, cy)}
                                
                                elif not is_in_roi and id in self.entry_times and idx in self.entry_times[id]:
                                    # Hız Hesaplama (Çıkışta)
                                    entry_info = self.entry_times[id][idx]
                                    duration = time.time() - entry_info['time']
                                    if duration > 0.5:
                                        distance_meters = self._calculate_hybrid_distance(roi, entry_info['pos'], (cx, cy))
                                        speed = (distance_meters / duration) * 3.6 * ai_config.SPEED_CORRECTION_FACTOR
                                        if speed > ai_config.MIN_SPEED_LIMIT:
                                            self.log_violation(id, frame, box, f"Hız İhlali ({int(speed)} km/h)")
                                    del self.entry_times[id][idx]
                                
                                # İhlal veya bölgede olma durumunda kırmızı ile ez
                                if is_in_roi:
                                    cv2.polylines(display_frame, [roi], True, (0, 0, 255), 3)
                                
                            self.prev_positions[id] = (cx, cy)
                            label = f"ID: {id}" + (" (SABIT)" if not is_moving else "")
                            cv2.rectangle(display_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255, 255, 0), 2)
                            cv2.putText(display_frame, label, (int(box[0]), int(box[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                
                preview = cv2.resize(display_frame, (800, 450)); _, buffer = cv2.imencode('.jpg', preview); self.current_frame = buffer.tobytes()
                time.sleep(0.01)
            except Exception as e:
                print(f"Engine Hatası: {e}"); time.sleep(1)

    def get_frame(self): return self.current_frame

def notify(data):
    msg = json.dumps(data)
    for q in sse_clients: q.put(msg)

def main():
    config = load_runtime_config()
    for cam_id_str, cam_data in config.get("cameras", {}).items():
        cam_id = int(cam_id_str)
        engine = HybridEngine(cam_id, cam_data['name'], cam_data['source'], cam_data.get('tasks', []))
        engine.on_violation = notify
        cameras[cam_id] = engine
        threading.Thread(target=engine.process, daemon=True).start()
        time.sleep(1.0) # FFmpeg thread çarpışmasını (Assertion fctx->async_lock) önlemek için gecikme

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        new_config = request.json
        save_runtime_config(new_config)
        
        new_cam_ids = [int(id_str) for id_str in new_config.get("cameras", {}).keys()]
        
        # Mevcut kameraları güncelle veya silinenleri durdur
        current_ids = list(cameras.keys())
        for cid in current_ids:
            if cid not in new_cam_ids:
                cameras[cid].stop()
                del cameras[cid]
            else:
                cid_str = str(cid)
                cameras[cid].update_config(new_config["cameras"][cid_str])
        
        return jsonify({"status": "success"})
    return jsonify(load_runtime_config())

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
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute(f'DELETE FROM violations WHERE id IN ({",".join(["?"]*len(ids))})', ids)
    conn.commit(); conn.close(); return jsonify({"status": "success"})

@app.route('/clear_all_violations', methods=['DELETE'])
def clear_all_violations():
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor(); cursor.execute('DELETE FROM violations'); conn.commit(); conn.close(); return jsonify({"status": "success"})

@app.route('/api/start_camera', methods=['POST'])
def api_start_camera():
    data = request.json
    cam_id_val = data.get('camera_id')
    if cam_id_val is None: return jsonify({"status": "error", "message": "ID missing"}), 400
    
    cid = int(cam_id_val)
    cid_str = str(cam_id_val)
    
    config = load_runtime_config()
    cam_data = config.get("cameras", {}).get(cid_str)
    if not cam_data:
        print(f"[!] Hata: Config'de ID {cid_str} bulunamadı. Mevcutlar: {list(config.get('cameras',{}).keys())}")
        return jsonify({"status": "error", "message": "Config not found"}), 404
    
    if cid not in cameras:
        print(f"[*] Yeni kamera motoru oluşturuluyor: {cam_data['name']} (ID: {cid})")
        engine = HybridEngine(cid, cam_data['name'], cam_data['source'], cam_data.get('tasks', []))
        engine.on_violation = notify
        cameras[cid] = engine
        t = threading.Thread(target=engine.process, daemon=True)
        t.start()
        print(f"[+] Kamera motoru başarıyla başlatıldı ve thread çalışıyor.")
    else:
        print(f"[*] Mevcut kamera motoru güncelleniyor: {cam_data['name']} (ID: {cid})")
        cameras[cid].update_config(cam_data)
        
    return jsonify({"status": "success"})

@app.route('/screenshots/<path:filename>')
def get_screenshot(filename): return send_from_directory(VIOLATIONS_DIR, filename)

if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
