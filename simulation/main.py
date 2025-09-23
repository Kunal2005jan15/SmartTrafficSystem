# main.py
import pygame
import random
import time
import json
import os

from simulation.vehicle import Vehicle
from simulation.traffic_light import TrafficLight
from ai.traffic_predictor import TrafficPredictor
from simulation.config import WIDTH, HEIGHT, FPS
from simulation.dashboard import Dashboard

GREEN_DURATION = 6
YELLOW_DURATION = 2

def create_lights():
    cx, cy = WIDTH // 2, HEIGHT // 2
    offset = 22
    lights = [
        TrafficLight(cx + 20, cy - 15, "N"),
        TrafficLight(cx - 20, cy + 15, "S"),
        TrafficLight(cx - offset, cy - 15, "W"),
        TrafficLight(cx + offset, cy + 15, "E"),
    ]
    for L in lights:
        L.state = "green" if L.direction in ("N", "S") else "red"
    return lights

def set_light_states(lights, active_group):
    for L in lights:
        if L.direction in active_group:
            L.state = "green"
        else:
            L.state = "red"

def main_loop():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Smart Traffic Management System Prototype - Dashboard")
    clock = pygame.time.Clock()

    vehicles = []
    lights = create_lights()
    predictor = TrafficPredictor(name="Intersection-1")
    predictor.train()
    dashboard = Dashboard(WIDTH, HEIGHT)

    running = True
    spawn_cooldown = 0.9
    last_spawn = time.time()
    active_group = ("N", "S")
    group_start = time.time()
    phase = "green"

    # optional: read detection json if available (integrate later)
    last_counts_read = 0

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    d = random.choice(["N", "S", "E", "W"])
                    vehicles.append(Vehicle(d, is_emergency=True))

        # spawn vehicles
        now = time.time()
        if now - last_spawn > spawn_cooldown:
            d = random.choice(["N", "S", "E", "W"])
            vehicles.append(Vehicle(d))
            last_spawn = now

        # read latest_counts.json if exists (integration demo)
        try:
            if now - last_counts_read > 1.0 and os.path.exists("latest_counts.json"):
                with open("latest_counts.json", "r") as jf:
                    data = json.load(jf)
                # optional: use data['total'] to adjust behavior (demo only)
                # e.g., if heavy traffic, increase green duration (this is simplistic)
                if isinstance(data.get("total"), int) and data["total"] > 12:
                    # cap green duration at 12
                    global GREEN_DURATION
                    GREEN_DURATION = min(12, max(4, GREEN_DURATION))
                last_counts_read = now
        except Exception:
            pass

        # --- Adaptive green duration based on vehicle counts ---
        def count_waiting(vehicles, lights, directions):
            """Count vehicles waiting at red/yellow lights in given directions."""
            count = 0
            for v in vehicles:
                if v.direction in directions and not v.has_crossed:
                    # Check if the light for this direction is red/yellow
                    for light in lights:
                        if light.direction == v.direction and light.state in ("red", "yellow"):
                            count += 1
            return count

        # light phase handling
        elapsed = now - group_start

        # --- Remaining time for countdown ---
        if phase == "green":
            remaining = max(0, int(GREEN_DURATION - elapsed))
        elif phase == "yellow":
            remaining = max(0, int(YELLOW_DURATION - elapsed))
        else:
            remaining = 0

        # attach countdown to lights
        for L in lights:
            if L.direction in active_group:
                L.remaining_time = remaining
            else:
                L.remaining_time = 0

        if phase == "green" and elapsed >= GREEN_DURATION:
            phase = "yellow"
            group_start = now
            for L in lights:
                if L.direction in active_group:
                    L.state = "yellow"

        elif phase == "yellow" and elapsed >= YELLOW_DURATION:
            phase = "green"
            group_start = now
            active_group = ("E", "W") if active_group == ("N", "S") else ("N", "S")
    
            # --- Adaptive logic ---
            ns_count = count_waiting(vehicles, lights, ("N", "S"))
            ew_count = count_waiting(vehicles, lights, ("E", "W"))

            # base min/max times
            min_green = 4
            max_green = 12

            if active_group == ("N", "S"):
                GREEN_DURATION = min(max_green, max(min_green, 4 + ns_count // 2))
            else:
                GREEN_DURATION = min(max_green, max(min_green, 4 + ew_count // 2))

            # NEW: save current green duration for dashboard
            predictor.current_green_duration = GREEN_DURATION

            set_light_states(lights, active_group)


        # move vehicles & remove out-of-bounds ones
        for v in list(vehicles):
            v.move(lights)
            if v.x < -200 or v.x > WIDTH + 200 or v.y < -200 or v.y > HEIGHT + 200:
                vehicles.remove(v)

        # predictor occasional update (non-blocking)
        if random.random() < 0.05:
            try:
                predictor.predict_next()
            except Exception:
                pass

        # DRAW
        screen.fill((18, 18, 18))
        # intersection guide
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        road_color = (60, 60, 60)   # asphalt gray
        lane_width = 100            # road width (adjust if needed)

        # Draw main roads (rectangles instead of lines)
        pygame.draw.rect(screen, road_color, (0, center_y - lane_width//2, WIDTH, lane_width))   # horizontal
        pygame.draw.rect(screen, road_color, (center_x - lane_width//2, 0, lane_width, HEIGHT))  # vertical

        # === Lane Dividers (dashed white lines) ===
        dash_color = (200, 200, 200)
        dash_length = 20
        gap = 15

        # Vertical dashed line (center divider)
        for y in range(0, HEIGHT, dash_length + gap):
            pygame.draw.line(screen, dash_color, (center_x, y), (center_x, y + dash_length), 2)

        # Horizontal dashed line (center divider)
        for x in range(0, WIDTH, dash_length + gap):
            pygame.draw.line(screen, dash_color, (x, center_y), (x + dash_length, center_y), 2)

        # === Stop Lines ===
        stopline_color = (255, 255, 255)
        stopline_thickness = 5
        offset = 70   # distance from center to stop line

        # North stop line
        pygame.draw.line(screen, stopline_color,
                         (center_x - lane_width//2, center_y - offset),
                         (center_x + lane_width//2, center_y - offset), stopline_thickness)

        # South stop line 
        pygame.draw.line(screen, stopline_color,
                         (center_x - lane_width//2, center_y + offset),
                         (center_x + lane_width//2, center_y + offset), stopline_thickness)

        # West stop line
        pygame.draw.line(screen, stopline_color,
                         (center_x - offset, center_y - lane_width//2),
                         (center_x - offset, center_y + lane_width//2), stopline_thickness)

        # East stop line
        pygame.draw.line(screen, stopline_color,
                         (center_x + offset, center_y - lane_width//2),
                         (center_x + offset, center_y + lane_width//2), stopline_thickness)
        

        for v in vehicles:
            v.draw(screen)
        for l in lights:
            l.draw(screen)

        dashboard.draw(screen, vehicles, lights, predictor)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main_loop()
