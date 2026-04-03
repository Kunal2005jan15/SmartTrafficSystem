"""
Smart Traffic Management System — Intersection Manager

Coordinates vehicle spawning, movement, collision avoidance,
emergency detection, and feeds data to the ML predictor.
"""

import random
import math
import pygame
from simulation.config import (
    C, FPS, SPAWN_POINTS, VEHICLE_TYPES, EMERGENCY_PROB,
    SPAWN_INTERVAL_BASE, SPAWN_INTERVAL_RUSH, NIGHT_DENSITY_MULT,
    CX, CY, ROAD_W, STOP_DIST, SIM_X, SIM_Y, MODE_RUSH_HOUR, MODE_NIGHT
)
from simulation.vehicle import Vehicle
from simulation.traffic_light import IntersectionController
from simulation.ml_predictor import MLPredictor


VEHICLE_TYPE_POOL = (
    ["car"] * 70 + ["truck"] * 15 + ["bus"] * 10 + ["emergency"] * 5
)


class Intersection:
    """
    Top-level simulation manager.
    Owns vehicles, the traffic controller, and the ML predictor.
    """

    def __init__(self):
        self.vehicles:    list[Vehicle]       = []
        self.controller:  IntersectionController = IntersectionController()
        self.predictor:   MLPredictor         = MLPredictor()

        self.tick         = 0
        self.spawn_timer  = {sp[2]: 0 for sp in SPAWN_POINTS}
        self.mode         = "normal"
        self.paused       = False

        # Stats
        self.total_vehicles_spawned  = 0
        self.total_vehicles_passed   = 0
        self.emergency_events        = 0
        self.wait_times: list[float] = []   # wait in seconds per cleared vehicle
        self.throughput_log: list[int] = [] # vehicles cleared per 60-tick window
        self._throughput_window = 0

        # Alerts
        self.alerts: list[dict] = []   # {msg, color, ttl}
        self.emergency_msg_ttl = 0

    # ── Main Update ───────────────────────────────────────────────────────────

    def update(self):
        if self.paused:
            return

        self.tick += 1

        # Spawn
        self._maybe_spawn()

        # ML prediction
        ns_count = sum(1 for v in self.vehicles if v.active and v.direction in ("N→S", "S→N"))
        ew_count = sum(1 for v in self.vehicles if v.active and v.direction in ("E→W", "W→E"))
        ns_queue = sum(1 for v in self.vehicles if v.active and v.stopped and v.direction in ("N→S", "S→N"))
        ew_queue = sum(1 for v in self.vehicles if v.active and v.stopped and v.direction in ("E→W", "W→E"))

        self.predictor.record(self.tick, ns_count, ew_count, ns_queue, ew_queue)
        ml_pred = self.predictor.predict(self.tick)

        # Detect approaching emergency vehicles
        self._check_emergency_vehicles()

        # Traffic controller update
        self.controller.update(self.vehicles, ml_pred)

        # Move vehicles
        for v in self.vehicles:
            can_go = self.controller.is_green_for(v.direction) or v.is_emergency
            v.move(can_go)

        # Clear passed/off-screen vehicles & collect stats
        self._collect_stats()
        self._prune_vehicles()

        # Throughput logging (per 60 ticks)
        self._throughput_window += 1
        if self._throughput_window >= 60:
            self.throughput_log.append(self._count_passed_in_window())
            if len(self.throughput_log) > 300:
                self.throughput_log.pop(0)
            self._throughput_window = 0

        # Tick alerts
        self.alerts = [a for a in self.alerts if a["ttl"] > 0]
        for a in self.alerts:
            a["ttl"] -= 1

    def _count_passed_in_window(self) -> int:
        """Count vehicles that cleared the intersection in the last window."""
        # Proxy: vehicles that left the active list this window
        return self.total_vehicles_passed

    # ── Spawning ──────────────────────────────────────────────────────────────

    def _spawn_interval(self) -> int:
        if self.mode == MODE_RUSH_HOUR:
            return SPAWN_INTERVAL_RUSH
        if self.mode == MODE_NIGHT:
            return int(SPAWN_INTERVAL_BASE / NIGHT_DENSITY_MULT)
        return SPAWN_INTERVAL_BASE

    def _maybe_spawn(self):
        interval = self._spawn_interval()
        for sp in SPAWN_POINTS:
            x0, y0, direction, dx, dy = sp
            self.spawn_timer[direction] = self.spawn_timer.get(direction, 0) + 1
            jitter = random.randint(-interval // 4, interval // 4)
            if self.spawn_timer[direction] < interval + jitter:
                continue
            self.spawn_timer[direction] = 0
            self._spawn_vehicle(x0, y0, dx, dy, direction)

    def _spawn_vehicle(self, x, y, dx, dy, direction):
        # Pick type
        vtype = random.choice(VEHICLE_TYPE_POOL)
        is_emergency = (vtype == "emergency") or (random.random() < EMERGENCY_PROB)
        if is_emergency:
            vtype = "emergency"

        v = Vehicle(x, y, dx, dy, direction, vtype=vtype, is_emergency=is_emergency)
        self.vehicles.append(v)
        self.total_vehicles_spawned += 1

        if is_emergency:
            self.emergency_events += 1
            self._push_alert(f"🚨 Emergency vehicle approaching from {direction}!", C["danger"], ttl=FPS * 5)

    # ── Emergency detection ───────────────────────────────────────────────────

    def _check_emergency_vehicles(self):
        """Find approaching emergency vehicles and trigger preemption."""
        preempt_dist = ROAD_W * 4.5
        for v in self.vehicles:
            if not v.active or not v.is_emergency or v.passed:
                continue
            dist = v.distance_to_intersection()
            if dist < preempt_dist:
                if not self.controller.emergency_active:
                    self.controller.trigger_emergency(v.id, v.direction)

        # Clear if no active emergency vehicles remain nearby
        if self.controller.emergency_active:
            still_active = any(
                v.active and v.is_emergency and not v.passed
                and v.distance_to_intersection() < ROAD_W * 6
                for v in self.vehicles
            )
            if not still_active:
                self.controller.clear_emergency()

    # ── Stats & Cleanup ───────────────────────────────────────────────────────

    def _collect_stats(self):
        for v in self.vehicles:
            if not v.active and v.passed and v.waiting_ticks > 0:
                wait_s = v.waiting_ticks / FPS
                self.wait_times.append(wait_s)
                if len(self.wait_times) > 500:
                    self.wait_times.pop(0)
                self.total_vehicles_passed += 1

    def _prune_vehicles(self):
        self.vehicles = [v for v in self.vehicles if v.active]

    # ── Alerts ────────────────────────────────────────────────────────────────

    def _push_alert(self, msg: str, color, ttl: int = FPS * 3):
        self.alerts.append({"msg": msg, "color": color, "ttl": ttl})
        if len(self.alerts) > 5:
            self.alerts.pop(0)

    # ── Mode control ──────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        if mode == self.mode:
            return
        self.mode = mode
        labels = {
            "normal":     ("Normal traffic", C["accent"]),
            "rush_hour":  ("Rush hour activated!", C["warn"]),
            "night":      ("Night mode — low density", C["info"]),
        }
        msg, col = labels.get(mode, ("Mode changed", C["text"]))
        self._push_alert(msg, col)

    def spawn_emergency(self):
        """Manually trigger an emergency vehicle from a random direction."""
        sp = random.choice(SPAWN_POINTS)
        x0, y0, direction, dx, dy = sp
        v = Vehicle(x0, y0, dx, dy, direction, vtype="emergency", is_emergency=True)
        self.vehicles.append(v)
        self.total_vehicles_spawned += 1
        self.emergency_events += 1
        self._push_alert(f"🚨 Manual: Emergency vehicle → {direction}", C["danger"], ttl=FPS * 5)

    # ── Accessors ─────────────────────────────────────────────────────────────

    def avg_wait(self) -> float:
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times[-50:]) / len(self.wait_times[-50:])

    def current_density(self) -> dict:
        ns = sum(1 for v in self.vehicles if v.active and v.direction in ("N→S", "S→N"))
        ew = sum(1 for v in self.vehicles if v.active and v.direction in ("E→W", "W→E"))
        return {"ns": ns, "ew": ew, "total": ns + ew}

    def queue_lengths(self) -> dict:
        ns = sum(1 for v in self.vehicles if v.active and v.stopped and v.direction in ("N→S", "S→N"))
        ew = sum(1 for v in self.vehicles if v.active and v.stopped and v.direction in ("E→W", "W→E"))
        return {"ns": ns, "ew": ew}

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, surface, tick: int):
        self._draw_road(surface)
        self.controller.draw(surface, tick)

        for v in self.vehicles:
            v.draw(surface, tick)

        self._draw_stop_lines(surface)
        self._draw_alerts(surface, tick)

    def _draw_road(self, surface):
        # Background fill is handled by main.py
        w, h = SIM_X, SIM_Y

        # Grass / sidewalk borders
        surface.fill(C["grass"])

        # Horizontal road corridor
        road_rect_h = pygame.Rect(0, CY - ROAD_W // 2, SIM_X, ROAD_W)
        pygame.draw.rect(surface, C["road"], road_rect_h)

        # Vertical road corridor
        road_rect_v = pygame.Rect(CX - ROAD_W // 2, 0, ROAD_W, SIM_Y)
        pygame.draw.rect(surface, C["road"], road_rect_v)

        # Intersection box
        int_rect = pygame.Rect(CX - ROAD_W // 2, CY - ROAD_W // 2, ROAD_W, ROAD_W)
        pygame.draw.rect(surface, C["road"], int_rect)

        # Centre dashed lane dividers
        dash_w, dash_gap = 12, 10
        # Horizontal centre line
        cx = 0
        while cx < SIM_X:
            if not (CX - ROAD_W // 2 - 4 < cx < CX + ROAD_W // 2 + 4):
                pygame.draw.rect(surface, C["road_stripe"], (cx, CY - 2, dash_w, 4))
            cx += dash_w + dash_gap

        # Vertical centre line
        cy = 0
        while cy < SIM_Y:
            if not (CY - ROAD_W // 2 - 4 < cy < CY + ROAD_W // 2 + 4):
                pygame.draw.rect(surface, C["road_stripe"], (CX - 2, cy, 4, dash_w))
            cy += dash_w + dash_gap

        # Road edge lines
        for offset in [-ROAD_W // 2, ROAD_W // 2]:
            pygame.draw.line(surface, C["road_line"], (0, CY + offset), (CX - ROAD_W // 2, CY + offset), 1)
            pygame.draw.line(surface, C["road_line"], (CX + ROAD_W // 2, CY + offset), (SIM_X, CY + offset), 1)
            pygame.draw.line(surface, C["road_line"], (CX + offset, 0), (CX + offset, CY - ROAD_W // 2), 1)
            pygame.draw.line(surface, C["road_line"], (CX + offset, CY + ROAD_W // 2), (CX + offset, SIM_Y), 1)

        # Sidewalks
        sw = 8
        pygame.draw.rect(surface, C["sidewalk"], (0,              CY - ROAD_W // 2 - sw, CX - ROAD_W // 2, sw))
        pygame.draw.rect(surface, C["sidewalk"], (0,              CY + ROAD_W // 2,      CX - ROAD_W // 2, sw))
        pygame.draw.rect(surface, C["sidewalk"], (CX + ROAD_W // 2, CY - ROAD_W // 2 - sw, SIM_X - CX - ROAD_W // 2, sw))
        pygame.draw.rect(surface, C["sidewalk"], (CX + ROAD_W // 2, CY + ROAD_W // 2,      SIM_X - CX - ROAD_W // 2, sw))

        # Zebra crossings
        self._draw_crosswalk(surface, CX - ROAD_W // 2 - 28, CY - ROAD_W // 2, horizontal=False)
        self._draw_crosswalk(surface, CX + ROAD_W // 2 + 4,  CY - ROAD_W // 2, horizontal=False)
        self._draw_crosswalk(surface, CX - ROAD_W // 2, CY - ROAD_W // 2 - 28, horizontal=True)
        self._draw_crosswalk(surface, CX - ROAD_W // 2, CY + ROAD_W // 2 + 4,  horizontal=True)

    def _draw_crosswalk(self, surface, x, y, horizontal: bool):
        stripe_w, stripe_h = (24, 5) if horizontal else (5, 24)
        for i in range(5):
            if horizontal:
                sx = x + i * (stripe_w + 2)
                pygame.draw.rect(surface, (200, 200, 200), (sx, y, stripe_w, stripe_h))
            else:
                sy = y + i * (stripe_h + 2)
                pygame.draw.rect(surface, (200, 200, 200), (x, sy, stripe_w, stripe_h))

    def _draw_stop_lines(self, surface):
        color = (200, 50, 50)
        hw = ROAD_W // 2
        # N approach
        pygame.draw.line(surface, color, (CX - hw, CY - STOP_DIST), (CX + hw, CY - STOP_DIST), 2)
        # S approach
        pygame.draw.line(surface, color, (CX - hw, CY + STOP_DIST), (CX + hw, CY + STOP_DIST), 2)
        # W approach
        pygame.draw.line(surface, color, (CX - STOP_DIST, CY - hw), (CX - STOP_DIST, CY + hw), 2)
        # E approach
        pygame.draw.line(surface, color, (CX + STOP_DIST, CY - hw), (CX + STOP_DIST, CY + hw), 2)

    def _draw_alerts(self, surface, tick: int):
        font = pygame.font.SysFont("monospace", 11, bold=True)
        y = SIM_Y - 14
        for alert in reversed(self.alerts[-3:]):
            alpha = min(255, alert["ttl"] * 8)
            txt   = font.render(alert["msg"], True, alert["color"])
            surface.blit(txt, (10, y))
            y -= 18
