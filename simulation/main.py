import pygame, random
from vehicle import Vehicle
from traffic_light import TrafficLight

pygame.init()
WIDTH, HEIGHT = 800, 600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Traffic Management Simulation")
clock = pygame.time.Clock()

# Traffic light at intersection center
traffic_light = TrafficLight(WIDTH//2, HEIGHT//2)

# Vehicle list
vehicles = []

def spawn_vehicle():
    x = random.randint(300, 500)
    y = HEIGHT
    is_emergency = random.random() < 0.05  # 5% chance emergency
    color = (255,0,0) if is_emergency else (0,0,255)
    speed = 4 if is_emergency else 2
    vehicles.append(Vehicle(x, y, color, speed, is_emergency))

# Main loop
running = True
frame_count = 0
while running:
    win.fill((50,50,50))  # road background

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Spawn vehicles every 30 frames
    if frame_count % 30 == 0:
        spawn_vehicle()

    # Count vehicles approaching light
    vehicle_count = sum(1 for v in vehicles if v.y < HEIGHT//2 + 100)

    traffic_light.update(vehicle_count)
    traffic_light.draw(win)

    for v in vehicles:
        v.move()
        v.draw(win)

    pygame.display.update()
    clock.tick(60)
    frame_count += 1

pygame.quit()
