"""
tests/test_smart_traffic.py
---------------------------
Run with:  pytest tests/ -v
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# ── Add project root to path ──────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))
sys.path.insert(0, os.path.join(ROOT, "simulation"))


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Signal recommendation logic (from detect_video)
# ══════════════════════════════════════════════════════════════════════════════

def _get_signal_recommendation(count: int):
    """Duplicated here so tests don't depend on cv2."""
    if count <= 5:
        return "LOW TRAFFIC  — Short green (15s)", (0, 200, 0)
    elif count <= 15:
        return "MED TRAFFIC  — Normal green (30s)", (0, 200, 255)
    else:
        return "HIGH TRAFFIC — Extended green (60s)", (0, 0, 220)


class TestSignalRecommendation:
    def test_zero_vehicles_is_low(self):
        label, _ = _get_signal_recommendation(0)
        assert "LOW" in label

    def test_five_vehicles_is_low(self):
        label, _ = _get_signal_recommendation(5)
        assert "LOW" in label

    def test_six_vehicles_is_medium(self):
        label, _ = _get_signal_recommendation(6)
        assert "MED" in label

    def test_fifteen_vehicles_is_medium(self):
        label, _ = _get_signal_recommendation(15)
        assert "MED" in label

    def test_sixteen_vehicles_is_high(self):
        label, _ = _get_signal_recommendation(16)
        assert "HIGH" in label

    def test_hundred_vehicles_is_high(self):
        label, _ = _get_signal_recommendation(100)
        assert "HIGH" in label

    def test_returns_tuple(self):
        result = _get_signal_recommendation(10)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_color_is_bgr_tuple(self):
        _, color = _get_signal_recommendation(10)
        assert len(color) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Traffic Predictor — preprocessing & training
# ══════════════════════════════════════════════════════════════════════════════

class TestTrafficPredictor:
    @pytest.fixture
    def sample_df(self, tmp_path):
        """Create a tiny CSV for testing."""
        csv_path = tmp_path / "traffic_history.csv"
        df = pd.DataFrame({
            "hour":          [8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                              18, 19, 20, 7,  6,  5,  4,  3,  2,  1],
            "day_of_week":   [1, 1,  2,  2,  3,  3,  4,  4,  5,  5,
                               6,  6,  7,  1,  2,  3,  4,  5,  6,  7],
            "vehicle_count": [50,60,45,40,70,65,55,80,90,100,
                              85,60,30,20,15,10,5, 3, 2, 1],
        })
        df.to_csv(csv_path, index=False)
        return df

    def test_column_detection(self, sample_df):
        target_candidates = [c for c in sample_df.columns
                             if "count" in c.lower()]
        assert len(target_candidates) == 1
        assert target_candidates[0] == "vehicle_count"

    def test_train_produces_predictions(self, sample_df):
        from sklearn.ensemble        import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        X = sample_df[["hour", "day_of_week"]].values
        y = sample_df["vehicle_count"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        assert len(preds) == len(y_test)
        assert all(p >= 0 for p in preds)   # vehicle counts can't be negative

    def test_model_save_load(self, tmp_path, sample_df):
        import pickle
        from sklearn.ensemble import RandomForestRegressor

        X = sample_df[["hour", "day_of_week"]].values
        y = sample_df["vehicle_count"].values

        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(X, y)

        path = tmp_path / "model.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)

        with open(path, "rb") as f:
            loaded = pickle.load(f)

        original_pred = model.predict([[8, 1]])[0]
        loaded_pred   = loaded.predict([[8, 1]])[0]
        assert original_pred == loaded_pred, "Saved/loaded model should give identical predictions"


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Simulation — Traffic Light logic
# ══════════════════════════════════════════════════════════════════════════════

class TestTrafficLight:
    """
    These tests assume simulation/traffic_light.py contains a TrafficLight class
    with at least: state (str), green_duration (int), update(vehicle_count) method.
    Adjust attribute names if yours differ.
    """
    @pytest.fixture
    def traffic_light(self):
        try:
            from traffic_light import TrafficLight
            return TrafficLight()
        except ImportError:
            pytest.skip("simulation/traffic_light.py not importable in test env")

    def test_initial_state_is_string(self, traffic_light):
        assert isinstance(traffic_light.state, str)

    def test_green_duration_positive(self, traffic_light):
        assert traffic_light.green_duration > 0

    def test_high_traffic_extends_green(self, traffic_light):
        traffic_light.update(vehicle_count=50)
        high_duration = traffic_light.green_duration
        traffic_light.update(vehicle_count=1)
        low_duration = traffic_light.green_duration
        assert high_duration >= low_duration, \
            "High traffic should result in equal or longer green duration"

    def test_state_is_valid_value(self, traffic_light):
        valid_states = {"green", "red", "yellow", "GREEN", "RED", "YELLOW"}
        assert traffic_light.state.lower() in {s.lower() for s in valid_states}


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Data / CSV integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestDataIntegrity:
    def test_csv_has_required_columns(self):
        csv_path = os.path.join(ROOT, "data", "traffic_history.csv")
        if not os.path.exists(csv_path):
            pytest.skip("traffic_history.csv not present — skipping data test")

        df = pd.read_csv(csv_path)
        assert len(df) > 0, "CSV should not be empty"
        # At least one numeric column should exist
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        assert len(numeric_cols) >= 1, "CSV should have at least one numeric column"

    def test_no_all_null_columns(self):
        csv_path = os.path.join(ROOT, "data", "traffic_history.csv")
        if not os.path.exists(csv_path):
            pytest.skip("traffic_history.csv not present — skipping data test")

        df = pd.read_csv(csv_path)
        for col in df.columns:
            assert not df[col].isnull().all(), f"Column '{col}' is entirely null"


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Smoke test — imports
# ══════════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_numpy_available(self):
        import numpy
        assert numpy.__version__

    def test_pandas_available(self):
        import pandas
        assert pandas.__version__

    def test_sklearn_available(self):
        import sklearn
        assert sklearn.__version__

    def test_pygame_available(self):
        try:
            import pygame
            assert pygame.version.ver
        except ImportError:
            pytest.skip("pygame not installed")

    def test_ultralytics_available(self):
        try:
            import ultralytics
            assert ultralytics.__version__
        except ImportError:
            pytest.skip("ultralytics not installed — YOLO detection unavailable")