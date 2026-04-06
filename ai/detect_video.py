"""
ai/detect_video.py  — IMPROVED VERSION
--------------------------------------
Changes over original:
  • Accepts --video flag (recorded file OR webcam index)
  • Saves annotated output video to data/output_<timestamp>.mp4
  • Saves/loads YOLOv8 model weights from models/ folder (persistence)
  • Overlays live vehicle count + signal recommendation on frame
  • Exposes run(video_path) so run.py CLI can call it directly
  • Press Q to quit early
"""

import cv2
import os
import sys
import argparse
from datetime import datetime

# ── Try importing ultralytics (YOLOv8) ──────────────────────────────────────
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics not installed. Falling back to OpenCV background subtraction.")
    print("   Install with: pip install ultralytics")

# ── Constants ────────────────────────────────────────────────────────────────
VEHICLE_CLASSES   = [2, 3, 5, 7]   # COCO: car, motorcycle, bus, truck
MODEL_PATH        = os.path.join(os.path.dirname(__file__), "..", "models", "yolov8n.pt")
OUTPUT_DIR        = os.path.join(os.path.dirname(__file__), "..", "data")
CONFIDENCE        = 0.4


def _get_signal_recommendation(count: int) -> tuple[str, tuple]:
    """Return (label, BGR_colour) based on vehicle count."""
    if count <= 5:
        return "LOW TRAFFIC  — Short green (15s)", (0, 200, 0)
    elif count <= 15:
        return "MED TRAFFIC  — Normal green (30s)", (0, 200, 255)
    else:
        return "HIGH TRAFFIC — Extended green (60s)", (0, 0, 220)


def _detect_yolo(cap, out, model):
    """Main detection loop using YOLOv8."""
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)[0]
        count   = 0

        for box in results.boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            if cls in VEHICLE_CLASSES and conf >= CONFIDENCE:
                count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{results.names[cls]} {conf:.2f}"
                cv2.putText(frame, label, (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Overlay HUD
        sig_text, sig_color = _get_signal_recommendation(count)
        cv2.rectangle(frame, (0, 0), (500, 60), (20, 20, 20), -1)
        cv2.putText(frame, f"Vehicles: {count}", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, sig_text, (10, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, sig_color, 2)

        if out:
            out.write(frame)
        cv2.imshow("SmartTrafficSystem — Vehicle Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n⏹  Detection stopped by user.")
            break


def _detect_background_subtraction(cap, out):
    """Fallback: simple MOG2 background subtraction if YOLO unavailable."""
    fgbg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=50)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        fgmask  = fgbg.apply(frame)
        _, thresh = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        count = 0
        for c in contours:
            if cv2.contourArea(c) > 1500:
                count += 1
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        sig_text, sig_color = _get_signal_recommendation(count)
        cv2.rectangle(frame, (0, 0), (480, 60), (20, 20, 20), -1)
        cv2.putText(frame, f"Vehicles (approx): {count}", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, sig_text, (10, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, sig_color, 2)

        if out:
            out.write(frame)
        cv2.imshow("SmartTrafficSystem — Vehicle Detection (Fallback)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n⏹  Detection stopped by user.")
            break


def run(video_path: str):
    """Entry point called by run.py or directly."""
    # ── Open video ───────────────────────────────────────────────────────────
    source = int(video_path) if video_path.isdigit() else video_path
    cap    = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"❌ Cannot open video source: {video_path}")
        sys.exit(1)

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"✅ Video opened — {width}x{height} @ {fps:.1f}fps")

    # ── Output writer ────────────────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"output_{ts}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    print(f"💾 Saving annotated output → {output_path}")

    # ── Load model ───────────────────────────────────────────────────────────
    if YOLO_AVAILABLE:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print(f"🤖 Loading YOLOv8 model from: {MODEL_PATH}")
        model = YOLO(MODEL_PATH)   # auto-downloads yolov8n.pt on first run
        _detect_yolo(cap, out, model)
    else:
        _detect_background_subtraction(cap, out)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Done. Annotated video saved to: {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartTrafficSystem — Vehicle Detection")
    parser.add_argument(
        "--video", default="0",
        help="Path to video file OR webcam index (default: 0 = webcam)"
    )
    args = parser.parse_args()
    run(args.video)