"""
Smart Traffic Management System — ML Traffic Predictor

Uses a sliding-window feature matrix fed into a scikit-learn
RandomForestRegressor (one per axis: N-S and E-W) to predict
vehicle density PRED_HORIZON ticks ahead.

Features per window step:
  [ns_count, ew_count, ns_queue, ew_queue, time_of_day_sin, time_of_day_cos]

The model is trained online as the simulation runs, so predictions
improve over time.  An initial synthetic warm-up dataset primes the
model before live data accumulates.
"""

import math
import random
import numpy as np
from collections import deque

from simulation.config import HISTORY_LEN, PRED_HORIZON, FPS

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[ML] scikit-learn not found — using heuristic predictor.")


class MLPredictor:
    """
    Online traffic density predictor.
    Trains incrementally on the live simulation data.
    """

    FEATURE_DIM = 6    # features per time-step

    def __init__(self):
        self.history_ns    = deque(maxlen=HISTORY_LEN + PRED_HORIZON + 10)
        self.history_ew    = deque(maxlen=HISTORY_LEN + PRED_HORIZON + 10)
        self.history_qns   = deque(maxlen=HISTORY_LEN + PRED_HORIZON + 10)
        self.history_qew   = deque(maxlen=HISTORY_LEN + PRED_HORIZON + 10)
        self.tick_log      = deque(maxlen=HISTORY_LEN + PRED_HORIZON + 10)

        self.trained       = False
        self.train_counter = 0
        self.retrain_every = 60    # retrain model every N ticks

        self.scaler_ns     = None
        self.scaler_ew     = None
        self.model_ns      = None
        self.model_ew      = None

        self.last_pred     = {"predicted_ns": 5.0, "predicted_ew": 5.0,
                               "confidence": 0.0,   "model_type": "warmup"}

        # Warm-up synthetic data so model is usable from tick 1
        self._generate_warmup_data()

    # ── Data ingestion ────────────────────────────────────────────────────────

    def record(self, tick: int, ns_count: int, ew_count: int,
               ns_queue: int, ew_queue: int):
        """Call every simulation tick to log traffic state."""
        self.history_ns.append(ns_count)
        self.history_ew.append(ew_count)
        self.history_qns.append(ns_queue)
        self.history_qew.append(ew_queue)
        self.tick_log.append(tick)

        self.train_counter += 1
        if self.train_counter >= self.retrain_every:
            self.train_counter = 0
            self._retrain()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, tick: int) -> dict:
        """Return predicted NS and EW density PRED_HORIZON ticks ahead."""
        if not self.trained or not ML_AVAILABLE:
            return self._heuristic_predict()

        feat = self._extract_latest_features(tick)
        if feat is None:
            return self._heuristic_predict()

        try:
            X = np.array(feat).reshape(1, -1)
            X_ns = self.scaler_ns.transform(X)
            X_ew = self.scaler_ew.transform(X)
            pred_ns = float(self.model_ns.predict(X_ns)[0])
            pred_ew = float(self.model_ew.predict(X_ew)[0])
            pred_ns = max(0.0, pred_ns)
            pred_ew = max(0.0, pred_ew)
            self.last_pred = {
                "predicted_ns": pred_ns,
                "predicted_ew": pred_ew,
                "confidence":   0.85,
                "model_type":   "RandomForest",
            }
        except Exception:
            return self._heuristic_predict()

        return self.last_pred

    def _heuristic_predict(self) -> dict:
        """Fallback: use recent average with light trend."""
        if len(self.history_ns) < 5:
            return {"predicted_ns": 5.0, "predicted_ew": 5.0,
                    "confidence": 0.0, "model_type": "heuristic"}
        recent_ns = list(self.history_ns)[-20:]
        recent_ew = list(self.history_ew)[-20:]
        pred_ns   = sum(recent_ns) / len(recent_ns)
        pred_ew   = sum(recent_ew) / len(recent_ew)
        return {"predicted_ns": pred_ns, "predicted_ew": pred_ew,
                "confidence": 0.4, "model_type": "heuristic"}

    # ── Training ──────────────────────────────────────────────────────────────

    def _retrain(self):
        if not ML_AVAILABLE:
            return
        if len(self.history_ns) < HISTORY_LEN + PRED_HORIZON:
            return

        X_list, y_ns, y_ew = [], [], []
        hist_len = len(self.history_ns)
        ns_arr   = list(self.history_ns)
        ew_arr   = list(self.history_ew)
        qns_arr  = list(self.history_qns)
        qew_arr  = list(self.history_qew)
        tk_arr   = list(self.tick_log)

        for i in range(HISTORY_LEN, hist_len - PRED_HORIZON):
            feat = self._build_features(
                ns_arr[i - HISTORY_LEN:i],
                ew_arr[i - HISTORY_LEN:i],
                qns_arr[i - HISTORY_LEN:i],
                qew_arr[i - HISTORY_LEN:i],
                tk_arr[i],
            )
            X_list.append(feat)
            y_ns.append(ns_arr[i + PRED_HORIZON])
            y_ew.append(ew_arr[i + PRED_HORIZON])

        if len(X_list) < 20:
            return

        X  = np.array(X_list)
        yn = np.array(y_ns)
        ye = np.array(y_ew)

        try:
            self.scaler_ns = StandardScaler().fit(X)
            self.scaler_ew = StandardScaler().fit(X)
            Xn = self.scaler_ns.transform(X)
            Xe = self.scaler_ew.transform(X)

            self.model_ns = RandomForestRegressor(
                n_estimators=40, max_depth=6, random_state=42, n_jobs=-1
            )
            self.model_ew = RandomForestRegressor(
                n_estimators=40, max_depth=6, random_state=42, n_jobs=-1
            )
            self.model_ns.fit(Xn, yn)
            self.model_ew.fit(Xe, ye)
            self.trained = True
        except Exception as exc:
            print(f"[ML] Training failed: {exc}")

    def _build_features(self, ns_win, ew_win, qns_win, qew_win, tick) -> list:
        """Aggregate a HISTORY_LEN window into a fixed feature vector."""
        ns_arr  = np.array(ns_win, dtype=float)
        ew_arr  = np.array(ew_win, dtype=float)
        # Time-of-day encoding (simulate a 10-minute day cycle in ticks)
        day_cycle = (tick / (FPS * 600)) * 2 * math.pi
        features = [
            float(np.mean(ns_arr)),
            float(np.mean(ew_arr)),
            float(np.max(ns_arr)),
            float(np.max(ew_arr)),
            float(np.std(ns_arr)),
            float(np.std(ew_arr)),
            float(np.mean(qns_win)),
            float(np.mean(qew_win)),
            math.sin(day_cycle),
            math.cos(day_cycle),
            float(ns_arr[-1]),
            float(ew_arr[-1]),
        ]
        return features

    def _extract_latest_features(self, tick) -> list | None:
        if len(self.history_ns) < HISTORY_LEN:
            return None
        ns_win  = list(self.history_ns)[-HISTORY_LEN:]
        ew_win  = list(self.history_ew)[-HISTORY_LEN:]
        qns_win = list(self.history_qns)[-HISTORY_LEN:]
        qew_win = list(self.history_qew)[-HISTORY_LEN:]
        return self._build_features(ns_win, ew_win, qns_win, qew_win, tick)

    # ── Warm-up ───────────────────────────────────────────────────────────────

    def _generate_warmup_data(self):
        """
        Synthetic traffic cycle data to prime the model before live data.
        Simulates a 10-min day with morning and evening rush peaks.
        """
        ticks_per_minute = FPS * 60
        total_ticks      = HISTORY_LEN + PRED_HORIZON + 200

        for t in range(total_ticks):
            day_frac = (t % (ticks_per_minute * 10)) / (ticks_per_minute * 10)

            # Two rush-hour peaks: 0.25 and 0.75 through the day cycle
            rush_ns = (math.exp(-((day_frac - 0.25) ** 2) / 0.005) * 14
                       + math.exp(-((day_frac - 0.75) ** 2) / 0.005) * 10 + 2)
            rush_ew = (math.exp(-((day_frac - 0.30) ** 2) / 0.005) * 12
                       + math.exp(-((day_frac - 0.70) ** 2) / 0.005) * 11 + 2)

            ns = max(0, int(rush_ns + random.gauss(0, 1)))
            ew = max(0, int(rush_ew + random.gauss(0, 1)))
            self.history_ns.append(ns)
            self.history_ew.append(ew)
            self.history_qns.append(max(0, ns - 3))
            self.history_qew.append(max(0, ew - 3))
            self.tick_log.append(t)

        self._retrain()

    # ── Accessors for dashboard ───────────────────────────────────────────────

    def get_history_ns(self) -> list:
        return list(self.history_ns)

    def get_history_ew(self) -> list:
        return list(self.history_ew)

    def get_model_info(self) -> str:
        if not self.trained:
            return "Warming up…"
        return f"RF · {len(self.history_ns)} samples"
