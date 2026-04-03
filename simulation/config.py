"""
Smart Traffic Management System — Configuration
All constants, layout params, timing rules, and color palette live here.
"""

# ── Window & Display ──────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1400
WINDOW_HEIGHT = 860
FPS           = 60
WINDOW_TITLE  = "Smart Traffic Management System"

# ── Color Palette (Dark industrial theme) ─────────────────────────────────────
C = {
    # Backgrounds
    "bg":           (10,  12,  18),
    "panel":        (16,  20,  30),
    "panel_light":  (22,  28,  42),
    "card":         (20,  25,  38),
    "card_hover":   (28,  34,  50),

    # Road
    "road":         (30,  33,  40),
    "road_line":    (60,  65,  75),
    "road_stripe":  (200, 180, 80),
    "sidewalk":     (45,  48,  55),
    "grass":        (20,  38,  22),
    "building":     (25,  30,  42),

    # Traffic lights
    "red":          (220, 50,  50),
    "amber":        (230, 160, 30),
    "green":        (50,  210, 100),
    "light_off":    (40,  40,  50),
    "light_housing":(55,  60,  70),

    # Vehicles
    "car_normal":   (70,  130, 200),
    "car_2":        (200, 130, 70),
    "car_3":        (130, 200, 70),
    "car_4":        (180, 80,  180),
    "truck":        (160, 140, 100),
    "bus":          (200, 170, 40),
    "emergency":    (220, 30,  30),
    "emergency_2":  (255, 255, 255),

    # UI / Text
    "text":         (220, 225, 235),
    "text_dim":     (130, 135, 150),
    "text_bright":  (255, 255, 255),
    "accent":       (0,   200, 180),
    "accent_dim":   (0,   120, 110),
    "warn":         (230, 160, 30),
    "danger":       (220, 60,  60),
    "success":      (50,  210, 100),
    "info":         (80,  160, 230),

    # Charts
    "chart_bg":     (14,  18,  28),
    "chart_grid":   (35,  40,  55),
    "chart_line":   (0,   200, 180),
    "chart_fill":   (0,   200, 180, 40),
    "chart_pred":   (230, 160, 30),
    "chart_emerg":  (220, 60,  60),
    "chart_ns":     (80,  160, 230),
    "chart_ew":     (50,  210, 100),
}

# ── Road / Intersection Geometry ──────────────────────────────────────────────
ROAD_W      = 90   # road corridor width (px)
LANE_W      = 30   # single lane width (px)
NUM_LANES   = 3    # lanes per direction

# Centre of the simulation canvas
SIM_X = 460        # sim panel occupies x: 0..920
SIM_Y = 430        # centre y of sim

CX = SIM_X // 2   # intersection centre x within sim canvas
CY = SIM_Y // 2   # intersection centre y within sim canvas

# Spawn points: (x, y, direction_name, heading_dx, heading_dy)
SPAWN_NORTH = (CX,              60,           "N→S", 0,   1)
SPAWN_SOUTH = (CX,              SIM_Y - 60,   "S→N", 0,  -1)
SPAWN_EAST  = (SIM_X - 60,     CY,            "E→W", -1,  0)
SPAWN_WEST  = (60,              CY,            "W→E",  1,  0)
SPAWN_POINTS = [SPAWN_NORTH, SPAWN_SOUTH, SPAWN_EAST, SPAWN_WEST]

# Stop lines (distance from intersection centre where vehicles stop)
STOP_DIST = ROAD_W // 2 + 8

# ── Vehicle Parameters ────────────────────────────────────────────────────────
VEHICLE_TYPES = {
    "car":       {"w": 22, "h": 14, "speed": 2.2, "color": "car_normal", "weight": 70},
    "truck":     {"w": 32, "h": 16, "speed": 1.6, "color": "truck",      "weight": 15},
    "bus":       {"w": 36, "h": 16, "speed": 1.5, "color": "bus",        "weight": 10},
    "emergency": {"w": 26, "h": 14, "speed": 3.5, "color": "emergency",  "weight": 5},
}

VEHICLE_COLORS_EXTRA = [
    C["car_2"], C["car_3"], C["car_4"]
]

SPAWN_INTERVAL_BASE  = 90    # frames between spawns (base)
SPAWN_INTERVAL_RUSH  = 40    # frames during rush hour
EMERGENCY_PROB       = 0.02  # probability any new vehicle is emergency

# ── Traffic Light Timing ──────────────────────────────────────────────────────
MIN_GREEN    = 10    # seconds
MAX_GREEN    = 60    # seconds
DEFAULT_GREEN = 25   # seconds
YELLOW_TIME  = 3     # seconds
ALL_RED_TIME  = 1    # seconds (safety clearance)

# ── ML Predictor ──────────────────────────────────────────────────────────────
HISTORY_LEN  = 120   # ticks of history to feed ML model
PRED_HORIZON = 30    # ticks ahead to predict

# ── Dashboard Panel Layout ────────────────────────────────────────────────────
SIM_PANEL_W  = 920   # left: simulation
DASH_PANEL_X = 920   # right: dashboard starts here
DASH_PANEL_W = 480   # dashboard width

# Chart rectangles (x, y, w, h) — all relative to full window
CHART_H      = 110
CHART_MARGIN = 14
CHART_W      = DASH_PANEL_W - CHART_MARGIN * 2

CHART_DENSITY_RECT  = (DASH_PANEL_X + CHART_MARGIN, 170,  CHART_W, CHART_H)
CHART_TIMING_RECT   = (DASH_PANEL_X + CHART_MARGIN, 310,  CHART_W, CHART_H)
CHART_WAIT_RECT     = (DASH_PANEL_X + CHART_MARGIN, 450,  CHART_W, CHART_H)

# ── Simulation Modes ──────────────────────────────────────────────────────────
MODE_NORMAL     = "normal"
MODE_RUSH_HOUR  = "rush_hour"
MODE_NIGHT      = "night"
MODE_EMERGENCY  = "emergency_active"

RUSH_HOUR_DENSITY_MULT = 2.5
NIGHT_DENSITY_MULT     = 0.3
