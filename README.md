# 🚦 SmartTrafficSystem

An AI-powered traffic management system combining **YOLOv8 vehicle detection**, **machine learning traffic prediction**, and an **adaptive signal simulation dashboard**.

---

## ✨ Features

| Module | What it does |
|---|---|
| 🚗 **Vehicle Detection** | Detects & counts vehicles frame-by-frame using YOLOv8 |
| 📈 **Traffic Predictor** | Forecasts traffic volume using RandomForest on historical data |
| 🟢 **Adaptive Signal Control** | Adjusts green/red timing dynamically based on vehicle count |
| 📊 **Simulation Dashboard** | pygame-based real-time visual of intersection state |
| 💾 **Model Persistence** | Trained models saved as `.pkl` — no retraining every run |
| 🎬 **Video Output** | Annotated detection video saved to `data/output_<timestamp>.mp4` |

---

## 📁 Project Structure

```
SmartTrafficSystem/
├── run.py                         ← ROOT CLI (NEW — start here)
├── requirements.txt
├── pytest.ini
│
├── ai/
│   ├── detect_video.py            ← Vehicle detection (IMPROVED)
│   ├── vehicle_detection.py       ← Core detection logic
│   └── traffic_predictor.py       ← ML forecasting (IMPROVED)
│
├── detection/
│   └── vehicle_detection_demo.py  ← Quick demo script
│
├── simulation/
│   ├── main.py                    ← Simulation entry point
│   ├── dashboard.py               ← pygame visualization
│   ├── traffic_light.py           ← Adaptive signal logic
│   ├── vehicle.py                 ← Vehicle model
│   ├── config.py                  ← Settings
│   └── data.json                  ← Sample simulation data
│
├── data/
│   ├── traffic_history.csv        ← Historical dataset
│   └── output_*.mp4               ← Annotated detection outputs (auto-generated)
│
├── models/                        ← Auto-created on first run
│   ├── yolov8n.pt                 ← YOLO weights (auto-downloaded)
│   └── traffic_predictor.pkl      ← Trained predictor (saved after first run)
│
└── tests/
    └── test_smart_traffic.py      ← pytest unit tests (NEW)
```

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/Kunal2005jan15/SmartTrafficSystem.git
cd SmartTrafficSystem
```

### 2. (Recommended) Create a virtual environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `ultralytics` will auto-download `yolov8n.pt` (~6MB) on first detection run. You need an internet connection the first time.

---

## 🚀 How to Run

### Option A — Root CLI (recommended)

```bash
# Vehicle detection on a recorded video
python run.py detect --video data/sample.mp4

# Traffic simulation dashboard
python run.py simulate

# Train/load traffic predictor
python run.py predict

# Full pipeline (predict → detect + simulate in parallel)
python run.py all --video data/sample.mp4
```

### Option B — Run modules directly

```bash
# Detection
cd ai
python detect_video.py --video ../data/sample.mp4

# Simulation
cd simulation
python main.py

# Predictor
cd ai
python traffic_predictor.py
```

---

## 🎥 Recommended Test Video

For the best prototype demo, use **UA-DETRAC** — real overhead CCTV traffic footage:

- Download: https://detrac-db.rit.albany.edu
- Place any `.mp4` file in `data/` folder
- Run: `python run.py detect --video data/your_video.mp4`

**Quick alternative** — download a free traffic video via yt-dlp:
```bash
yt-dlp "https://www.youtube.com/watch?v=wqctLW0Hb_0" -o data/sample.mp4
```
(Search YouTube for "traffic intersection CCTV" for good overhead angle videos)

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest --cov=. tests/

# Run a specific test class
pytest tests/ -v -k "TestSignalRecommendation"
```

Expected output:
```
tests/test_smart_traffic.py::TestSignalRecommendation::test_zero_vehicles_is_low  PASSED
tests/test_smart_traffic.py::TestSignalRecommendation::test_high_traffic ...       PASSED
tests/test_smart_traffic.py::TestTrafficPredictor::test_model_save_load            PASSED
...
```

---

## 🖥️ Demo Presentation Guide

Best way to showcase the prototype:

1. **Open two terminals side by side**
   - Terminal 1: `python run.py detect --video data/sample.mp4`
   - Terminal 2: `python run.py simulate`

2. **What judges/viewers will see:**
   - Detection window: bounding boxes around vehicles + live count + signal recommendation overlay
   - Simulation window: intersection with traffic lights adapting in real time

3. **Record your screen** using OBS Studio (free) for submission videos

4. **Show two scenarios** back to back:
   - Low traffic video → short green time (15s)
   - Dense traffic video → extended green time (60s)

---

## 📊 How Adaptive Signal Timing Works

| Vehicle Count | Signal State | Green Duration |
|---|---|---|
| 0 – 5 | 🟢 Low traffic | 15 seconds |
| 6 – 15 | 🟡 Medium traffic | 30 seconds |
| 16+ | 🔴 High traffic | 60 seconds |

The detector counts vehicles per frame → feeds count to `traffic_light.py` → duration updates dynamically.

---

## 🔧 Configuration

Edit `simulation/config.py` to adjust:
- Intersection size
- Min/max green time
- Vehicle spawn rate (simulation)
- Detection confidence threshold

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `ultralytics` | YOLOv8 vehicle detection |
| `opencv-python` | Video I/O and frame processing |
| `scikit-learn` | RandomForest traffic predictor |
| `pygame` | Simulation dashboard rendering |
| `pandas` / `numpy` | Data handling |
| `pytest` | Unit testing |

---

## 🛣️ Future Improvements

- [ ] Multi-intersection coordination
- [ ] Emergency vehicle priority detection
- [ ] License plate recognition (ANPR)
- [ ] Web dashboard (Flask/FastAPI)
- [ ] Edge deployment (Raspberry Pi / Jetson Nano)
- [ ] Night/rain condition handling

---

## 👤 Author

**Kunal** — [@Kunal2005jan15](https://github.com/Kunal2005jan15)