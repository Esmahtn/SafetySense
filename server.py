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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

# Load users from persistent JSON if available, otherwise use defaults
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        USERS = json.load(f)
else:
    USERS = {
        "admin": {"password": "admin", "role": "admin"},
        "user": {"password": "user", "role": "user"}
    }
    # Ensure the default file exists for future persistence
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(USERS, f, indent=4, ensure_ascii=False)

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

def save_users():
    """Persist the USERS dict to the JSON file."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(USERS, f, indent=4, ensure_ascii=False)

@app.route('/admin/create_user', methods=['POST'])
@admin_required
def admin_create_user():
    """Create a new user (admin or regular) via admin API."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({"status": "error", "message": "username and password required"}), 400
    if role not in ('admin', 'user'):
        return jsonify({"status": "error", "message": "Invalid role"}), 400
    if username in USERS:
        return jsonify({"status": "error", "message": "User already exists"}), 400
    USERS[username] = {"password": password, "role": role}
    save_users()
    return jsonify({"status": "success", "user": username, "role": role})

@app.route('/admin/set_role', methods=['POST'])
@admin_required
def admin_set_role():
    """Change role of an existing user (admin or user)."""
    data = request.json
    username = data.get('username')
    role = data.get('role')
    if username not in USERS:
        return jsonify({"status": "error", "message": "User not found"}), 404
    if role not in ('admin', 'user'):
        return jsonify({"status": "error", "message": "Invalid role"}), 400
    USERS[username]['role'] = role
    save_users()
    return jsonify({"status": "success", "user": username, "role": role})

@app.route('/api/auth/status')
def auth_status():
    if 'user' in session:
        return jsonify({"logged_in": True, "role": session.get('role'), "user": session.get('user')})
    return jsonify({"logged_in": False})

# New endpoint to list users for admin UI
@app.route('/admin/list_users')
@admin_required
def admin_list_users():
    return jsonify(USERS)

# Admin UI page for managing users
@app.route('/admin/users')
@admin_required
def admin_users_page():
    return """
    <!doctype html>
    <html lang='tr'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Admin Kullanıcı Yönetimi</title>
        <style>
            body { background:#020203; color:#fff; font-family:Arial,Helvetica,sans-serif; padding:20px; }
            input, select { padding:8px; margin:4px; border-radius:4px; border:none; }
            button { padding:8px 12px; margin:4px; border:none; border-radius:4px; background:#c00; color:#fff; cursor:pointer; }
            table { width:100%; border-collapse:collapse; margin-top:20px; }
            th, td { padding:8px; border:1px solid #444; text-align:left; }
        </style>
    </head>
    <body>
    <a href="/settings" class="glass px-6 py-4 rounded-3xl flex items-center gap-2 border-white/5 hover:border-blue-600/50 hover:bg-blue-600/10 transition-all font-black text-xs uppercase tracking-widest text-blue-500"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 24 24" class="stroke-current"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09A1.65 1.65 0 0 0 12 5.6V5a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V12a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>Ayarlara Dön</a>
        <h2>Yeni Kullanıcı Oluştur</h2>
        <form id='createForm'>
            <input type='text' id='username' placeholder='Kullanıcı Adı' required />
            <input type='password' id='password' placeholder='Şifre' required />
            <select id='role'>
                <option value='user'>Kullanıcı</option>
                <option value='admin'>Admin</option>
            </select>
            <button type='submit'>Oluştur</button>
        </form>
        <h2>Kullanıcılar</h2>
        <table id='usersTable'>
            <thead><tr><th>Kullanıcı</th><th>Rol</th><th>İşlem</th></tr></thead>
            <tbody></tbody>
        </table>
        <script>
            const API = 'http://localhost:5000';
            async function loadUsers(){
                const res = await fetch(`${API}/admin/list_users`, {credentials:'include'});
                const data = await res.json();
                const tbody = document.querySelector('#usersTable tbody');
                tbody.innerHTML='';
                for(const [user,info] of Object.entries(data)){
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${user}</td><td>${info.role}</td><td><select class='roleSelect' data-user='${user}'>
                        <option value='user' ${info.role==='user'?'selected':''}>Kullanıcı</option>
                        <option value='admin' ${info.role==='admin'?'selected':''}>Admin</option>
                    </select></td>`;
                    tbody.appendChild(tr);
                }
                document.querySelectorAll('.roleSelect').forEach(sel=>{
                    sel.addEventListener('change', async e=>{
                        const username = e.target.dataset.user;
                        const role = e.target.value;
                        await fetch(`${API}/admin/set_role`, {
                            method:'POST',
                            headers:{'Content-Type':'application/json'},
                            credentials:'include',
                            body:JSON.stringify({username,role})
                        });
                        loadUsers();
                    });
                });
            }
            document.getElementById('createForm').addEventListener('submit', async e=>{
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const role = document.getElementById('role').value;
                await fetch(`${API}/admin/create_user`, {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    credentials:'include',
                    body:JSON.stringify({username,password,role})
                });
                document.getElementById('createForm').reset();
                loadUsers();
            });
            loadUsers();
        </script>
    </body>
    </html>
    """


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
EMAIL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_config.json")

DEFAULT_EMAIL_CONFIG = {
    "enabled": False,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "",
    "sender_password": "",
    "recipient_email": ""
}

