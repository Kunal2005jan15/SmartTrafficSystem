"""
simulation/stats.py — In-memory stats collector + CSV/JSON exporter

Collects fine-grained per-tick metrics during a simulation run and
exports them to CSV or JSON for offline analysis / model training.

Usage:
    from simulation.stats import StatsCollector
    stats = StatsCollector()
    stats.record(tick, intersection, ml_pred)
    stats.export_csv("data/run_001.csv")
    stats.summary()
"""

import csv
import json
import os
import math
from collections import deque


class StatsCollector:
    """Accumulates simulation metrics in memory and exports them."""

    MAX_RECORDS = 18_000   # 5 minutes at 60 fps — beyond this, rotate

    def __init__(self):
        self.records:  list[dict] = []
        self._tick_map: dict[int, dict] = {}

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, tick: int, intersection, ml_pred: dict):
        """Call every simulation tick."""
        ctrl   = intersection.controller
        dens   = intersection.current_density()
        queues = intersection.queue_lengths()

        row = {
            "tick":              tick,
            "time_s":            tick / 60,
            "ns_count":          dens["ns"],
            "ew_count":          dens["ew"],
            "total_vehicles":    dens["total"],
            "ns_queue":          queues["ns"],
            "ew_queue":          queues["ew"],
            "avg_wait_s":        round(intersection.avg_wait(), 3),
            "total_passed":      intersection.total_vehicles_passed,
            "total_spawned":     intersection.total_vehicles_spawned,
            "emergency_events":  intersection.emergency_events,
            "emergency_active":  int(ctrl.emergency_active),
            "phase":             ctrl.phase,
            "signal_state":      ctrl.state,
            "green_remaining_s": round(ctrl.seconds_remaining(), 2),
            "adaptive_green_s":  round(ctrl.green_duration / 60, 2),
            "mode":              intersection.mode,
            "pred_ns":           round(ml_pred.get("predicted_ns", 0), 3),
            "pred_ew":           round(ml_pred.get("predicted_ew", 0), 3),
            "ml_confidence":     round(ml_pred.get("confidence", 0), 3),
        }

        self.records.append(row)
        if len(self.records) > self.MAX_RECORDS:
            self.records.pop(0)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self, path: str):
        """Write all collected records to a CSV file."""
        if not self.records:
            print("[Stats] No records to export.")
            return

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.records[0].keys())
            writer.writeheader()
            writer.writerows(self.records)
        print(f"[Stats] Exported {len(self.records)} records → {path}")

    def export_json(self, path: str):
        """Write summary statistics to JSON."""
        summary = self._compute_summary()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[Stats] Summary exported → {path}")

    # ── Summary ───────────────────────────────────────────────────────────────

    def _compute_summary(self) -> dict:
        if not self.records:
            return {}

        waits    = [r["avg_wait_s"]   for r in self.records if r["avg_wait_s"] > 0]
        ns_vals  = [r["ns_count"]     for r in self.records]
        ew_vals  = [r["ew_count"]     for r in self.records]
        total    = [r["total_vehicles"] for r in self.records]

        def safe_avg(lst): return sum(lst) / len(lst) if lst else 0.0
        def safe_max(lst): return max(lst) if lst else 0

        return {
            "total_ticks":          len(self.records),
            "simulation_time_s":    self.records[-1]["time_s"] if self.records else 0,
            "total_vehicles_passed": self.records[-1]["total_passed"] if self.records else 0,
            "total_spawned":        self.records[-1]["total_spawned"] if self.records else 0,
            "emergency_events":     self.records[-1]["emergency_events"] if self.records else 0,
            "avg_wait_s":           round(safe_avg(waits), 3),
            "max_wait_s":           round(safe_max(waits), 3),
            "avg_ns_density":       round(safe_avg(ns_vals), 2),
            "avg_ew_density":       round(safe_avg(ew_vals), 2),
            "peak_total_vehicles":  safe_max(total),
            "avg_total_vehicles":   round(safe_avg(total), 2),
        }

    def summary(self):
        """Print a human-readable summary to console."""
        s = self._compute_summary()
        if not s:
            print("[Stats] No data yet.")
            return
        print("\n" + "=" * 48)
        print("  Simulation Summary")
        print("=" * 48)
        for k, v in s.items():
            print(f"  {k:<30} {v}")
        print("=" * 48 + "\n")

    # ── Accessors ─────────────────────────────────────────────────────────────

    def last_n(self, n: int) -> list[dict]:
        return self.records[-n:]

    def __len__(self):
        return len(self.records)
