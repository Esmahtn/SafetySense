import cv2
import numpy as np
from ultralytics import YOLO
import time

# User's new ROI
ROI_POLYGON = np.array([(381, 34), (298, 148), (213, 289), (563, 283), (403, 35)], dtype=np.int32)
VIDEO_PATH = "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"

def test_new_roi():
    model = YOLO("yolo11n.pt")
    cap = cv2.VideoCapture(VIDEO_PATH)
    cap.set(cv2.CAP_PROP_POS_MSEC, 170 * 1000) 
    
    prev_positions = {}
    start_points = {}
    violators = set()
    track_age = {}
    
    # Video Kayıt (Tüm oturum)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_vid_name = f"tum_kayit_ters_yon_{timestamp}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_vid_name, fourcc, fps, (w, h))
    
    print(f"SİSTEM BAŞLADI: Tüm oturum '{out_vid_name}' dosyasına kaydediliyor...")
    
    cv2.namedWindow("Ters Yon Test - Kayit Ediliyor")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # Scale ROI
        scale_x = w / 800
        scale_y = h / 450
        scaled_roi = np.array([(int(x * scale_x), int(y * scale_y)) for x, y in ROI_POLYGON], dtype=np.int32)
        
        display_frame = frame.copy()
        cv2.polylines(display_frame, [scaled_roi], True, (255, 255, 0), 2)
        
        results = model.track(frame, persist=True, classes=[2, 3, 5, 7], imgsz=640, tracker="botsort_custom.yaml", verbose=False)
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            
            for box, id in zip(boxes, ids):
                cx, cy = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
                
                if cv2.pointPolygonTest(scaled_roi, (cx, cy), False) < 0:
                    continue
                
                track_age[id] = track_age.get(id, 0) + 1
                if id not in prev_positions:
                    prev_positions[id] = cy
                    start_points[id] = (cx, cy)
                    continue
                
                dy = cy - prev_positions[id]
                total_dy = cy - start_points[id][1]
                total_dx = abs(cx - start_points[id][0])
                
                if dy > 2:
                    start_points[id] = (cx, cy)
                
                is_upward = total_dy < -40
                is_vertical_dominant = abs(total_dy) > (total_dx * 1.2)
                
                if is_upward and is_vertical_dominant and track_age[id] >= 10:
                    violators.add(id)
                
                prev_positions[id] = cy
                
                # Visuals
                color = (0, 0, 255) if id in violators else (0, 255, 0)
                label = "!!! TERS YON IHLAL !!!" if id in violators else f"ID:{id}"
                cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), color, 4)
                cv2.putText(display_frame, label, (box[0], box[1]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

        # Videoya çizimli frame'i yaz
        writer.write(display_frame)

        cv2.imshow("Ters Yon Test - Kayit Ediliyor", cv2.resize(display_frame, (1024, 576)))
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"Kayıt bitti: {out_vid_name}")

if __name__ == "__main__":
    test_new_roi()
