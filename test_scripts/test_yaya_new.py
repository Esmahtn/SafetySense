import cv2
import numpy as np
from ultralytics import YOLO
import time

# Original Pedestrian ROI
ROI_POLYGON = np.array([
    (38, 446), (171, 346), (289, 258), (372, 199), 
    (442, 148), (485, 124), (521, 96), (533, 86), 
    (576, 91), (552, 192), (502, 329), (456, 448)
], dtype=np.int32)

VIDEO_PATH = "video/192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"

def test_yaya():
    model = YOLO("yolo11n.pt")
    cap = cv2.VideoCapture(VIDEO_PATH)
    cap.set(cv2.CAP_PROP_POS_MSEC, 270 * 1000) 
    
    person_in_roi_frames = {}
    logged_ids = set()
    
    # Video Kayıt (Tüm oturum)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_vid_name = f"tum_kayit_yaya_{timestamp}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_vid_name, fourcc, fps, (w, h))
    
    print(f"SİSTEM BAŞLADI: Tüm oturum '{out_vid_name}' dosyasına kaydediliyor...")
    
    cv2.namedWindow("Yaya Gecidi Test - Kayit Ediliyor")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # Scale ROI
        scale_x = w / 800
        scale_y = h / 450
        scaled_roi = np.array([(int(x * scale_x), int(y * scale_y)) for x, y in ROI_POLYGON], dtype=np.int32)
        
        display_frame = frame.copy()
        # Draw ROI
        overlay = display_frame.copy()
        cv2.fillPoly(overlay, [scaled_roi], (0, 255, 255))
        cv2.addWeighted(overlay, 0.2, display_frame, 0.8, 0, display_frame)
        cv2.polylines(display_frame, [scaled_roi], True, (0, 200, 200), 2)
        
        results = model.track(frame, persist=True, classes=[0], conf=0.08, imgsz=320, tracker="botsort_custom.yaml", verbose=False)
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            
            for box, id in zip(boxes, ids):
                cx, cy = int((box[0] + box[2]) / 2), int(box[3])
                
                in_roi = cv2.pointPolygonTest(scaled_roi, (cx, cy), False) >= 0
                
                if in_roi:
                    person_in_roi_frames[id] = person_in_roi_frames.get(id, 0) + 1
                else:
                    person_in_roi_frames[id] = 0
                
                is_violation = person_in_roi_frames.get(id, 0) >= 10
                
                color = (0, 0, 255) if is_violation else (0, 255, 0)
                
                cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), color, 4)
                # ID her zaman görünsün
                cv2.putText(display_frame, f"ID:{id}", (box[0], box[1]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)
                if is_violation:
                    cv2.putText(display_frame, "!!! IHLAL !!!", (box[0], box[3]+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        # Frame numarasını sol üste yaz (ID değişimini takip etmek için)
        frame_no = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        cv2.putText(display_frame, f"Frame:{frame_no}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

        # Videoya çizimli frame'i yaz
        writer.write(display_frame)

        cv2.imshow("Yaya Gecidi Test - Kayit Ediliyor", cv2.resize(display_frame, (1024, 576)))
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"Kayıt bitti: {out_vid_name}")

if __name__ == "__main__":
    test_yaya()
