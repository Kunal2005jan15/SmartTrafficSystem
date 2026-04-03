"""
tests/test_extended.py — Extended tests for logger, stats, intersection, and scripts
Run: python -m pytest tests/ -v  (or: python tests/test_extended.py)
"""

import sys
import os
import math
import csv
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Logger ────────────────────────────────────────────────────────────────────

class TestLogger:
    def test_logger_creates_files(self):
        tmpdir = tempfile.mkdtemp()
        try:
            import simulation.logger as L
            orig_dir = L.LOG_DIR
            L.LOG_DIR = tmpdir

            logger = L.SimLogger(enabled=True)
            logger.event("test_event", tick=1, foo="bar")
            logger.close()

            files = os.listdir(tmpdir)
            assert any("events_" in f for f in files), "events file missing"
            assert any("stats_"  in f for f in files), "stats file missing"

            L.LOG_DIR = orig_dir
        finally:
            shutil.rmtree(tmpdir)

    def test_logger_disabled(self):
        from simulation.logger import SimLogger
        logger = SimLogger(enabled=False)
        logger.event("no_op", tick=0)
        logger.close()   # should not raise


# ── StatsCollector ────────────────────────────────────────────────────────────

class MockIntersection:
    """Minimal mock for stats tests."""
    class MockController:
        phase = 0
        state = "green"
        emergency_active = False
        green_duration   = 1500
        def seconds_remaining(self): return 15.0

    def __init__(self):
        self.controller             = self.MockController()
        self.total_vehicles_passed  = 10
        self.total_vehicles_spawned = 20
        self.emergency_events       = 1
        self.mode                   = "normal"

    def avg_wait(self):         return 4.5
    def current_density(self):  return {"ns": 5, "ew": 4, "total": 9}
    def queue_lengths(self):    return {"ns": 2, "ew": 1}


def test_stats_record_and_export():
    from simulation.stats import StatsCollector
    mock = MockIntersection()
    ml_pred = {"predicted_ns": 5.2, "predicted_ew": 4.1, "confidence": 0.8}

    sc = StatsCollector()
    for t in range(10):
        sc.record(t, mock, ml_pred)

    assert len(sc) == 10

    tmpf = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmpf.close()
    try:
        sc.export_csv(tmpf.name)
        with open(tmpf.name) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 10
        assert "ns_count" in rows[0]
        assert rows[0]["ns_count"] == "5"
    finally:
        os.unlink(tmpf.name)


def test_stats_export_json():
    from simulation.stats import StatsCollector
    mock    = MockIntersection()
    ml_pred = {"predicted_ns": 5.0, "predicted_ew": 4.0, "confidence": 0.7}
    sc      = StatsCollector()
    for t in range(5):
        sc.record(t, mock, ml_pred)

    tmpf = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmpf.close()
    try:
        sc.export_json(tmpf.name)
        with open(tmpf.name) as f:
            data = json.load(f)
        assert "avg_wait_s" in data
        assert data["total_ticks"] == 5
    finally:
        os.unlink(tmpf.name)


def test_stats_summary_empty():
    from simulation.stats import StatsCollector
    sc = StatsCollector()
    sc.summary()   # should not raise on empty data


# ── ML Predictor edge cases ───────────────────────────────────────────────────

def test_predictor_retrain_trigger():
    from simulation.ml_predictor import MLPredictor
    p = MLPredictor()
    p.retrain_every = 5
    for t in range(10):
        p.record(t, ns_count=t % 8, ew_count=(t + 2) % 6, ns_queue=1, ew_queue=0)
    # Should have triggered retrain at t=5
    # Model may or may not be trained (depends on data) but should not crash
    pred = p.predict(10)
    assert isinstance(pred, dict)


def test_predictor_get_history():
    from simulation.ml_predictor import MLPredictor
    p = MLPredictor()
    for t in range(5):
        p.record(t, 3, 4, 1, 0)
    ns_hist = p.get_history_ns()
    ew_hist = p.get_history_ew()
    assert len(ns_hist) > 0
    assert len(ew_hist) > 0


# ── Config completeness ───────────────────────────────────────────────────────

def test_all_color_keys_are_tuples():
    from simulation.config import C
    for key, val in C.items():
        assert isinstance(val, tuple), f"Color {key!r} is not a tuple"
        assert len(val) in (3, 4),    f"Color {key!r} has wrong length"
        for ch in val:
            assert 0 <= ch <= 255,    f"Color {key!r} channel out of range"


def test_vehicle_types_complete():
    from simulation.config import VEHICLE_TYPES
    required_keys = {"w", "h", "speed", "color", "weight"}
    for vtype, cfg in VEHICLE_TYPES.items():
        missing = required_keys - set(cfg.keys())
        assert not missing, f"Vehicle type {vtype!r} missing keys: {missing}"
        assert cfg["speed"] > 0,  f"{vtype} speed must be positive"
        assert cfg["w"] > 0,      f"{vtype} width must be positive"
        assert cfg["h"] > 0,      f"{vtype} height must be positive"


# ── Data generation script ────────────────────────────────────────────────────

def test_generate_data_script():
    from scripts.generate_data import generate
    tmpf = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmpf.close()
    try:
        generate(days=1, out_path=tmpf.name, seed=0, ticks_per_hour=6)
        with open(tmpf.name) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 6 * 24
        assert "ns_count" in rows[0]
        assert "signal_phase" in rows[0]
    finally:
        os.unlink(tmpf.name)


# ── Manual runner ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("logger_creates_files",   TestLogger().test_logger_creates_files),
        ("logger_disabled",        TestLogger().test_logger_disabled),
        ("stats_record_export",    test_stats_record_and_export),
        ("stats_export_json",      test_stats_export_json),
        ("stats_summary_empty",    test_stats_summary_empty),
        ("predictor_retrain",      test_predictor_retrain_trigger),
        ("predictor_get_history",  test_predictor_get_history),
        ("color_keys_valid",       test_all_color_keys_are_tuples),
        ("vehicle_types_complete", test_vehicle_types_complete),
        ("generate_data_script",   test_generate_data_script),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}  →  {e}")

    print(f"\n{passed}/{len(tests)} tests passed.")
