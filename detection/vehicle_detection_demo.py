# detection/vehicle_detection_demo.py
import cv2
import json
import os
from ultralytics import YOLO
from collections import Counter


def run_detection(video_name="traffic.mp4"):
    """
    Run vehicle detection on a recorded video.
    Looks for video inside detection/videos/ folder.
    """

    video_path = os.path.join(os.path.dirname(__file__), "videos", video_name)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Load YOLOv8 nano (lightweight and fast)
    model = YOLO("yolov8n.pt")

    # Map COCO class IDs to vehicle names
    vehicle_classes = {2: "car", 3: "motorbike", 5: "bus", 7: "truck"}

    # Process video frame by frame
    for result in model.track(source=video_path, show=True, stream=True, classes=list(vehicle_classes.keys())):
        counts = Counter()

        # Count vehicles in current frame
        for box in result.boxes:
            cls = int(box.cls[0])
            if cls in vehicle_classes:
                counts[vehicle_classes[cls]] += 1

        # Save counts into JSON file
        data = {
            "cars": counts["car"],
            "motorbikes": counts["motorbike"],
            "buses": counts["bus"],
            "trucks": counts["truck"],
            "total": sum(counts.values())
        }

        with open("latest_counts.json", "w") as jf:
            json.dump(data, jf, indent=2)

        print("Vehicle counts:", data)


if __name__ == "__main__":
    run_detection("traffic.mp4")   # default video in detection/videos/
