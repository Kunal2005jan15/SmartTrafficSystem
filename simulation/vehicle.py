"""
Smart Traffic Management System — Vehicle Model
Handles all vehicle types, movement, rendering, and emergency state.
"""

import pygame
import math
import random
from simulation.config import C, VEHICLE_TYPES, VEHICLE_COLORS_EXTRA, CX, CY, ROAD_W, STOP_DIST, SIM_X, SIM_Y


_vid_counter = 0

def _next_id():
    global _vid_counter
    _vid_counter += 1
    return _vid_counter


class Vehicle:
    """
    A single vehicle in the simulation.

    direction: "N→S" | "S→N" | "E→W" | "W→E"
    vtype:     "car" | "truck" | "bus" | "emergency"
    """

    COLORS = [C["car_normal"], C["car_2"], C["car_3"], C["car_4"]]

    def __init__(self, x, y, dx, dy, direction, vtype="car", is_emergency=False):
        self.id          = _next_id()
        self.x           = float(x)
        self.y           = float(y)
        self.dx          = dx          # unit direction vector
        self.dy          = dy
        self.direction   = direction
        self.vtype       = vtype
        self.is_emergency = is_emergency

        cfg              = VEHICLE_TYPES[vtype]
        self.w           = cfg["w"]
        self.h           = cfg["h"]
        self.base_speed  = cfg["speed"]
        self.speed       = self.base_speed
        self.color       = C[cfg["color"]] if not is_emergency else C["emergency"]

        # Pick a unique lane offset so vehicles don't stack on centreline
        self.lane_offset = random.choice([-ROAD_W // 6, 0, ROAD_W // 6])

        # State
        self.stopped       = False
        self.waiting_ticks = 0
        self.passed        = False        # has crossed intersection centre
        self.active        = True
        self.flash_state   = True
        self.flash_timer   = 0

        # Siren animation for emergency vehicles
        self.siren_phase   = random.random() * math.pi * 2
        self.siren_color   = C["emergency"]

        # Apply lane offset to perpendicular axis
        if abs(dx) > 0:           # horizontal movement → offset on Y
            self.y += self.lane_offset
        else:                     # vertical movement → offset on X
            self.x += self.lane_offset

    # ── Movement ──────────────────────────────────────────────────────────────

    def move(self, can_go: bool):
        """Advance the vehicle. Stops at red; continues on green or if emergency."""
        if not self.active:
            return

        # Emergency vehicles always go (handled by intersection preemption)
        if self.is_emergency:
            self._advance()
            return

        if self.stopped and not can_go:
            self.waiting_ticks += 1
            return

        # Check approach to stop line
        at_stop = self._at_stop_line()
        if at_stop and not can_go and not self.passed:
            self.stopped = True
            self.waiting_ticks += 1
            return

        self.stopped = False
        self._advance()

        # Mark as having passed the centre
        if not self.passed:
            dist_to_centre = math.hypot(self.x - CX, self.y - CY)
            if dist_to_centre < 12:
                self.passed = True

        # Deactivate when off-screen
        margin = 60
        if (self.x < -margin or self.x > SIM_X + margin or
                self.y < -margin or self.y > SIM_Y + margin):
            self.active = False

    def _advance(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

    def _at_stop_line(self) -> bool:
        """Returns True if vehicle is within braking distance of its stop line."""
        if self.dy > 0:    # N→S: approaching from top
            stop_y = CY - STOP_DIST
            return self.y < stop_y < self.y + self.speed + 6
        elif self.dy < 0:  # S→N
            stop_y = CY + STOP_DIST
            return self.y > stop_y > self.y - self.speed - 6
        elif self.dx > 0:  # W→E
            stop_x = CX - STOP_DIST
            return self.x < stop_x < self.x + self.speed + 6
        elif self.dx < 0:  # E→W
            stop_x = CX + STOP_DIST
            return self.x > stop_x > self.x - self.speed - 6
        return False

    def distance_to_intersection(self) -> float:
        return math.hypot(self.x - CX, self.y - CY)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def draw(self, surface, tick: int):
        if not self.active:
            return

        # Update siren flash
        self.flash_timer += 1
        if self.flash_timer % 12 == 0:
            self.flash_state = not self.flash_state

        # Determine draw rect (rotated for direction of travel)
        horizontal = abs(self.dx) > 0
        if horizontal:
            bw, bh = self.w, self.h
        else:
            bw, bh = self.h, self.w   # swap for vertical travel

        rect = pygame.Rect(self.x - bw // 2, self.y - bh // 2, bw, bh)

        # Body
        pygame.draw.rect(surface, self.color, rect, border_radius=3)

        # Windshield highlight
        ws_color = (200, 230, 255) if not self.is_emergency else (255, 255, 255)
        if horizontal:
            ws = pygame.Rect(rect.x + (2 if self.dx > 0 else bw - 8), rect.y + 2, 6, bh - 4)
        else:
            ws = pygame.Rect(rect.x + 2, rect.y + (2 if self.dy > 0 else bh - 8), bw - 4, 6)
        pygame.draw.rect(surface, ws_color, ws, border_radius=1)

        # Emergency: siren lights
        if self.is_emergency:
            self._draw_siren(surface, rect, horizontal, tick)

        # Waiting indicator (small pulsing dot above vehicle)
        if self.stopped and self.waiting_ticks > 30:
            pulse = abs(math.sin(tick * 0.05)) * 0.6 + 0.4
            dot_color = (int(C["warn"][0] * pulse), int(C["warn"][1] * pulse), int(C["warn"][2] * pulse))
            pygame.draw.circle(surface, dot_color, (int(rect.centerx), int(rect.top - 6)), 3)

    def _draw_siren(self, surface, rect, horizontal, tick):
        siren_phase = tick * 0.15
        red_on  = math.sin(siren_phase) > 0
        blue_on = not red_on

        if horizontal:
            lx = rect.left + 2
            rx = rect.right - 6
            sy = rect.centery
        else:
            lx = rect.centerx - 4
            rx = rect.centerx + 4
            sy = rect.top + 2

        r_col  = C["danger"]    if red_on  else (80, 20, 20)
        b_col  = C["info"]      if blue_on else (20, 30, 80)

        pygame.draw.circle(surface, r_col, (lx if horizontal else lx, sy if horizontal else sy), 3)
        pygame.draw.circle(surface, b_col, (rx if horizontal else rx, sy if horizontal else sy + 6), 3)

        # Glow
        if red_on:
            glow = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow, (220, 50, 50, 60), (15, 15), 14)
            surface.blit(glow, (lx - 15, sy - 15) if horizontal else (lx - 15, sy - 15))

    def __repr__(self):
        return f"Vehicle(id={self.id}, type={self.vtype}, dir={self.direction}, emergency={self.is_emergency})"
