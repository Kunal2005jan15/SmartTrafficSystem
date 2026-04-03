"""
Smart Traffic Management System — Traffic Light Controller
Handles state machine, adaptive green-time calculation, and emergency preemption.

States: GREEN → YELLOW → ALL_RED → (switch phase) → GREEN → ...
Phases:
  Phase 0: N-S green  (E-W red)
  Phase 1: E-W green  (N-S red)
"""

import pygame
import math
from simulation.config import (
    C, FPS, MIN_GREEN, MAX_GREEN, DEFAULT_GREEN,
    YELLOW_TIME, ALL_RED_TIME, CX, CY, ROAD_W
)

STATE_GREEN   = "green"
STATE_YELLOW  = "yellow"
STATE_ALL_RED = "all_red"


class TrafficLight:
    """
    One of four traffic light heads at the intersection.
    Knows its physical position and which phase it is green for.
    """

    def __init__(self, x, y, green_phase: int):
        self.x = x
        self.y = y
        self.green_phase = green_phase   # which controller phase makes this light green
        self.state = STATE_ALL_RED       # current display state
        self.housing_w = 20
        self.housing_h = 56

    def set_state(self, controller_phase: int, controller_state: str):
        """Update display based on the intersection controller's current phase/state."""
        if controller_state == STATE_ALL_RED:
            self.state = STATE_ALL_RED
        elif controller_phase == self.green_phase:
            self.state = controller_state   # GREEN or YELLOW
        else:
            self.state = STATE_ALL_RED      # other direction is active

    def draw(self, surface, tick: int):
        hx = self.x - self.housing_w // 2
        hy = self.y - self.housing_h // 2

        # Housing
        pygame.draw.rect(surface, C["light_housing"],
                         (hx, hy, self.housing_w, self.housing_h), border_radius=4)
        pygame.draw.rect(surface, (30, 33, 40),
                         (hx, hy, self.housing_w, self.housing_h), width=1, border_radius=4)

        positions = [
            (self.x, self.y - 16),   # top    = red
            (self.x, self.y),         # middle = amber
            (self.x, self.y + 16),   # bottom = green
        ]
        off_colors = [
            (80, 20, 20),
            (80, 60, 10),
            (15, 70, 30),
        ]
        on_colors = [
            C["red"],
            C["amber"],
            C["green"],
        ]

        lit = [False, False, False]
        if self.state == STATE_ALL_RED:
            lit[0] = True
        elif self.state == STATE_GREEN:
            lit[2] = True
        elif self.state == STATE_YELLOW:
            lit[1] = True

        # Amber blink at 2 Hz during yellow
        if self.state == STATE_YELLOW:
            blink = (tick // (FPS // 4)) % 2 == 0
            lit[1] = blink

        for i, (lx, ly) in enumerate(positions):
            color = on_colors[i] if lit[i] else off_colors[i]
            pygame.draw.circle(surface, color, (int(lx), int(ly)), 7)
            if lit[i]:
                # Glow effect
                glow = pygame.Surface((36, 36), pygame.SRCALPHA)
                gc = (*on_colors[i], 55)
                pygame.draw.circle(glow, gc, (18, 18), 17)
                surface.blit(glow, (int(lx) - 18, int(ly) - 18))


class IntersectionController:
    """
    Central controller for the 4-way intersection.
    Manages phases, adaptive timing, and emergency preemption.
    """

    def __init__(self):
        self.phase           = 0             # 0 = N-S green, 1 = E-W green
        self.state           = STATE_GREEN
        self.tick            = 0
        self.phase_timer     = 0             # frames elapsed in current state
        self.green_duration  = DEFAULT_GREEN * FPS
        self.yellow_duration = YELLOW_TIME * FPS
        self.all_red_duration = ALL_RED_TIME * FPS

        self.emergency_active     = False
        self.emergency_phase      = None     # which phase clears for emergency
        self.emergency_vehicle_id = None
        self.emergency_countdown  = 0

        # Stats
        self.phase_history   = []            # list of (phase, green_frames)
        self.current_phase_start = 0

        # Place 4 lights around intersection
        offset = ROAD_W // 2 + 14
        self.lights = [
            TrafficLight(CX - offset, CY - offset, 0),   # NW → N-S phase
            TrafficLight(CX + offset, CY + offset, 0),   # SE → N-S phase
            TrafficLight(CX + offset, CY - offset, 1),   # NE → E-W phase
            TrafficLight(CX - offset, CY + offset, 1),   # SW → E-W phase
        ]

    # ── Phase logic ───────────────────────────────────────────────────────────

    def update(self, vehicles: list, ml_pred: dict):
        self.tick += 1
        self.phase_timer += 1

        if self.emergency_active:
            self._handle_emergency_phase()
        else:
            self._normal_cycle(vehicles, ml_pred)

        # Sync light states
        for light in self.lights:
            light.set_state(self.phase, self.state)

    def _normal_cycle(self, vehicles, ml_pred):
        if self.state == STATE_GREEN:
            if self.phase_timer >= self.green_duration:
                self._transition_to_yellow()

        elif self.state == STATE_YELLOW:
            if self.phase_timer >= self.yellow_duration:
                self._transition_to_all_red()

        elif self.state == STATE_ALL_RED:
            if self.phase_timer >= self.all_red_duration:
                self._switch_phase(vehicles, ml_pred)

    def _transition_to_yellow(self):
        self.state = STATE_YELLOW
        self.phase_timer = 0

    def _transition_to_all_red(self):
        self.state = STATE_ALL_RED
        self.phase_timer = 0

    def _switch_phase(self, vehicles, ml_pred):
        self.phase = 1 - self.phase
        self.state = STATE_GREEN
        self.phase_timer = 0

        # Adaptive green time from ML predictor
        self.green_duration = self._compute_adaptive_green(vehicles, ml_pred)

    def _compute_adaptive_green(self, vehicles, ml_pred: dict) -> int:
        """
        Use vehicle queue lengths and ML prediction to set next green duration.
        Longer queue in the incoming direction → more green time.
        """
        queue_ns = sum(1 for v in vehicles if v.active and not v.passed and
                       v.direction in ("N→S", "S→N") and v.stopped)
        queue_ew = sum(1 for v in vehicles if v.active and not v.passed and
                       v.direction in ("E→W", "W→E") and v.stopped)

        # Predicted density boost
        pred_ns = ml_pred.get("predicted_ns", 5.0)
        pred_ew = ml_pred.get("predicted_ew", 5.0)

        if self.phase == 0:     # about to go N-S green
            demand = queue_ns + pred_ns * 0.4
        else:                   # about to go E-W green
            demand = queue_ew + pred_ew * 0.4

        # Scale between MIN and MAX
        ratio   = min(demand / 20.0, 1.0)
        seconds = MIN_GREEN + (MAX_GREEN - MIN_GREEN) * ratio
        return int(seconds * FPS)

    # ── Emergency preemption ──────────────────────────────────────────────────

    def trigger_emergency(self, vehicle_id: int, vehicle_direction: str):
        """
        Called when an emergency vehicle is detected approaching.
        Grants green to the emergency vehicle's direction ASAP.
        """
        # Determine which phase gives right-of-way to this direction
        if vehicle_direction in ("N→S", "S→N"):
            needed_phase = 0
        else:
            needed_phase = 1

        self.emergency_active      = True
        self.emergency_phase       = needed_phase
        self.emergency_vehicle_id  = vehicle_id
        self.emergency_countdown   = 6 * FPS   # hold emergency green for 6s

        # Immediately start yellow on current green if it conflicts
        if self.phase != needed_phase and self.state == STATE_GREEN:
            self.state       = STATE_YELLOW
            self.phase_timer = 0

    def clear_emergency(self):
        self.emergency_active      = False
        self.emergency_phase       = None
        self.emergency_vehicle_id  = None
        self.emergency_countdown   = 0

    def _handle_emergency_phase(self):
        needed = self.emergency_phase

        if self.state == STATE_YELLOW:
            if self.phase_timer >= self.yellow_duration:
                self._transition_to_all_red()

        elif self.state == STATE_ALL_RED:
            if self.phase_timer >= self.all_red_duration:
                self.phase       = needed
                self.state       = STATE_GREEN
                self.phase_timer = 0
                self.green_duration = self.emergency_countdown

        elif self.state == STATE_GREEN:
            if self.phase == needed:
                self.emergency_countdown -= 1
                if self.emergency_countdown <= 0:
                    self.clear_emergency()
                    self._transition_to_yellow()
            else:
                # Wrong phase active → force yellow immediately
                self._transition_to_yellow()

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_green_for(self, direction: str) -> bool:
        if self.state != STATE_GREEN:
            return False
        if direction in ("N→S", "S→N"):
            return self.phase == 0
        return self.phase == 1

    def seconds_remaining(self) -> float:
        if self.state == STATE_GREEN:
            remaining = self.green_duration - self.phase_timer
        elif self.state == STATE_YELLOW:
            remaining = self.yellow_duration - self.phase_timer
        else:
            remaining = self.all_red_duration - self.phase_timer
        return max(0.0, remaining / FPS)

    def green_fraction(self) -> float:
        """0..1 fraction of current green time elapsed."""
        if self.state != STATE_GREEN:
            return 0.0
        return min(self.phase_timer / max(self.green_duration, 1), 1.0)

    def draw(self, surface, tick: int):
        for light in self.lights:
            light.draw(surface, tick)

        # Phase label near each light cluster
        font = pygame.font.SysFont("monospace", 10)
        for light in self.lights:
            label = "N-S" if light.green_phase == 0 else "E-W"
            surf  = font.render(label, True, C["text_dim"])
            surface.blit(surf, (light.x - 10, light.y + 34))
