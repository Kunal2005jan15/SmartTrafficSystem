"""
tests/test_core.py — Core logic tests (no pygame, no display required)
Run: pytest tests/ -v
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_imports():
    from simulation.config import C, FPS, VEHICLE_TYPES, SPAWN_POINTS, CX, CY
    assert FPS == 60
    assert len(SPAWN_POINTS) == 4
    assert "car" in VEHICLE_TYPES
    assert "emergency" in VEHICLE_TYPES
    assert "bg" in C
    assert CX > 0 and CY > 0


def test_config_geometry():
    from simulation.config import CX, CY, ROAD_W, STOP_DIST, SIM_X, SIM_Y
    assert CX < SIM_X
    assert CY < SIM_Y
    assert STOP_DIST > ROAD_W // 2


def test_predictor_warmup():
    from simulation.ml_predictor import MLPredictor
    p = MLPredictor()
    assert len(p.history_ns) > 0
    assert len(p.history_ew) > 0


def test_predictor_record_and_predict():
    from simulation.ml_predictor import MLPredictor
    p = MLPredictor()
    for t in range(20):
        p.record(t, ns_count=5, ew_count=4, ns_queue=2, ew_queue=1)
    pred = p.predict(20)
    assert "predicted_ns" in pred
    assert "predicted_ew" in pred
    assert pred["predicted_ns"] >= 0
    assert pred["predicted_ew"] >= 0


def test_predictor_heuristic_fallback():
    from simulation.ml_predictor import MLPredictor
    p = MLPredictor()
    p.history_ns.clear()
    p.history_ew.clear()
    p.trained = False
    pred = p.predict(0)
    assert pred["predicted_ns"] >= 0


def test_state_machine_cycle():
    from simulation.config import FPS
    green_dur  = 10 * FPS
    yellow_dur = 3  * FPS
    allred_dur = 1  * FPS

    phase, state, timer = 0, "green", 0
    states_seen = set()

    for _ in range(green_dur + yellow_dur + allred_dur + 10):
        timer += 1
        states_seen.add(state)
        if state == "green"   and timer >= green_dur:
            state, timer = "yellow",  0
        elif state == "yellow"  and timer >= yellow_dur:
            state, timer = "all_red", 0
        elif state == "all_red" and timer >= allred_dur:
            phase, state, timer = 1 - phase, "green", 0

    assert "green"   in states_seen
    assert "yellow"  in states_seen
    assert "all_red" in states_seen
    assert phase == 1


def test_emergency_phase_selection():
    def needed_phase(direction):
        return 0 if direction in ("N→S", "S→N") else 1

    assert needed_phase("N→S") == 0
    assert needed_phase("S→N") == 0
    assert needed_phase("E→W") == 1
    assert needed_phase("W→E") == 1


def test_vehicle_distance():
    from simulation.config import CX, CY
    def dist(x, y):
        return math.hypot(x - CX, y - CY)

    assert dist(CX, CY) == 0.0
    assert dist(CX + 100, CY) == 100.0
    assert dist(0, 0) > dist(CX + 5, CY)


def test_adaptive_green_range():
    from simulation.config import MIN_GREEN, MAX_GREEN

    def compute_green(queue, pred):
        demand = queue + pred * 0.4
        ratio  = min(demand / 20.0, 1.0)
        return MIN_GREEN + (MAX_GREEN - MIN_GREEN) * ratio

    g_low  = compute_green(0, 0)
    g_high = compute_green(20, 20)

    assert MIN_GREEN <= g_low  <= MAX_GREEN
    assert MIN_GREEN <= g_high <= MAX_GREEN
    assert g_high > g_low


def test_csv_exists_and_parseable():
    import csv
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "data", "traffic_history.csv")
    assert os.path.exists(csv_path), "data/traffic_history.csv missing"

    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 10
    assert "ns_count" in rows[0]
    assert "ew_count" in rows[0]