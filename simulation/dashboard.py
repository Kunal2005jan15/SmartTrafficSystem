"""
Smart Traffic Management System — Dashboard Renderer

Renders the right-side professional dashboard panel with:
  • KPI summary cards (throughput, avg wait, active vehicles, emergency events)
  • Real-time line charts: N-S density, E-W density, ML prediction, wait time
  • Traffic light phase bar + adaptive timer
  • Mode control buttons
  • Emergency trigger button
  • System status / alerts
"""

import pygame
import math
from simulation.config import (
    C, FPS, WINDOW_WIDTH, WINDOW_HEIGHT, DASH_PANEL_X, DASH_PANEL_W,
    CHART_MARGIN, CHART_H, CHART_DENSITY_RECT, CHART_TIMING_RECT, CHART_WAIT_RECT
)


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


class Button:
    def __init__(self, rect, label, color, label_color=None):
        self.rect        = pygame.Rect(rect)
        self.label       = label
        self.color       = color
        self.label_color = label_color or C["text_bright"]
        self.hover       = False
        self.active      = False

    def draw(self, surface, font):
        c = _lerp_color(self.color, (255, 255, 255), 0.15) if self.hover else self.color
        if self.active:
            c = _lerp_color(c, (255, 255, 255), 0.25)
        pygame.draw.rect(surface, c, self.rect, border_radius=6)
        pygame.draw.rect(surface, (255, 255, 255, 40), self.rect, width=1, border_radius=6)
        txt = font.render(self.label, True, self.label_color)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class Dashboard:
    """All dashboard drawing and control logic."""

    CHART_POINTS = 180    # how many data points to display on charts

    def __init__(self, intersection):
        self.intersection = intersection
        self.font_title   = None
        self.font_body    = None
        self.font_small   = None
        self.font_mono    = None
        self.font_large   = None

        # Chart histories
        self.chart_ns:       list[float] = []
        self.chart_ew:       list[float] = []
        self.chart_pred_ns:  list[float] = []
        self.chart_pred_ew:  list[float] = []
        self.chart_wait:     list[float] = []
        self.chart_green:    list[float] = []   # green fraction over time

        # Buttons
        px = DASH_PANEL_X + 14
        bw, bh = (DASH_PANEL_W - 42) // 3, 32
        self.btn_normal    = Button((px,            620, bw, bh), "Normal",     (30, 80,  60))
        self.btn_rush      = Button((px + bw + 7,   620, bw, bh), "Rush Hour", (120, 70, 20))
        self.btn_night     = Button((px + (bw+7)*2, 620, bw, bh), "Night",     (30, 40,  90))

        self.btn_emergency = Button(
            (DASH_PANEL_X + 14, 670, DASH_PANEL_W - 28, 36),
            "🚨  Trigger Emergency Vehicle",
            (140, 20, 20),
        )
        self.btn_pause     = Button(
            (DASH_PANEL_X + 14, 718, DASH_PANEL_W - 28, 36),
            "⏸  Pause Simulation",
            (40, 50, 70),
        )

        self.btn_normal.active = True

    def init_fonts(self):
        pygame.font.init()
        self.font_title = pygame.font.SysFont("segoeui",   15, bold=True)
        self.font_body  = pygame.font.SysFont("segoeui",   13)
        self.font_small = pygame.font.SysFont("segoeui",   11)
        self.font_mono  = pygame.font.SysFont("monospace", 11)
        self.font_large = pygame.font.SysFont("segoeui",   26, bold=True)

    # ── Update per tick ───────────────────────────────────────────────────────

    def update(self, tick: int):
        dens   = self.intersection.current_density()
        pred   = self.intersection.predictor.predict(tick)
        ctrl   = self.intersection.controller

        self.chart_ns.append(dens["ns"])
        self.chart_ew.append(dens["ew"])
        self.chart_pred_ns.append(pred["predicted_ns"])
        self.chart_pred_ew.append(pred["predicted_ew"])
        self.chart_wait.append(self.intersection.avg_wait())
        self.chart_green.append(ctrl.green_fraction() * 100)

        for lst in [self.chart_ns, self.chart_ew, self.chart_pred_ns,
                    self.chart_pred_ew, self.chart_wait, self.chart_green]:
            if len(lst) > self.CHART_POINTS:
                lst.pop(0)

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, tick: int):
        if not self.font_title:
            self.init_fonts()

        # Panel background
        panel = pygame.Rect(DASH_PANEL_X, 0, DASH_PANEL_W, WINDOW_HEIGHT)
        pygame.draw.rect(surface, C["panel"], panel)
        pygame.draw.line(surface, C["accent_dim"], (DASH_PANEL_X, 0), (DASH_PANEL_X, WINDOW_HEIGHT), 1)

        self._draw_header(surface, tick)
        self._draw_kpi_cards(surface, tick)
        self._draw_density_chart(surface)
        self._draw_phase_bar(surface, tick)
        self._draw_wait_chart(surface)
        self._draw_ml_status(surface)
        self._draw_mode_buttons(surface)
        self._draw_emergency_btn(surface)
        self._draw_pause_btn(surface)
        self._draw_legend(surface)

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, surface, tick):
        y = 14
        # Accent bar
        pygame.draw.rect(surface, C["accent"],
                         (DASH_PANEL_X, y, DASH_PANEL_W, 3))
        y += 10

        # Title
        title = self.font_title.render("SMART TRAFFIC MANAGEMENT", True, C["text_bright"])
        surface.blit(title, (DASH_PANEL_X + 14, y + 6))

        # Tick counter
        secs  = tick // FPS
        m, s  = divmod(secs, 60)
        tstr  = self.font_mono.render(f"SIM {m:02d}:{s:02d}", True, C["text_dim"])
        surface.blit(tstr, (DASH_PANEL_X + DASH_PANEL_W - tstr.get_width() - 14, y + 6))

        # Mode badge
        mode_labels = {
            "normal":    ("● NORMAL",    C["accent"]),
            "rush_hour": ("● RUSH HOUR", C["warn"]),
            "night":     ("● NIGHT",     C["info"]),
        }
        ml, mc = mode_labels.get(self.intersection.mode, ("● UNKNOWN", C["text_dim"]))
        mode_surf = self.font_small.render(ml, True, mc)
        surface.blit(mode_surf, (DASH_PANEL_X + 14, y + 24))

        # Emergency indicator
        if self.intersection.controller.emergency_active:
            emerg_surf = self.font_small.render("🚨 EMERGENCY PREEMPTION ACTIVE", True, C["danger"])
            ex = DASH_PANEL_X + DASH_PANEL_W // 2 - emerg_surf.get_width() // 2
            surface.blit(emerg_surf, (ex, y + 24))

        # Separator
        pygame.draw.line(surface, C["chart_grid"],
                         (DASH_PANEL_X + 14, y + 40), (DASH_PANEL_X + DASH_PANEL_W - 14, y + 40), 1)

    # ── KPI Cards ─────────────────────────────────────────────────────────────

    def _draw_kpi_cards(self, surface, tick):
        dens   = self.intersection.current_density()
        queues = self.intersection.queue_lengths()
        ctrl   = self.intersection.controller

        kpis = [
            ("Active", f"{dens['total']:3d}",       "vehicles",       C["accent"]),
            ("N-S",    f"{dens['ns']:3d}",           "vehicles",       C["chart_ns"]),
            ("E-W",    f"{dens['ew']:3d}",           "vehicles",       C["chart_ew"]),
            ("Queue",  f"{queues['ns']+queues['ew']:3d}", "waiting",   C["warn"]),
            ("Wait",   f"{self.intersection.avg_wait():4.1f}",  "s avg", C["chart_pred"]),
            ("Total",  f"{self.intersection.total_vehicles_passed:4d}", "passed", C["success"]),
        ]

        x0   = DASH_PANEL_X + 14
        y0   = 70
        cw   = (DASH_PANEL_W - 28 - 10) // 3   # 3 per row
        ch   = 48
        gap  = 5

        for i, (label, val, unit, col) in enumerate(kpis):
            col_i = i % 3
            row_i = i // 3
            cx    = x0 + col_i * (cw + gap)
            cy    = y0 + row_i * (ch + gap)

            # Card background
            card  = pygame.Rect(cx, cy, cw, ch)
            pygame.draw.rect(surface, C["card"], card, border_radius=5)
            pygame.draw.rect(surface, col, card, width=1, border_radius=5)

            # Value
            val_surf  = self.font_large.render(val, True, col)
            surface.blit(val_surf, (cx + 6, cy + 4))

            # Label + unit
            lbl_surf  = self.font_small.render(label, True, C["text_dim"])
            unit_surf = self.font_small.render(unit,  True, C["text_dim"])
            surface.blit(lbl_surf,  (cx + 6, cy + ch - 22))
            surface.blit(unit_surf, (cx + cw - unit_surf.get_width() - 6, cy + ch - 22))

    # ── Density chart ─────────────────────────────────────────────────────────

    def _draw_density_chart(self, surface):
        rx, ry, rw, rh = CHART_DENSITY_RECT
        self._draw_chart_background(surface, rx, ry, rw, rh, "Vehicle Density")

        # N-S actual
        self._draw_sparkline(surface, self.chart_ns,      rx, ry, rw, rh, C["chart_ns"],   1.5)
        # E-W actual
        self._draw_sparkline(surface, self.chart_ew,      rx, ry, rw, rh, C["chart_ew"],   1.5)
        # N-S predicted (dashed)
        self._draw_sparkline(surface, self.chart_pred_ns, rx, ry, rw, rh, C["chart_pred"], 1.0, dashed=True)
        # E-W predicted (dashed)
        self._draw_sparkline(surface, self.chart_pred_ew, rx, ry, rw, rh, C["chart_ns"],   1.0, dashed=True)

    # ── Phase bar ─────────────────────────────────────────────────────────────

    def _draw_phase_bar(self, surface, tick):
        rx, ry, rw, rh = CHART_TIMING_RECT
        ctrl = self.intersection.controller

        # Background
        self._draw_chart_background(surface, rx, ry, rw, rh, "Signal Phase & Timing")

        # Phase indicator
        bar_h  = 22
        bar_y  = ry + 24
        bar_x  = rx + 4
        bar_w  = rw - 8

        # N-S phase occupies left fraction based on green duration ratio
        total   = ctrl.green_duration + ctrl.yellow_duration + ctrl.all_red_duration
        ns_frac = ctrl.green_duration / max(total, 1) if ctrl.phase == 0 else 0.0
        ew_frac = ctrl.green_duration / max(total, 1) if ctrl.phase == 1 else 0.0

        # Draw full bar background
        pygame.draw.rect(surface, C["chart_grid"], (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # Active direction fill
        phase_lbl = "N-S" if ctrl.phase == 0 else "E-W"
        phase_col = C["chart_ns"] if ctrl.phase == 0 else C["chart_ew"]

        # Progress fill based on time elapsed in current green
        frac   = ctrl.green_fraction()
        fill_w = int(bar_w * frac)

        if ctrl.state == "green":
            pygame.draw.rect(surface, phase_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        elif ctrl.state == "yellow":
            pulse = (math.sin(tick * 0.3) + 1) / 2
            col   = _lerp_color(C["amber"], C["warn"], pulse)
            pygame.draw.rect(surface, col, (bar_x, bar_y, bar_w // 2, bar_h), border_radius=4)
        else:
            pygame.draw.rect(surface, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # State label
        state_map = {"green": "● GREEN", "yellow": "● YELLOW", "all_red": "● ALL RED"}
        state_col = {"green": C["success"], "yellow": C["warn"], "all_red": C["danger"]}
        sl  = self.font_mono.render(state_map.get(ctrl.state, ctrl.state), True,
                                     state_col.get(ctrl.state, C["text"]))
        surface.blit(sl, (bar_x + 6, bar_y + 5))

        # Seconds remaining
        secs_surf = self.font_mono.render(f"{ctrl.seconds_remaining():.1f}s", True, C["text_bright"])
        surface.blit(secs_surf, (bar_x + bar_w - secs_surf.get_width() - 6, bar_y + 5))

        # Phase label row
        y2 = bar_y + bar_h + 8
        pl = self.font_small.render(f"Active phase: {phase_lbl}", True, phase_col)
        surface.blit(pl, (rx + 4, y2))

        adaptive_sec = ctrl.green_duration / FPS
        al = self.font_small.render(f"Adaptive green: {adaptive_sec:.1f}s", True, C["text_dim"])
        surface.blit(al, (rx + 4, y2 + 14))

        emerg_str = "YES — preempting" if ctrl.emergency_active else "No"
        emerg_col = C["danger"] if ctrl.emergency_active else C["text_dim"]
        el = self.font_small.render(f"Emergency override: {emerg_str}", True, emerg_col)
        surface.blit(el, (rx + 4, y2 + 28))

        # Mini green-fraction sparkline
        self._draw_sparkline(surface, self.chart_green, rx, y2 + 44, rw, 26, C["chart_pred"], 1.0)

    # ── Wait time chart ───────────────────────────────────────────────────────

    def _draw_wait_chart(self, surface):
        rx, ry, rw, rh = CHART_WAIT_RECT
        self._draw_chart_background(surface, rx, ry, rw, rh, "Avg Wait Time (seconds)")
        self._draw_sparkline(surface, self.chart_wait, rx, ry, rw, rh, C["chart_pred"], 1.5)

        if self.chart_wait:
            latest = self.chart_wait[-1]
            col    = C["success"] if latest < 5 else (C["warn"] if latest < 15 else C["danger"])
            val_s  = self.font_body.render(f"{latest:.2f}s", True, col)
            surface.blit(val_s, (rx + rw - val_s.get_width() - 6, ry + 4))

    # ── ML Status ─────────────────────────────────────────────────────────────

    def _draw_ml_status(self, surface):
        x  = DASH_PANEL_X + 14
        y  = 576
        pred = self.intersection.predictor

        label = self.font_small.render("ML MODEL", True, C["accent"])
        surface.blit(label, (x, y))

        info  = pred.get_model_info()
        i_surf = self.font_mono.render(info, True, C["text_dim"])
        surface.blit(i_surf, (x + 80, y))

        # Confidence bar
        conf   = self.intersection.predictor.last_pred.get("confidence", 0.0)
        bar_w  = DASH_PANEL_W - 28
        bar_h  = 6
        pygame.draw.rect(surface, C["chart_grid"], (x, y + 14, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(surface, C["accent"],     (x, y + 14, int(bar_w * conf), bar_h), border_radius=3)
        cl = self.font_small.render(f"Confidence {conf*100:.0f}%", True, C["text_dim"])
        surface.blit(cl, (x, y + 24))

    # ── Mode buttons ──────────────────────────────────────────────────────────

    def _draw_mode_buttons(self, surface):
        font = self.font_body
        lbl  = self.font_small.render("TRAFFIC MODE", True, C["text_dim"])
        surface.blit(lbl, (DASH_PANEL_X + 14, 606))
        self.btn_normal.draw(surface, font)
        self.btn_rush.draw(surface, font)
        self.btn_night.draw(surface, font)

    def _draw_emergency_btn(self, surface):
        self.btn_emergency.draw(surface, self.font_body)

    def _draw_pause_btn(self, surface):
        label = "▶  Resume Simulation" if self.intersection.paused else "⏸  Pause Simulation"
        self.btn_pause.label = label
        self.btn_pause.draw(surface, self.font_body)

    # ── Legend ────────────────────────────────────────────────────────────────

    def _draw_legend(self, surface):
        items = [
            (C["chart_ns"],   "N-S actual"),
            (C["chart_ew"],   "E-W actual"),
            (C["chart_pred"], "ML prediction"),
        ]
        x = DASH_PANEL_X + 14
        y = WINDOW_HEIGHT - 38
        for col, lbl in items:
            pygame.draw.line(surface, col, (x, y + 6), (x + 18, y + 6), 2)
            ls = self.font_small.render(lbl, True, C["text_dim"])
            surface.blit(ls, (x + 22, y))
            x += ls.get_width() + 40

    # ── Chart helpers ─────────────────────────────────────────────────────────

    def _draw_chart_background(self, surface, rx, ry, rw, rh, title: str):
        pygame.draw.rect(surface, C["chart_bg"],  (rx, ry, rw, rh), border_radius=6)
        pygame.draw.rect(surface, C["chart_grid"], (rx, ry, rw, rh), width=1, border_radius=6)

        # Horizontal grid lines
        for i in range(1, 4):
            ly = ry + (rh * i) // 4
            pygame.draw.line(surface, C["chart_grid"], (rx + 2, ly), (rx + rw - 2, ly), 1)

        # Title
        t = self.font_small.render(title, True, C["text_dim"])
        surface.blit(t, (rx + 6, ry + 5))

    def _draw_sparkline(self, surface, data: list, rx, ry, rw, rh,
                         color, width=1.5, dashed=False):
        if len(data) < 2:
            return

        pad_t, pad_b, pad_l, pad_r = 20, 8, 6, 6
        inner_w = rw - pad_l - pad_r
        inner_h = rh - pad_t - pad_b

        max_val = max(max(data), 1)
        min_val = 0

        points = []
        for i, val in enumerate(data):
            x = rx + pad_l + int(i / max(len(data) - 1, 1) * inner_w)
            y = ry + pad_t + inner_h - int((val - min_val) / (max_val - min_val) * inner_h)
            y = max(ry + pad_t, min(ry + rh - pad_b, y))
            points.append((x, y))

        if dashed:
            for i in range(0, len(points) - 1, 3):
                if i + 1 < len(points):
                    pygame.draw.line(surface, color, points[i], points[i + 1], max(1, int(width)))
        else:
            pygame.draw.lines(surface, color, False, points, max(1, int(width)))

    # ── Event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        """Process button clicks. Returns action string or None."""
        if self.btn_normal.handle_event(event):
            self._set_mode_active("normal")
            return "mode:normal"
        if self.btn_rush.handle_event(event):
            self._set_mode_active("rush_hour")
            return "mode:rush_hour"
        if self.btn_night.handle_event(event):
            self._set_mode_active("night")
            return "mode:night"
        if self.btn_emergency.handle_event(event):
            return "emergency"
        if self.btn_pause.handle_event(event):
            return "pause"

        # Hover
        for btn in [self.btn_normal, self.btn_rush, self.btn_night,
                    self.btn_emergency, self.btn_pause]:
            btn.handle_event(event)

        return None

    def _set_mode_active(self, mode: str):
        self.btn_normal.active = (mode == "normal")
        self.btn_rush.active   = (mode == "rush_hour")
        self.btn_night.active  = (mode == "night")
