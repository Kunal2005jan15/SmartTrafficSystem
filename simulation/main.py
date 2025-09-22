# main.py
import json

import pygame
import random
from simulation.vehicle import Vehicle
from simulation.traffic_light import TrafficLight
from ai.traffic_predictor import TrafficPredictor
from simulation.config import WIDTH, HEIGHT, STOP_OFFSET, FPS, LANE_WIDTH

pygame.init()

# Window
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Traffic Management System Prototype")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Simulation
vehicles = []

# Traffic Lights
lights = [
    TrafficLight(WIDTH//2 - 40, HEIGHT//2 - 100, "N"),
    TrafficLight(WIDTH//2 + 20, HEIGHT//2 + 100, "S"),
    TrafficLight(WIDTH//2 + 100, HEIGHT//2 - 40, "E"),
    TrafficLight(WIDTH//2 - 100, HEIGHT//2 + 20, "W")
]

# AI predictor
predictor = TrafficPredictor("Main Intersection")
predictor.train()

# Traffic light logic
MIN_GREEN = 10
MAX_RED = 20
CYCLE_BUFFER = 1
last_switch_time = pygame.time.get_ticks()
current_active = "NS"

# Vehicle spawn
def spawn_vehicle():
    direction = random.choice(["N", "S", "E", "W"])
    is_emergency = random.random() < 0.05
    vehicles.append(Vehicle(direction, is_emergency))

def update_traffic_lights():
    global last_switch_time, current_active
    now = pygame.time.get_ticks()
    elapsed = (now - last_switch_time) / 1000

    # Emergency vehicle logic
    emergency_waiting = any(
        v.is_emergency and any(v._is_before_stop_line(l) for l in lights if l.direction == v.direction)
        for v in vehicles
    )

    if emergency_waiting:
        for light in lights:
            light.state = "red"
        for v in vehicles:
            if v.is_emergency:
                for light in lights:
                    if light.direction == v.direction:
                        light.state = "green"
                        current_active = "NS" if light.direction in ["N", "S"] else "EW"
        last_switch_time = now
        return

    # Normal lane switching
    if current_active == "NS":
        green_lights = [l for l in lights if l.direction in ["N", "S"]]
        red_lights = [l for l in lights if l.direction in ["E", "W"]]
    else:
        green_lights = [l for l in lights if l.direction in ["E", "W"]]
        red_lights = [l for l in lights if l.direction in ["N", "S"]]

    total_approaching = sum(
        sum(1 for v in vehicles if v._is_before_stop_line(light)) for light in green_lights
    )
    green_duration = max(MIN_GREEN, min(MAX_RED, total_approaching * 2))

    if elapsed >= green_duration + CYCLE_BUFFER:
        current_active = "EW" if current_active == "NS" else "NS"
        last_switch_time = now
        for light in green_lights:
            light.state = "red"
        for light in red_lights:
            light.state = "green"

def export_simulation_data():
    data = {
        "vehicles": [
            {"x": v.x, "y": v.y, "direction": v.direction, "is_emergency": v.is_emergency}
            for v in vehicles
        ],
        "traffic_lights": [
            {"direction": l.direction, "state": l.state} for l in lights
        ],
        "lane_counts": {
            "N": sum(1 for v in vehicles if v.direction == "N"),
            "S": sum(1 for v in vehicles if v.direction == "S"),
            "E": sum(1 for v in vehicles if v.direction == "E"),
            "W": sum(1 for v in vehicles if v.direction == "W")
        },
        "predicted_density": predictor.history[-1] if predictor.history else None
    }
    with open("simulation/data.json", "w") as f:
        json.dump(data, f)


def draw_window():
    WIN.fill(GRAY)

    # Roads
    pygame.draw.rect(WIN, BLACK, (WIDTH//2 - 100, 0, 60, HEIGHT))  # vertical
    pygame.draw.rect(WIN, BLACK, (0, HEIGHT//2 - 100, WIDTH, 60))  # horizontal

    # Intersection box
    pygame.draw.rect(WIN, (50, 50, 50), (WIDTH//2 - 100, HEIGHT//2 - 100, 200, 200))

    # Traffic lights
    for light in lights:
        light.draw(WIN)

    # Vehicles
    for v in vehicles:
        v.draw(WIN)

    # Legends
    font = pygame.font.SysFont(None, 24)
    WIN.blit(font.render("Blue: Normal Vehicle", True, BLUE), (10, 10))
    WIN.blit(font.render("Yellow: Emergency Vehicle", True, YELLOW), (10, 30))

    pygame.display.update()
    export_simulation_data()

def main_loop():
    clock = pygame.time.Clock()
    run = True
    spawn_timer = 0

    # Initialize lights
    for light in lights:
        light.state = "green" if light.direction in ["N", "S"] else "red"

    while run:
        clock.tick(FPS)
        spawn_timer += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        if spawn_timer >= FPS:
            spawn_vehicle()
            spawn_timer = 0

        update_traffic_lights()

        for v in vehicles:
            v.move(lights)

        draw_window()

    pygame.quit()



if __name__ == "__main__":
    main_loop()
