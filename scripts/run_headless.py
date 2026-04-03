"""
scripts/run_headless.py — Headless simulation runner

Runs the simulation for N ticks without a display window.
Useful for:
  - Generating training data for the ML predictor
  - Benchmarking adaptive vs fixed-timing performance
  - CI/CD pipeline testing

Usage:
    python scripts/run_headless.py --ticks 3600 --mode rush_hour
    python scripts/run_headless.py --ticks 1800 --emergency-rate 0.05
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Headless pygame (no display)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


def run(ticks: int, mode: str, emergency_rate: float, out_csv: str, quiet: bool):
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))   # minimal surface for headless

    from simulation.intersection import Intersection
    from simulation.stats        import StatsCollector

    intersection = Intersection()
    intersection.set_mode(mode)
    intersection.predictor.EMERGENCY_PROB = emergency_rate
    stats = StatsCollector()

    print_every = max(ticks // 20, 1)

    for tick in range(ticks):
        intersection.update()
        ml_pred = intersection.predictor.predict(tick)
        stats.record(tick, intersection, ml_pred)

        if not quiet and tick % print_every == 0:
            dens  = intersection.current_density()
            print(f"  tick {tick:5d}/{ticks}  "
                  f"NS={dens['ns']:2d}  EW={dens['ew']:2d}  "
                  f"passed={intersection.total_vehicles_passed:4d}  "
                  f"avgwait={intersection.avg_wait():.2f}s")

    stats.export_csv(out_csv)
    stats.summary()
    pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Headless traffic simulation")
    parser.add_argument("--ticks",          type=int,   default=3600,
                        help="Number of simulation ticks (default: 3600 = 1 min)")
    parser.add_argument("--mode",           default="normal",
                        choices=["normal", "rush_hour", "night"],
                        help="Traffic mode")
    parser.add_argument("--emergency-rate", type=float, default=0.02,
                        help="Probability of emergency vehicle per spawn (0–1)")
    parser.add_argument("--out",            default="data/headless_run.csv",
                        help="Output CSV path")
    parser.add_argument("--quiet",          action="store_true")
    args = parser.parse_args()

    print(f"Running headless simulation: {args.ticks} ticks, mode={args.mode}")
    run(args.ticks, args.mode, args.emergency_rate, args.out, args.quiet)
