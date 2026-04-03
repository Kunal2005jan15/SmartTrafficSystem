"""
scripts/generate_data.py — Generate synthetic traffic history dataset

Creates a rich traffic_history.csv with realistic daily patterns:
  - Morning rush (07:00–09:00)
  - Midday lull (11:00–13:00)
  - Evening rush (17:00–19:00)
  - Night quiet (22:00–06:00)
  - Random emergency events
  - All three traffic modes

Usage:
    python scripts/generate_data.py --days 7 --out data/traffic_history.csv
"""

import csv
import math
import random
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


TICKS_PER_HOUR   = 3600       # 60 fps × 60 seconds
TICKS_PER_DAY    = TICKS_PER_HOUR * 24


def traffic_density(hour_frac: float, base_ns: float = 8, base_ew: float = 7) -> tuple[float, float]:
    """
    Returns (ns_density, ew_density) for a given fractional hour of day (0–24).
    Models two rush peaks and a night trough.
    """
    # Morning rush: peak at 08:00
    morning = math.exp(-((hour_frac - 8.0) ** 2) / 1.5) * 12
    # Evening rush: peak at 17:30
    evening = math.exp(-((hour_frac - 17.5) ** 2) / 1.8) * 10
    # Night trough (quiet after 22:00 until 06:00)
    night_suppress = max(0.0, 1.0 - math.exp(-((hour_frac - 23) ** 2) / 3))
    if hour_frac < 6:
        night_suppress = max(0.0, 1.0 - math.exp(-((hour_frac + 1) ** 2) / 3))

    ns = max(0.5, base_ns + morning * 1.1 + evening * 0.9 - night_suppress * 6
             + random.gauss(0, 0.8))
    ew = max(0.5, base_ew + morning * 0.9 + evening * 1.1 - night_suppress * 5
             + random.gauss(0, 0.7))
    return ns, ew


def determine_mode(hour_frac: float, ns: float) -> str:
    if 22 <= hour_frac or hour_frac < 6:
        return "night"
    if (7 <= hour_frac <= 9) or (17 <= hour_frac <= 19):
        if ns > 10:
            return "rush_hour"
    return "normal"


def generate(days: int, out_path: str, seed: int, ticks_per_hour: int):
    random.seed(seed)
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)

    tpd = ticks_per_hour * 24
    total_ticks = days * tpd

    print(f"Generating {total_ticks:,} ticks ({days} days) → {out_path}")

    phase, state, phase_timer = 0, "green", 0
    green_dur  = 25 * 60
    yellow_dur = 3  * 60
    allred_dur = 1  * 60

    ns_queue, ew_queue = 0, 0

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "tick", "day", "hour", "minute", "time_of_day",
            "ns_count", "ew_count", "ns_queue", "ew_queue",
            "total_vehicles", "signal_phase", "signal_state",
            "mode", "emergency", "avg_wait_s",
        ])

        for tick in range(total_ticks):
            day       = tick // tpd
            tick_day  = tick % tpd
            hour_frac = tick_day / ticks_per_hour
            hour      = int(hour_frac)
            minute    = int((hour_frac - hour) * 60)
            tod       = tick_day / tpd   # 0–1

            ns_raw, ew_raw = traffic_density(hour_frac)
            ns_count = max(0, int(round(ns_raw)))
            ew_count = max(0, int(round(ew_raw)))

            # Queues depend on signal phase
            if state == "green":
                if phase == 0:
                    ns_queue = max(0, ns_queue - 2 + random.randint(0, 2))
                    ew_queue = min(ew_queue + random.randint(0, 2), ew_count)
                else:
                    ew_queue = max(0, ew_queue - 2 + random.randint(0, 2))
                    ns_queue = min(ns_queue + random.randint(0, 2), ns_count)
            else:
                ns_queue = min(ns_queue + random.randint(0, 1), ns_count)
                ew_queue = min(ew_queue + random.randint(0, 1), ew_count)

            # State machine
            phase_timer += 1
            if state == "green"   and phase_timer >= green_dur:
                state, phase_timer = "yellow",  0
            elif state == "yellow"  and phase_timer >= yellow_dur:
                state, phase_timer = "all_red", 0
            elif state == "all_red" and phase_timer >= allred_dur:
                phase, state, phase_timer = 1 - phase, "green", 0
                # Adaptive green based on queues
                demand    = (ns_queue if phase == 0 else ew_queue)
                ratio     = min(demand / 20.0, 1.0)
                green_dur = int((10 + (60 - 10) * ratio) * 60)

            mode      = determine_mode(hour_frac, ns_raw)
            emergency = 1 if random.random() < 0.003 else 0
            avg_wait  = round(random.gauss(4 + ns_queue * 0.5 + ew_queue * 0.3, 0.5), 2)

            writer.writerow([
                tick, day, hour, minute, round(tod, 4),
                ns_count, ew_count, ns_queue, ew_queue,
                ns_count + ew_count,
                phase, state,
                mode, emergency,
                max(0.0, avg_wait),
            ])

            if tick % 50_000 == 0:
                print(f"  {tick:>8,} / {total_ticks:,} ticks  ({tick/total_ticks*100:.0f}%)")

    size_kb = os.path.getsize(out_path) // 1024
    print(f"Done. {out_path}  ({size_kb:,} KB, {total_ticks:,} rows)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic traffic dataset")
    parser.add_argument("--days",  type=int,   default=7,
                        help="Number of simulated days (default: 7)")
    parser.add_argument("--out",   default="data/traffic_history.csv",
                        help="Output CSV path")
    parser.add_argument("--seed",  type=int,   default=42)
    parser.add_argument("--tph",   type=int,   default=360,
                        help="Ticks per hour (default: 360 = 1 tick/10s)")
    args = parser.parse_args()
    generate(args.days, args.out, args.seed, args.tph)
