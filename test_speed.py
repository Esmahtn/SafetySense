import cv2
import time
import os
import sys
from speed_engine import SpeedEngine

def main():
    try:
        video_path = "video/192.168.12.5_ch50_20260422112304_20260422113058_hız.avi"
        
        if not os.path.exists(video_path):
            print(f"HATA: Video dosyası bulunamadı: {video_path}", flush=True)
            return

        print("=== Hız Testi Başlatılıyor (Terminal Modu) ===", flush=True)
        print(f"Video: {video_path}", flush=True)
        
        # Engine'i başlat
        print("Model yükleniyor...", flush=True)
        engine = SpeedEngine(cam_id=3, name="Hiz_Test_Terminal", source=video_path)
        print("Model yüklendi. Video işleniyor...", flush=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("HATA: Video açılamadı.", flush=True)
            return
            
        # Videoyu 2:30'dan (150. saniye) başlat
        cap.set(cv2.CAP_PROP_POS_MSEC, 150 * 1000)
        print("Video 02:30 konumuna sarıldı.", flush=True)

        frame_counter = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Video bitti.", flush=True)
                break
                
            frame_counter += 1
            
            # SpeedEngine'in içindeki mantığı çalıştır (her 2 karede bir)
            if frame_counter % 2 == 0:
                results = engine.model.track(frame, persist=True, classes=[2, 5, 7], verbose=False)
                
                if results and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                    ids = results[0].boxes.id.cpu().numpy().astype(int)
                    
                    for box, id in zip(boxes, ids):
                        cy = int((box[1] + box[3]) / 2)
                        
                        if id not in engine.track_history:
                            from collections import deque
                            engine.track_history[id] = deque(maxlen=20)
                        
                        # Video üzerinden test yaparken gerçek zaman yerine sanal zaman kullanmalıyız
                        # FPS = 25 varsayarsak, her frame 0.04 saniyedir.
                        fps = 25.0 # Videonun gerçek FPS'i
                        virtual_time = frame_counter / fps
                        
                        engine.track_history[id].append((virtual_time, cy))
                        speed = engine.calculate_speed(engine.track_history[id])
                        
                        if speed > 0:
                            print(f"[Frame {frame_counter}] Araç ID: {id} | Anlık Hız: {speed:.2f} km/h", flush=True)
                        
                        # Görselleştirme
                        color = (0, 255, 0) if speed <= 20 else (0, 0, 255)
                        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                        cv2.putText(frame, f"ID:{id} {speed:.1f} km/h", (box[0], box[1]-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.imshow("Hiz Testi", cv2.resize(frame, (800, 450)))
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Kullanıcı tarafından durduruldu.", flush=True)
                break

        cap.release()
        cv2.destroyAllWindows()
        print("Test tamamlandı.", flush=True)
    except Exception as e:
        print(f"BİR HATA OLUŞTU: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
