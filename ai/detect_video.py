# detect_video.py
"""
Detect vehicles in a video file or webcam using Ultralytics YOLO.
Outputs:
 - Annotated video file (if --output provided)
 - Per-frame CSV of counts (--csv)
 - Writes latest_counts.json (optional) for integraton with simulator

Usage:
    python -m ai.detect_video --source path/to/video.mp4 --output out.mp4 --csv counts.csv
    python -m ai.detect_video --source 0 --output out.mp4 --csv counts.csv
"""

import argparse
import time
import csv
import json
import os
from pathlib import Path

try:
    import cv2
except Exception as e:
    raise SystemExit("OpenCV (cv2) is required. Install: pip install opencv-python") from e

YOLO_AVAILABLE = True
try:
    from ultralytics import YOLO
except Exception:
    YOLO_AVAILABLE = False

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="Video file path or camera index (0)")
    p.add_argument("--output", default=None, help="Output annotated video path (mp4)")
    p.add_argument("--csv", dest="csv_out", default=None, help="CSV path to write per-frame counts")
    p.add_argument("--model", default="yolov8n.pt", help="YOLO model name/path")
    p.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    p.add_argument("--nojson", dest="write_json", action="store_false", help="Do not write latest_counts.json")
    return p.parse_args()

def run_detection(source, output=None, csv_out=None, write_json=True, model_name="yolov8n.pt", conf=0.35):
    if not YOLO_AVAILABLE:
        raise RuntimeError("Ultralytics YOLO is not installed. Install: pip install ultralytics")

    model = None
    try:
        model = YOLO(model_name)
    except Exception as e:
        raise RuntimeError(f"Failed loading YOLO model '{model_name}': {e}")

    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else str(source))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

    out_writer = None
    if output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_writer = cv2.VideoWriter(output, fourcc, fps, (width, height))

    csv_file = None
    csv_writer = None
    if csv_out:
        csv_file = open(csv_out, "w", newline="")
        csv_writer = csv.writer(csv_file)
        header = ["frame", "timestamp", "total", "car", "motorcycle", "bus", "truck", "bicycle"]
        csv_writer.writerow(header)

    frame_idx = 0
    latest_counts = {}

    print("Starting detection. Press Ctrl+C to stop. (Press 'q' in the window to stop early.)")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            t0 = time.time()
            results = model(frame, imgsz=640, conf=conf, verbose=False)[0]

            counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "bicycle": 0}
            total = 0

            boxes = getattr(results, "boxes", [])
            for b in boxes:
                try:
                    cls = int(b.cls)
                except Exception:
                    try:
                        cls = int(b.cls.item())
                    except Exception:
                        continue
                if cls == 2:
                    counts["car"] += 1; total += 1
                elif cls == 3:
                    counts["motorcycle"] += 1; total += 1
                elif cls == 5:
                    counts["bus"] += 1; total += 1
                elif cls == 7:
                    counts["truck"] += 1; total += 1
                elif cls == 1:
                    counts["bicycle"] += 1; total += 1

            annotated = frame.copy()
            for box in boxes:
                try:
                    xyxy = None
                    if hasattr(box, "xyxy"):
                        xy = box.xyxy
                        if hasattr(xy, "cpu"):
                            xy = xy.cpu().numpy()
                        xyxy = xy[0]
                    if xyxy is None:
                        continue
                    x1, y1, x2, y2 = map(int, xyxy)
                    label = f"{int(box.cls)}:{float(getattr(box, 'conf', 0.0)):.2f}"
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated, label, (x1, max(10, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                except Exception:
                    continue

            overlay_text = f"Total: {total}  car:{counts['car']} bus:{counts['bus']} truck:{counts['truck']} moto:{counts['motorcycle']}"
            cv2.putText(annotated, overlay_text, (10, height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2)

            if out_writer:
                out_writer.write(annotated)

            ts = time.time()
            if csv_writer:
                csv_writer.writerow([frame_idx, ts, total, counts["car"], counts["motorcycle"], counts["bus"], counts["truck"], counts["bicycle"]])
                csv_file.flush()

            if write_json:
                latest_counts = {"frame": frame_idx, "timestamp": ts, "total": total, **counts}
                try:
                    with open("latest_counts.json", "w") as jf:
                        json.dump(latest_counts, jf)
                except Exception:
                    pass

            frame_idx += 1

            cv2.imshow("Detection", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cap.release()
        if out_writer:
            out_writer.release()
        if csv_file:
            csv_file.close()
        cv2.destroyAllWindows()
        print("Finished. Last counts:", latest_counts)

if __name__ == "__main__":
    args = parse_args()
    run_detection(args.source, output=args.output, csv_out=args.csv_out, write_json=args.write_json, model_name=args.model, conf=args.conf)
