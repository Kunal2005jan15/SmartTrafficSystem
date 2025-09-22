from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # small pre-trained model

def detect_vehicles(frame):
    results = model(frame)[0]
    vehicle_count = sum([1 for r in results.boxes if int(r.cls) in [2,3,5,7]])  # car, bus, truck
    return vehicle_count
