import cv2
import time
import os
import sys
import numpy as np
from collections import deque
from ultralytics import YOLO

class DirectionTester:
    def __init__(self, video_path):
        self.video_path = video_path
        self.model = YOLO("yolo11n.pt")
        self.cap = cv2.VideoCapture(video_path)
        
        # Start at 2:50 as in server.py
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 170 * 1000)
        
        self.prev_positions = {}
        self.start_points = {}
        self.violation_scores = {}
        self.downward_streak = {}
        self.track_age = {}
        self.violators = set()
        self.pos_history = {}
        self.post_reset_grace = {}

    def run(self):
        print(f"=== Ters Yön Debug Testi Başlatılıyor ===")
        print(f"Video: {self.video_path}")
        
        frame_counter = 0
        results = None
        
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success: break

            h, w, _ = frame.shape
            line_y     = int(h * 0.72)
            top_line_y = int(h * 0.40)
            corridor_x_min = int(w * 0.12)
            corridor_x_max = int(w * 0.88)

            frame_counter += 1
            if frame_counter % 2 == 0:
                results = self.model.track(frame, persist=True, classes=[2, 5, 7], verbose=False)

            if results and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                confs = results[0].boxes.conf.cpu().numpy()

                for box, id, conf in zip(boxes, ids, confs):
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    bbox_area = (box[2] - box[0]) * (box[3] - box[1])

                    # Filters
                    if cx < corridor_x_min or cx > corridor_x_max: continue
                    if cy >= top_line_y and conf < 0.55: continue
                    
                    self.track_age[id] = self.track_age.get(id, 0) + 1
                    if self.track_age[id] < 4:
                        self.prev_positions[id] = cy
                        continue

                    if id not in self.start_points:
                        self.start_points[id] = (cx, cy)
                        self.violation_scores[id] = 0
                        self.downward_streak[id] = 0

                    if id in self.prev_positions:
                        dy = cy - self.prev_positions[id]
                        prev_cy = self.prev_positions[id]
                        start_x, start_y = self.start_points[id]
                        total_dx = abs(cx - start_x)
                        total_dy = cy - start_y
                        
                        # Direction Logic
                        if dy > 1:
                            self.downward_streak[id] = self.downward_streak.get(id, 0) + 1
                        elif dy < -2:
                            self.downward_streak[id] = 0
                            
                        if self.downward_streak.get(id, 0) >= 4:
                            self.violation_scores[id] = 0
                            self.start_points[id] = (cx, cy)
                            self.post_reset_grace[id] = 15

                        # Debug Prints
                        score = self.violation_scores.get(id, 0)
                        age = self.track_age.get(id, 0)
                        is_vertical_dominant = (abs(total_dy) > total_dx * 1.5)
                        
                        region = "DIS"
                        if top_line_y <= cy < line_y: region = "KORIDOR"
                        elif cy < top_line_y: region = "UST_BOLGE"
                        
                        if dy != 0:
                            print(f"[F:{frame_counter}] ID:{id} | dy:{dy:3} | Score:{score:4.1f} | Ratio:{is_vertical_dominant} | Age:{age} | Reg:{region}", flush=True)

                        # Rule 1: Top Gate Crossing
                        if prev_cy >= top_line_y and cy < top_line_y:
                            if is_vertical_dominant and age >= 15 and dy < -2:
                                print(f"!!! KURAL 1 TETIKLENDI !!! ID:{id}", flush=True)
                                self.violators.add(id)

                        # Rule 2: Junction Corridor
                        elif top_line_y <= cy < line_y and dy < -1:
                            self.violation_scores[id] += abs(dy)
                            if self.violation_scores[id] > 50 and total_dy <= -60 and is_vertical_dominant and age >= 20:
                                if id not in self.violators:
                                    print(f"!!! KURAL 2 TETIKLENDI !!! ID:{id}", flush=True)
                                    self.violators.add(id)

                        # Rule 3: Bottleneck (Above top line)
                        elif cy < top_line_y and dy < -1:
                            if age >= 25:
                                self.violation_scores[id] += abs(dy)
                                if self.violation_scores[id] > 25 and total_dy <= -30 and is_vertical_dominant:
                                    if id not in self.violators:
                                        print(f"!!! KURAL 3 TETIKLENDI !!! ID:{id}", flush=True)
                                        self.violators.add(id)

                    self.prev_positions[id] = cy
                    
                    # Visualization
                    color = (0, 0, 255) if id in self.violators else (0, 255, 0)
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                    cv2.putText(frame, f"ID:{id} S:{self.violation_scores.get(id,0):.0f}", (box[0], box[1]-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw Lines
            cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 255), 2)
            cv2.line(frame, (0, top_line_y), (w, top_line_y), (0, 255, 0), 2)
            
            cv2.imshow("Ters Yon Debug", cv2.resize(frame, (1280, 720)))
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    video = "video/192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"
    tester = DirectionTester(video)
    tester.run()
