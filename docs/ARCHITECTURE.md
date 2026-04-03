# Architecture — Smart Traffic Management System

## System Overview

```
SmartTrafficSystem/
│
├── simulation/          ← Core simulation engine (always active)
│   ├── config.py        ← Single source of truth: all constants
│   ├── vehicle.py       ← Vehicle model: motion, rendering, emergency
│   ├── traffic_light.py ← Signal controller: phases, adaptive timing, preemption
│   ├── ml_predictor.py  ← Online RandomForest density predictor
│   ├── intersection.py  ← Intersection manager: spawning, coordination
│   ├── dashboard.py     ← Real-time pygame dashboard
│   ├── logger.py        ← CSV event + stats logger
│   ├── stats.py         ← In-memory stats collector + exporter
│   └── main.py          ← Entry point
│
├── ai/                  ← Phase 2: live detection (stubs + integration points)
│   ├── vehicle_detection.py   ← YOLOv8 detection + emergency heuristic
│   ├── detect_video.py        ← Video/webcam runner
│   ├── traffic_predictor.py   ← Offline training from CSV
│   └── models/                ← Saved .joblib / .pt model files
│
├── detection/           ← Demo scripts (no camera needed)
│   └── vehicle_detection_demo.py
│
├── data/                ← CSV datasets (sample + generated runs)
├── logs/                ← Per-session event and stats logs
├── scripts/             ← CLI utilities
│   ├── run_headless.py  ← Headless simulation for data collection
│   ├── benchmark.py     ← Adaptive vs fixed timing comparison
│   └── generate_data.py ← Synthetic dataset generator
│
└── tests/               ← pytest test suite
    ├── test_core.py
    └── test_extended.py
```

---

## Data Flow

```
Spawn points (N/S/E/W)
        │
        ▼
  Intersection manager
    ├── detects emergency vehicles (dist < 4.5 × road_width)
    ├── records density counts per axis
    └── feeds MLPredictor.record()
              │
              ▼
        MLPredictor
          ├── builds feature window (120 ticks)
          ├── retrains RandomForest every 60 ticks
          └── returns predicted_ns, predicted_ew
                    │
                    ▼
        IntersectionController
          ├── _compute_adaptive_green(vehicles, ml_pred)
          │     → demand = queue_len + pred × 0.4
          │     → green_s = MIN + (MAX - MIN) × min(demand/20, 1)
          ├── phases: 0=N-S green, 1=E-W green
          ├── states: green → yellow → all_red → green
          └── emergency preemption:
                trigger_emergency() → immediate yellow → all_red → emergency green (6s)
```

---

## ML Model Detail

- **Algorithm**: `sklearn.ensemble.RandomForestRegressor`
- **Two models**: one for N-S density, one for E-W density
- **Feature vector** (12 features):
  - Mean NS/EW count over last 120 ticks
  - Max NS/EW count
  - Std NS/EW count
  - Mean queue lengths NS/EW
  - Time-of-day sin/cos encoding
  - Latest NS/EW count
- **Training cadence**: online, every 60 ticks
- **Warm-up**: synthetic rush-hour data primes the model before tick 1
- **Fallback**: 20-tick rolling average heuristic if sklearn unavailable

---

## Emergency Vehicle Flow

```
Vehicle spawned with is_emergency=True
            │
            ▼
  intersection._check_emergency_vehicles()
    distance < 4.5 × ROAD_W?
            │  yes
            ▼
  controller.trigger_emergency(vehicle_id, direction)
    ├── compute needed_phase (0=N-S, 1=E-W)
    ├── if current phase ≠ needed: → state = YELLOW immediately
    └── set emergency_countdown = 6 × FPS
            │
            ▼
  ALL_RED (1s safety clearance)
            │
            ▼
  GREEN for emergency phase (6s hold)
            │
            ▼
  emergency vehicle passes → controller.clear_emergency()
            │
            ▼
  Normal adaptive cycle resumes
```

---

## Extending to Live Detection (Phase 2)

1. Install detection deps: `pip install -e ".[detection]"`
2. Download YOLOv8: `yolo download model=yolov8n.pt`
3. In `simulation/intersection.py`, replace `_maybe_spawn()` with a call to
   `ai.vehicle_detection.detect_frame(frame)` and map bounding boxes to vehicle positions
4. Wire camera frames from `ai/detect_video.py` into the simulation loop
5. Use `ai/traffic_predictor.py --csv data/run_*.csv` to train a production model
   from accumulated real-world data, then load it in `simulation/ml_predictor.py`
