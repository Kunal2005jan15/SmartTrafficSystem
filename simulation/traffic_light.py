# traffic_light.py
import pygame

class TrafficLight:
    WIDTH = 20
    HEIGHT = 60

    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.state = "red"  # initial state

    def draw(self, screen):
        color = (255, 0, 0) if self.state == "red" else (0, 255, 0)
        pygame.draw.rect(screen, color, (self.x, self.y, TrafficLight.WIDTH, TrafficLight.HEIGHT))
