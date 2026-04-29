import cv2
from ultralytics import YOLO
from direction_logic import DirectionTracker
import time

# --- CONFIGURATION ---
MODEL_PATH = "yolo11n.pt" # Or your custom model
SOURCE = 0 # Camera index or video path
LINE = ((100, 300), (500, 300)) # Default horizontal line for detection
TOP_LINE = ((100, 150), (500, 150)) # Secondary line for top region detection


class WrongWayApp:
    def __init__(self):
        print("Loading Model...")
        self.model = YOLO(MODEL_PATH)
        self.tracker = DirectionTracker(LINE, TOP_LINE)
        self.cap = cv2.VideoCapture(SOURCE)
        self.violation_count = 0

    def run(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break

            # Run YOLO Tracking
            # classes=[2, 3, 5, 7] correspond to car, motorcycle, bus, truck in COCO
            results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], tracker="botsort_custom.yaml", verbose=False)

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)

                for box, id in zip(boxes, ids):
                    # Calculate Centroid
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    
                    status = self.tracker.update(id, (cx, cy))

                    # Drawing logic
                    color = (0, 255, 0) # Default Green
                    if status == 'new_violation':
                        self.violation_count += 1
                        print(f"!!! VIOLATION DETECTED: ID {id} !!!")
                        color = (0, 0, 255) # Red for violation
                    elif status == 'already_violator':
                        color = (0, 0, 255) # Keep red for violating vehicles
                    
                    # Draw Bounding Box & ID
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                    cv2.putText(frame, f"ID: {id}", (box[0], box[1] - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw the Gate Line
            cv2.line(frame, LINE[0], LINE[1], (255, 255, 0), 3)
            cv2.putText(frame, "DETECTION GATE", (LINE[0][0], LINE[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Draw the Top Gate Line
            cv2.line(frame, TOP_LINE[0], TOP_LINE[1], (0, 255, 255), 3)
            cv2.putText(frame, "TOP DETECTION GATE", (TOP_LINE[0][0], TOP_LINE[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Dashboard Info
            cv2.putText(frame, f"Violations: {self.violation_count}", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.imshow("Factory Wrong-Way Detection", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = WrongWayApp()
    app.run()
