# vehicle_detection.py
"""
Safe wrapper for vehicle detection. If ultralytics YOLO is available and the model
loads, detect_vehicles(frame) runs inference. Otherwise it returns 0, so the simulation
can continue without a heavy ML dependency.
"""

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except Exception:
    _YOLO_AVAILABLE = False

_model = None
if _YOLO_AVAILABLE:
    try:
        _model = YOLO("yolov8n.pt")  # common small model name (downloads if needed)
    except Exception:
        _model = None
        _YOLO_AVAILABLE = False

def detect_vehicles(frame=None):
    """
    If model is available and frame provided, returns number of vehicle detections.
    Otherwise returns 0.
    """
    if _YOLO_AVAILABLE and _model is not None and frame is not None:
        results = _model(frame)[0]
        # COCO class ids we treat as vehicles: car=2, motorcycle=3, bus=5, truck=7, bicycle=1
        vehicle_ids = {1,2,3,5,7}
        boxes = getattr(results, "boxes", [])
        count = 0
        for b in boxes:
            try:
                cls = int(b.cls)
                if cls in vehicle_ids:
                    count += 1
            except Exception:
                continue
        return count
    return 0
