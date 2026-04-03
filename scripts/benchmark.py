"""
scripts/benchmark.py — Compare adaptive vs fixed-timing signal control

Runs the simulation twice (same random seed, same traffic):
  Run A: Adaptive ML-based green timing (default)
  Run B: Fixed 25-second green timing

Reports:
  - Average wait time
  - Total throughput
  - Emergency clearance time

Usage:
    python scripts/benchmark.py --ticks 3600 --mode rush_hour
"""

import sys
import os
import argparse
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


def run_simulation(ticks: int, mode: str, fixed_green: int | None, seed: int) -> dict:
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    random.seed(seed)

    from simulation.intersection import Intersection
    from simulation.config       import FPS

    intersection = Intersection()
    intersection.set_mode(mode)

    if fixed_green is not None:
        # Override adaptive timing with a fixed duration
        ctrl = intersection.controller
        ctrl.green_duration = fixed_green * FPS
        original_compute = ctrl._compute_adaptive_green
        ctrl._compute_adaptive_green = lambda *_: fixed_green * FPS

    for tick in range(ticks):
        intersection.update()

    result = {
        "avg_wait_s":     round(intersection.avg_wait(), 3),
        "total_passed":   intersection.total_vehicles_passed,
        "total_spawned":  intersection.total_vehicles_spawned,
        "throughput_pct": round(
            intersection.total_vehicles_passed / max(intersection.total_vehicles_spawned, 1) * 100, 1
        ),
        "emergency_events": intersection.emergency_events,
    }

    pygame.quit()
    return result


def benchmark(ticks: int, mode: str, fixed_green: int, seed: int):
    print(f"\n{'='*56}")
    print(f"  Benchmark: {ticks} ticks, mode={mode}, seed={seed}")
    print(f"{'='*56}")

    print("\n[A] Adaptive ML timing...")
    result_a = run_simulation(ticks, mode, fixed_green=None, seed=seed)

    print("[B] Fixed timing ({fixed_green}s green)...".format(fixed_green=fixed_green))
    result_b = run_simulation(ticks, mode, fixed_green=fixed_green, seed=seed)

    print(f"\n{'─'*56}")
    print(f"  {'Metric':<28} {'Adaptive':>10}  {'Fixed':>10}  {'Delta':>10}")
    print(f"{'─'*56}")

    metrics = [
        ("Avg wait (s)",      "avg_wait_s",     True),
        ("Total passed",      "total_passed",   False),
        ("Throughput (%)",    "throughput_pct", False),
        ("Emergency events",  "emergency_events", None),
    ]

    for label, key, lower_is_better in metrics:
        va = result_a[key]
        vb = result_b[key]
        if lower_is_better is not None:
            delta = va - vb
            delta_str = f"{delta:+.1f}" if isinstance(delta, float) else f"{delta:+d}"
            better = "✓ A" if (lower_is_better and delta < 0) or (not lower_is_better and delta > 0) else "✓ B"
        else:
            delta_str = "—"
            better    = "—"
        print(f"  {label:<28} {str(va):>10}  {str(vb):>10}  {delta_str:>7}  {better}")

    print(f"{'─'*56}")
    print(f"\n  Adaptive wait improvement: "
          f"{result_b['avg_wait_s'] - result_a['avg_wait_s']:+.2f}s\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive vs Fixed timing benchmark")
    parser.add_argument("--ticks",       type=int, default=3600)
    parser.add_argument("--mode",        default="rush_hour",
                        choices=["normal", "rush_hour", "night"])
    parser.add_argument("--fixed-green", type=int, default=25,
                        help="Fixed green time in seconds for comparison")
    parser.add_argument("--seed",        type=int, default=42)
    args = parser.parse_args()
    benchmark(args.ticks, args.mode, args.fixed_green, args.seed)
