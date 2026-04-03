"""
simulation/logger.py — Structured simulation event logger

Writes a timestamped CSV log of key simulation events:
  - Phase changes
  - Emergency events
  - Mode changes
  - Per-tick stats snapshot (every N ticks)

Usage:
    from simulation.logger import SimLogger
    log = SimLogger()
    log.event("phase_change", phase=1, green_duration=30.2)
    log.snapshot(tick=120, ns=8, ew=5, avg_wait=4.1)
    log.close()
"""

import csv
import os
import time
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


class SimLogger:
    """
    Lightweight CSV event logger.
    Creates two files per session:
      logs/events_<timestamp>.csv   — discrete events
      logs/stats_<timestamp>.csv    — per-tick snapshots
    """

    SNAPSHOT_EVERY = 60   # ticks between stat snapshots

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        if not enabled:
            return

        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._event_path = os.path.join(LOG_DIR, f"events_{ts}.csv")
        self._stats_path = os.path.join(LOG_DIR, f"stats_{ts}.csv")

        self._event_file = open(self._event_path, "w", newline="")
        self._stats_file = open(self._stats_path, "w", newline="")

        self._event_writer = csv.writer(self._event_file)
        self._stats_writer = csv.writer(self._stats_file)

        self._event_writer.writerow(["wall_time", "sim_tick", "event_type", "details"])
        self._stats_writer.writerow([
            "wall_time", "sim_tick", "ns_count", "ew_count",
            "ns_queue", "ew_queue", "avg_wait_s", "phase",
            "signal_state", "green_remaining_s", "total_passed",
            "emergency_active", "mode", "pred_ns", "pred_ew",
        ])

        self._event_file.flush()
        self._stats_file.flush()
        print(f"[Logger] Events → {self._event_path}")
        print(f"[Logger] Stats  → {self._stats_path}")

    # ── Events ────────────────────────────────────────────────────────────────

    def event(self, event_type: str, tick: int = 0, **kwargs):
        if not self.enabled:
            return
        details = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        self._event_writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            tick,
            event_type,
            details,
        ])
        self._event_file.flush()

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self, tick: int, intersection, ml_pred: dict):
        if not self.enabled:
            return
        if tick % self.SNAPSHOT_EVERY != 0:
            return

        ctrl   = intersection.controller
        dens   = intersection.current_density()
        queues = intersection.queue_lengths()

        self._stats_writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            tick,
            dens["ns"],
            dens["ew"],
            queues["ns"],
            queues["ew"],
            f"{intersection.avg_wait():.2f}",
            ctrl.phase,
            ctrl.state,
            f"{ctrl.seconds_remaining():.1f}",
            intersection.total_vehicles_passed,
            int(ctrl.emergency_active),
            intersection.mode,
            f"{ml_pred.get('predicted_ns', 0):.2f}",
            f"{ml_pred.get('predicted_ew', 0):.2f}",
        ])
        self._stats_file.flush()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self):
        if not self.enabled:
            return
        self._event_file.close()
        self._stats_file.close()
        print(f"[Logger] Session closed.")