def load_email_config():
    if os.path.exists(EMAIL_CONFIG_PATH):
        with open(EMAIL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_EMAIL_CONFIG.copy()

def save_email_config(cfg):
    with open(EMAIL_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def send_violation_email(violation_data):
    """Send an email notification for a new violation (runs in background thread)."""
    try:
        cfg = load_email_config()
        if not cfg.get("enabled"):
            return
        if not cfg.get("sender_email") or not cfg.get("recipient_email"):
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[SafetySense] Yeni İhlal: {violation_data.get('type', '')}"
        msg["From"] = cfg["sender_email"]
        msg["To"] = cfg["recipient_email"]

        body = f"""
        <html><body style='font-family:Arial,sans-serif;background:#111;color:#eee;padding:20px;'>
          <h2 style='color:#e53e3e;'>🚨 Yeni Güvenlik İhlali Tespit Edildi</h2>
          <table style='border-collapse:collapse;width:100%;'>
            <tr><td style='padding:8px;color:#aaa;'>İhlal Türü</td><td style='padding:8px;color:#fff;font-weight:bold;'>{violation_data.get('type','')}</td></tr>
            <tr><td style='padding:8px;color:#aaa;'>Kamera</td><td style='padding:8px;'>{violation_data.get('cam_name','')}</td></tr>
            <tr><td style='padding:8px;color:#aaa;'>Zaman</td><td style='padding:8px;'>{violation_data.get('time','')}</td></tr>
            <tr><td style='padding:8px;color:#aaa;'>Kayıt ID</td><td style='padding:8px;'>#{violation_data.get('db_id','')}</td></tr>
          </table>
          <p style='color:#666;margin-top:20px;font-size:12px;'>Bu bildirim SafetySense AI sistemi tarafından otomatik gönderilmiştir.</p>
        </body></html>
        """
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"])) as server:
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
    except Exception as e:
        print(f"[EMAIL] Gönderim hatası: {e}")

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
        
        violation_payload = {"id": int(vehicle_id), "db_id": last_id, "cam_name": self.name, "type": v_type, "time": ts_str, "img": img_name}
        if self.on_violation:
            self.on_violation(violation_payload)
        # Send email notification in background
        threading.Thread(target=send_violation_email, args=(violation_payload,), daemon=True).start()

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

@app.route('/api/email_settings', methods=['GET', 'POST'])
@admin_required
def email_settings():
    if request.method == 'POST':
        data = request.json
        cfg = load_email_config()
        cfg.update({
            "enabled": bool(data.get("enabled", False)),
            "smtp_host": data.get("smtp_host", cfg["smtp_host"]),
            "smtp_port": int(data.get("smtp_port", cfg["smtp_port"])),
            "sender_email": data.get("sender_email", cfg["sender_email"]),
            "sender_password": data.get("sender_password", cfg["sender_password"]),
            "recipient_email": data.get("recipient_email", cfg["recipient_email"])
        })
        save_email_config(cfg)
        return jsonify({"status": "success"})
    cfg = load_email_config()
    # Never expose password to frontend
    safe = {k: v for k, v in cfg.items() if k != "sender_password"}
    safe["has_password"] = bool(cfg.get("sender_password"))
    return jsonify(safe)

@app.route('/api/test_email', methods=['POST'])
@admin_required
def test_email():
    try:
        cfg = load_email_config()
        # Allow overriding password from request for test
        test_password = request.json.get("sender_password") if request.json else None
        if test_password:
            cfg["sender_password"] = test_password
        send_violation_email({
            "type": "Test İhlali",
            "cam_name": "Test Kamera",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "db_id": 0
        })
        return jsonify({"status": "success", "message": "Test e-postası gönderildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/screenshots/<path:filename>')
def get_screenshot(filename): return send_from_directory(VIOLATIONS_DIR, filename)

# ---- Kullanıcı Yönetimi API (React arayüzü için) ----
@app.route('/api/users', methods=['GET'])
@admin_required
def api_list_users():
    """Liste: tüm kullanıcıları döndür (şifre hariç)."""
    result = [
        {"id": uname, "username": uname, "role": info["role"]}
        for uname, info in USERS.items()
    ]
    return jsonify(result)

@app.route('/api/users/<string:username>', methods=['DELETE'])
@admin_required
def api_delete_user(username):
    """Kullanıcı sil."""
    if username not in USERS:
        return jsonify({"status": "error", "message": "Kullanıcı bulunamadı."}), 404
    # Admin kendi hesabını silemesin
    if username == session.get('user'):
        return jsonify({"status": "error", "message": "Kendi hesabınızı silemezsiniz."}), 400
    del USERS[username]
    save_users()
    return jsonify({"status": "success"})

@app.route('/api/users', methods=['POST'])
@admin_required
def api_create_user():
    """Kullanıcı oluştur."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({"status": "error", "message": "Kullanıcı adı ve şifre zorunludur."}), 400
    if role not in ('admin', 'user'):
        return jsonify({"status": "error", "message": "Geçersiz rol."}), 400
    if username in USERS:
        return jsonify({"status": "error", "message": "Bu kullanıcı adı zaten mevcut."}), 400
    USERS[username] = {"password": password, "role": role}
    save_users()
    return jsonify({"status": "success", "username": username, "role": role})

if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
