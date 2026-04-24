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

app = Flask(__name__)
CORS(app)

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ihlal_kayitlari")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")
if not os.path.exists(VIOLATIONS_DIR):
    os.makedirs(VIOLATIONS_DIR)

# SQLite Setup
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

# SSE (Server-Sent Events) Clients Queue List
sse_clients = []

cameras = {}

class CameraEngine:
    def __init__(self, cam_id, name, source):
        self.cam_id = cam_id
        self.name = name
        self.source = source
        self.model = YOLO("yolo11n.pt")
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 170 * 1000)
        self.current_frame = None
        
        # Tarayıcılar için H264 (avc1) deneyelim
        self.fourcc = cv2.VideoWriter_fourcc(*'avc1')
        
        # Kamera FPS değerini al, okuyamazsa varsayılan 25 kabul et
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not self.fps or self.fps < 10:
            self.fps = 25.0
            
        self.frame_buffer = deque(maxlen=int(self.fps * 4)) # Geriye dönük 4 saniyelik tampon
        self.recording_frames_left = 0
        self.current_writer = None
        
        self.violation_count = 0
        self.alert_timer = 0
        self.violators = set()           # Kalıcı ihlalci araç ID seti
        self.prev_positions = {}         # Her araç için önceki cy
        self.start_points = {}           # İhlal analizi başlangıç noktası (sıfırlanabilir)
        self.entry_cy = {}               # Araç ilk görüldüğündeki cy (üstten mi alttan mı girdi?)
        self.violation_scores = {}       # Yukarı hareket birikimi
        self.vehicle_logged = set()      # DB'ye zaten yazılanlar, bir daha yazılmaz
        self.track_age = {}              # Kaç frame'dir görülüyor (gürültü filtresi)
        self.downward_streak = {}        # Arka arkaya kaç frame aşağı gitti
        self.pos_history = {}            # Son N frame'deki cy değerleri (durağanlık tespiti)
        self.post_reset_grace = {}       # Reset sonrası koruma (yanlış top-gate geçişini engeller)
        self.violation_cooldown = 0
        self.last_alert_time = 0         # Spam/ID drop koruması (30sn)

    def log_violation(self, vehicle_id, frame, box=None):
        # Spam Önleme
        current_time = time.time()
        is_spam = (current_time - self.last_alert_time) < 30
        
        timestamp = datetime.now().strftime("%H%M%S_%f")
        rand_suffix = random.randint(1000, 9999)
        img_name = f"cam{self.cam_id}_ID{vehicle_id}_{timestamp}_{rand_suffix}.jpg"
        vid_name = f"cam{self.cam_id}_ID{vehicle_id}_{timestamp}_{rand_suffix}.mp4"
        
        # Screenshot Kaydet
        img_path = os.path.join(VIOLATIONS_DIR, img_name)
        cv2.imwrite(img_path, frame)
        
        # CROP (Yakınlaştırma): Tam olarak ihlal yapan araca odaklan
        crop_name = f"crop_{img_name}"
        crop_path = os.path.join(VIOLATIONS_DIR, crop_name)
        if box is not None:
            try:
                y1, y2 = max(0, int(box[1]-80)), min(frame.shape[0], int(box[3]+80))
                x1, x2 = max(0, int(box[0]-80)), min(frame.shape[1], int(box[2]+80))
                crop_img = frame[y1:y2, x1:x2]
                cv2.imwrite(crop_path, crop_img)
            except: cv2.imwrite(crop_path, frame)
        else:
            cv2.imwrite(crop_path, frame)
        
        # Video Kaydı: Bağımsız writer kullan
        vid_path = os.path.join(VIOLATIONS_DIR, vid_name)
        h, w = 450, 800
        # FFmpeg ile avc1 deniyoruz
        writer = cv2.VideoWriter(vid_path, cv2.CAP_FFMPEG, self.fourcc, self.fps, (w, h))
        
        if not writer.isOpened():
            # Eğer avc1 başarısız olursa mp4v'ye düş
            fourcc_alt = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(vid_path, cv2.CAP_FFMPEG, fourcc_alt, self.fps, (w, h))
            
        if writer.isOpened():
            # Tampondaki kareleri bu writer'a dök
            for buf_frame in self.frame_buffer:
                # Boyutları eşitle
                resized_frame = cv2.resize(buf_frame, (w, h))
                writer.write(resized_frame)
            # Aktif yazıcılar listesine ekle
            if not hasattr(self, 'active_writers'): self.active_writers = []
            self.active_writers.append({'writer': writer, 'frames_left': int(self.fps * 5)})
        
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        violation_type = "Ters Yön İhlali"
        
        # SQLite'a Kaydet
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO violations (vehicle_id, cam_name, type, timestamp, image_path, video_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (int(vehicle_id), self.name, violation_type, timestamp_str, img_name, vid_name))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()

        # SSE İstemcilerine Canlı Bildirim Gönder ve Mail At
        event_data = {
            "id": int(vehicle_id), 
            "db_id": last_id,
            "cam_name": self.name, 
            "type": violation_type, 
            "time": timestamp_str, 
            "img": img_name,
            "crop": crop_name,
            "video": vid_name
        }
        
        if not is_spam:
            if hasattr(self, 'on_violation') and self.on_violation:
                self.on_violation(event_data)
            self.last_alert_time = current_time

        self.violation_count += 1
        self.alert_timer = 35

    def process(self):
        frame_counter = 0
        results = None
        
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success: break

            h, w, _ = frame.shape
            line_y     = int(h * 0.72)  # Sarı çizgi — ana tespit bölgesi
            top_line_y = int(h * 0.40)  # Cyan çizgi — tünel girişi

            # ── YOL KORİDORU ──
            corridor_x_min = int(w * 0.12)   
            corridor_x_max = int(w * 0.88)   

            frame_counter += 1
            if frame_counter % 2 == 0:
                # Fabrika: motosiklet yok (class 3 kaldırıldı), yalnızca araç/kamtör/otöbüs
                results = self.model.track(frame, persist=True, classes=[2, 5, 7], verbose=False, imgsz=640, conf=0.20)

            if results and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                confs = results[0].boxes.conf.cpu().numpy()

                for box, id, conf in zip(boxes, ids, confs):
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    bbox_w = box[2] - box[0]
                    bbox_h = box[3] - box[1]
                    bbox_area = bbox_w * bbox_h

                    # ── FİLTRE 0: X-eksen koridor filtresi ──
                    if cx < corridor_x_min or cx > corridor_x_max:
                        continue

                    # ── FİLTRE 1: Güven eşiği ──
                    if cy >= top_line_y and conf < 0.55:
                        continue

                    # ── FİLTRE 2: Minimum boyut ──
                    min_area = 2500 if cy < top_line_y else 7000
                    if bbox_area < min_area:
                        continue

                    # ── FİLTRE 3: Aspect ratio (0.45 – 4.0) ──
                    aspect = bbox_w / (bbox_h + 1e-5)
                    if aspect < 0.45 or aspect > 4.0:
                        continue

                    # ── TRACK AGE: İlk 4 frame'de analiz yapma ──
                    self.track_age[id] = self.track_age.get(id, 0) + 1
                    if self.track_age[id] < 4:
                        self.prev_positions[id] = cy
                        continue

                    # ── DURAĞANLIK TESPİTİ: Yeşil çizgi üstündeki sabit nesneler araç değil ──
                    if id not in self.pos_history:
                        self.pos_history[id] = deque(maxlen=20)
                    self.pos_history[id].append(cy)

                    if cy < top_line_y and len(self.pos_history[id]) >= 15:
                        pos_range = max(self.pos_history[id]) - min(self.pos_history[id])
                        if pos_range < 10:  # 20 frame içinde 10px'den az hareket → sabit nesne
                            # Gri kutu ile göster ama takip etme
                            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (120, 120, 120), 1)
                            cv2.putText(frame, f"STATIC", (box[0], box[1]-8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1)
                            self.prev_positions[id] = cy
                            continue

                    # İlk kayda alındığında başlangıç noktasını sakla
                    if id not in self.start_points:
                        self.start_points[id] = (cx, cy)
                        self.violation_scores[id] = 0
                        self.downward_streak[id] = 0

                    if id in self.prev_positions:
                        dy = cy - self.prev_positions[id]

                        start_x, start_y = self.start_points[id]
                        total_dx = abs(cx - start_x)
                        total_dy = cy - start_y   # pozitif = aşağı, negatif = yukarı

                        # ── YÖN TAKİBİ ──
                        # Sadece belirgin yukarı hareket (dy < -2) streak'i sıfırlar.
                        # Hafif sağ-sol kayma (dy in [-2, 1]) streak'i BOZMAZ.
                        if dy > 1:
                            self.downward_streak[id] = self.downward_streak.get(id, 0) + 1
                        elif dy < -2:
                            self.downward_streak[id] = 0
                        # dy in [-2, 1] → nötr, streak değişmez

                        # Grace sayacını her frame azalt
                        if self.post_reset_grace.get(id, 0) > 0:
                            self.post_reset_grace[id] -= 1

                        # 5+ frame kararlı aşağı → sıfırla + 12 frame koruma başlat
                        if self.downward_streak.get(id, 0) >= 5:
                            self.violation_scores[id] = 0
                            self.start_points[id] = (cx, cy)
                            start_x, start_y = cx, cy
                            total_dx = 0
                            total_dy = 0
                            self.post_reset_grace[id] = 12  # Reset sonrası 12 frame dokunulmazlık

                        prev_cy = self.prev_positions[id]

                        # ── AŞAĞI KORUMA ──
                        # downward_streak >= 3  → son 3 frame aşağı gitti
                        # total_dy >= 0         → start noktasından beri net aşağı
                        # post_reset_grace > 0  → reset sonrası salınım koruması
                        grace = self.post_reset_grace.get(id, 0)
                        if self.downward_streak.get(id, 0) >= 3 or total_dy >= 0 or grace > 0:
                            self.prev_positions[id] = cy
                            is_bad = id in self.violators
                            color = (0, 0, 255) if is_bad else (0, 200, 0)
                            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 12 if is_bad else 2)
                            cv2.putText(frame, f"ID:{id} ({conf:.2f})", (box[0], box[1]-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                            continue

                        # ── KURAL 1: Top Gate geçişi — anında ihlal ──
                        # Sadece net yukarı hareket varsa (dy < 0) ve çizgi geçildiyse
                        if prev_cy >= top_line_y and cy < top_line_y:
                            dy = cy - prev_cy
                            age = self.track_age.get(id, 0)
                            ratio_ok = (total_dx == 0) or (abs(total_dy) > total_dx * 0.45)
                            # dy < -1: Net yukarı hareket şartı eklendi (yanlış tetiklemeyi önlemek için)
                            if ratio_ok and age >= 8 and dy < -1 and id not in self.vehicle_logged:
                                self.vehicle_logged.add(id)
                                self.violators.add(id)
                                self.log_violation(id, frame, box)
                                self.violation_cooldown = int(self.fps * 10)

                        # ── KURAL 2: Kavşak koridoru (sarı–yeşil arası) ──
                        elif top_line_y <= cy < line_y and dy < -1:
                            self.violation_scores[id] += abs(dy)
                            if (self.violation_scores[id] > 35
                                    and total_dy <= -40
                                    and (total_dx == 0 or abs(total_dy) > total_dx * 0.85)):
                                if id not in self.vehicle_logged:
                                    self.vehicle_logged.add(id)
                                    self.violators.add(id)
                                    self.log_violation(id, frame)
                                    self.violation_cooldown = int(self.fps * 10)

                        # ── KURAL 3: Darboğaz (yeşil çizgi üstü) — sabit nesneler için yaş filtresi ──
                        elif cy < top_line_y and dy < -1:
                            age = self.track_age.get(id, 0)
                            # Yeşil çizgi üstündeki nesneler için en az 20 frame takip şart
                            # (statik raflar/konteynerler erken ID alır ama yaş 20'yi geçemez)
                            if age >= 20:
                                self.violation_scores[id] += abs(dy)
                                if (self.violation_scores[id] > 10
                                        and total_dy <= -12
                                        and (total_dx == 0 or abs(total_dy) > total_dx * 0.35)):
                                    if id not in self.vehicle_logged:
                                        self.vehicle_logged.add(id)
                                        self.violators.add(id)
                                        self.log_violation(id, frame, box)
                                        self.violation_cooldown = int(self.fps * 10)

                    self.prev_positions[id] = cy

                    # Çizim
                    is_bad = id in self.violators
                    color  = (0, 0, 255) if is_bad else (0, 255, 0)
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 12 if is_bad else 2)
                    cv2.putText(frame, f"ID:{id} ({conf:.2f})", (box[0], box[1]-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            if self.violation_cooldown > 0:
                self.violation_cooldown -= 1

            # Koridor dikey sınırlarını çiz
            cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 255), 2)
            cv2.putText(frame, "DETECTION ZONE", (10, line_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.line(frame, (0, top_line_y), (w, top_line_y), (0, 255, 0), 2)
            cv2.putText(frame, "TOP GATE", (10, top_line_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Koridor X sınırlarını çiz (sol/sağ dışlanan bölgeler)
            cv2.line(frame, (corridor_x_min, 0), (corridor_x_min, h), (100, 100, 255), 1)
            cv2.line(frame, (corridor_x_max, 0), (corridor_x_max, h), (100, 100, 255), 1)
            if self.alert_timer > 0:
                cv2.rectangle(frame, (0,0), (w,h), (0,0,255), 15)
                self.alert_timer -= 1

            preview = cv2.resize(frame, (800, 450))
            self.frame_buffer.append(preview) # Geçmiş için tampona kaydet
            
            _, buffer = cv2.imencode('.jpg', preview)
            self.current_frame = buffer.tobytes()
            
            # Eğer kayıt devam ediyorsa güncel kareyi de yaz
            # Aktif video kayıtlarını güncelle
            if hasattr(self, 'active_writers'):
                for rec in self.active_writers[:]:
                    rec['writer'].write(preview)
                    rec['frames_left'] -= 1
                    if rec['frames_left'] <= 0:
                        rec['writer'].release()
                        self.active_writers.remove(rec)

            # cv2.imshow("Viraj Korumali Analiz", preview)
            # if cv2.waitKey(1) & 0xFF == ord('q'): break

        self.cap.release()
        if self.current_writer is not None:
            self.current_writer.release()
        cv2.destroyAllWindows()
        
    def get_frame(self):
        return self.current_frame

# Başlat
engine = CameraEngine(1, "Ana Koridor", "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi")
cameras[1] = engine

engine2 = PedestrianEngine(2, "Güvensiz Bölge", "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi")
cameras[2] = engine2

def notify_pedestrian(data):
    event_data = {
        "id": data["id"], 
        "cam_name": data["camera_name"], 
        "type": data["type"], 
        "time": data["timestamp"], 
        "img": os.path.basename(data["image_path"]), 
        "video": os.path.basename(data.get("video_path", ""))
    }
    msg = json.dumps(event_data)
    for q in sse_clients:
        q.put(msg)
        
    # Asenkron E-Posta Gönderimi
    threading.Thread(
        target=send_violation_email,
        args=(event_data["cam_name"], event_data["type"], event_data["id"], event_data["time"], data["image_path"]),
        daemon=True
    ).start()

engine2.on_violation = notify_pedestrian

def notify_clients(data):
    msg = json.dumps(data)
    for q in sse_clients:
        q.put(msg)
        
    # Asenkron E-Posta Gönderimi
    img_full_path = os.path.join(VIOLATIONS_DIR, data["img"])
    threading.Thread(
        target=send_violation_email,
        args=(data["cam_name"], data["type"], data["id"], data["time"], img_full_path),
        daemon=True
    ).start()

engine.on_violation = notify_clients

@app.route('/screenshots/<path:filename>')
def get_screenshot(filename):
    return send_from_directory(VIOLATIONS_DIR, filename)

@app.route('/videos/<path:filename>')
def get_video(filename):
    return send_from_directory(VIOLATIONS_DIR, filename)

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
            if q in sse_clients:
                sse_clients.remove(q)
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/pedestrian_stream')
def pedestrian_stream():
    def generate():
        while True:
            frame = engine2.get_frame() if 'engine2' in globals() else None
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.03)
            else:
                time.sleep(0.5)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vehicle_stream')
def vehicle_stream():
    def generate():
        while True:
            frame = engine.get_frame() if 'engine' in globals() else None
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.03)
            else:
                time.sleep(0.5)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM violations ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    
    history = []
    for r in rows:
        history.append({
            "id": r['id'], # Veritabanı primary key (silme işlemi için gerekli)
            "vehicle_id": r['vehicle_id'],
            "cam_name": r['cam_name'],
            "type": r['type'],
            "time": r['timestamp'],
            "img": r['image_path'],
            "video": r['video_path']
        })
    
    cursor.execute('SELECT COUNT(*) FROM violations')
    total = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({"total": total, "history": history})

@app.route('/delete_violation/<int:violation_id>', methods=['DELETE'])
def delete_violation(violation_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Dosya yollarını bul
    cursor.execute('SELECT image_path, video_path FROM violations WHERE id = ?', (violation_id,))
    row = cursor.fetchone()
    
    if row:
        img_path, vid_path = row
        # Diskten dosyaları sil
        if img_path and os.path.exists(os.path.join(VIOLATIONS_DIR, os.path.basename(img_path))):
            try: os.remove(os.path.join(VIOLATIONS_DIR, os.path.basename(img_path)))
            except: pass
        if vid_path and os.path.exists(os.path.join(VIOLATIONS_DIR, os.path.basename(vid_path))):
            try: os.remove(os.path.join(VIOLATIONS_DIR, os.path.basename(vid_path)))
            except: pass
            
        # Veritabanından sil
        cursor.execute('DELETE FROM violations WHERE id = ?', (violation_id,))
        conn.commit()
        
    conn.close()
    return jsonify({"success": True})

@app.route('/delete_multiple', methods=['POST'])
def delete_multiple():
    data = request.json
    ids = data.get('ids', [])
    if not ids: return jsonify({"success": False})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for vid_id in ids:
        cursor.execute('SELECT image_path, video_path FROM violations WHERE id = ?', (vid_id,))
        row = cursor.fetchone()
        if row:
            img_path, vid_path = row
            # Dosyaları temizle
            for f in [img_path, vid_path, f"crop_{img_path}"]:
                if f:
                    p = os.path.join(VIOLATIONS_DIR, os.path.basename(f))
                    if os.path.exists(p):
                        try: os.remove(p)
                        except: pass
        cursor.execute('DELETE FROM violations WHERE id = ?', (vid_id,))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True})



if __name__ == "__main__":
    threading.Thread(target=engine.process, daemon=True).start()
    threading.Thread(target=engine2.process, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
