# 🚦 Smart Traffic Management System

An AI-powered traffic simulation with adaptive signal control, ML traffic prediction, and emergency vehicle preemption — all rendered in a real-time professional dashboard.

---

## Features

| Module | What it does |
|---|---|
| **Adaptive Signal Control** | Adjusts green-light durations dynamically based on live queue lengths and ML predictions |
| **ML Traffic Predictor** | Scikit-learn RandomForest trained online during simulation; predicts density N steps ahead |
| **Emergency Preemption** | Detects approaching emergency vehicles and clears their path within seconds |
| **Multi-vehicle Simulation** | Cars, trucks, buses, and emergency vehicles with realistic lane behaviour |
| **Real-time Dashboard** | KPI cards, live charts, phase timers, and one-click mode controls |

---

## Setup

```bash
# 1. Clone / copy the project
cd SmartTrafficSystem

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the simulation
python -m simulation.main
```

Requires **Python 3.10+** and a display (runs a pygame window).

---

## Controls

| Key / Button | Action |
|---|---|
| `N` | Normal traffic mode |
| `R` | Rush hour (high density) |
| `G` | Night mode (low density) |
| `E` | Spawn emergency vehicle |
| `P` / `Space` | Pause / Resume |
| `ESC` / `Q` | Quit |

All controls are also available as clickable buttons in the dashboard panel.

---

## Project Structure

```
SmartTrafficSystem/
├── simulation/
│   ├── config.py          # All constants and layout parameters
│   ├── vehicle.py         # Vehicle model (types, movement, rendering)
│   ├── traffic_light.py   # Signal controller + adaptive phase logic
│   ├── ml_predictor.py    # RandomForest density predictor
│   ├── intersection.py    # Intersection manager + emergency detection
│   ├── dashboard.py       # Real-time dashboard renderer
│   └── main.py            # Entry point
├── requirements.txt
└── README.md
```

---

## ML Model

The predictor uses a **RandomForestRegressor** (separate models for N-S and E-W axes) trained on a rolling window of simulation history. It starts with synthetic warm-up data and retrains every 60 ticks as live data accumulates. The predicted density is used by the signal controller to bias green-time allocation toward the busier direction.

---

## Emergency Vehicle Flow

1. Vehicle spawns as `type=emergency` (red body, blue/red siren)
2. Intersection controller detects it within **4.5 road-widths** of centre
3. Current green is cut to yellow immediately; all-red follows
4. Emergency vehicle's direction gets a dedicated green for **6 seconds**
5. Normal adaptive cycle resumes automatically

---

## Planned: Live Feed Integration

The `ai/` directory is prepared for YOLOv8-based real vehicle detection from webcam or video files. Once integrated, the ML predictor will consume real density observations instead of simulated ones.
