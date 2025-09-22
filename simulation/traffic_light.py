import pygame

class TrafficLight:
    def __init__(self, x, y, green_time=120, red_time=120):
        self.x = x
        self.y = y
        self.green_time = green_time
        self.red_time = red_time
        self.state = "RED"
        self.timer = 0

    def update(self, vehicle_count=0):
        # Adaptive logic: more vehicles → longer green
        if self.state == "GREEN":
            self.timer += 1
            if self.timer > self.green_time + vehicle_count*2:
                self.state = "RED"
                self.timer = 0
        else:
            self.timer += 1
            if self.timer > self.red_time:
                self.state = "GREEN"
                self.timer = 0

    def draw(self, win):
        color = (0,255,0) if self.state=="GREEN" else (255,0,0)
        pygame.draw.circle(win, color, (self.x, self.y), 20)
