# vehicle.py
import pygame
from simulation.config import WIDTH, HEIGHT, STOP_OFFSET, LANE_WIDTH
import random

class Vehicle:
    WIDTH = 20
    HEIGHT = 40
    SPEED = 2

    def __init__(self, direction, is_emergency=False):
        self.direction = direction
        self.is_emergency = is_emergency
        self.color = (255, 255, 0) if is_emergency else (0, 0, 255)
        self.set_start_pos()

    def set_start_pos(self):
        if self.direction == "N":
            self.x = WIDTH//2 - LANE_WIDTH
            self.y = 0 - Vehicle.HEIGHT
        elif self.direction == "S":
            self.x = WIDTH//2 + LANE_WIDTH
            self.y = HEIGHT
        elif self.direction == "E":
            self.x = 0 - Vehicle.HEIGHT
            self.y = HEIGHT//2 - LANE_WIDTH
        elif self.direction == "W":
            self.x = WIDTH
            self.y = HEIGHT//2 + LANE_WIDTH

    def _is_before_stop_line(self, light):
        if self.direction == "N":
            return self.y + Vehicle.HEIGHT < HEIGHT//2 - STOP_OFFSET
        elif self.direction == "S":
            return self.y > HEIGHT//2 + STOP_OFFSET
        elif self.direction == "E":
            return self.x + Vehicle.HEIGHT < WIDTH//2 - STOP_OFFSET
        elif self.direction == "W":
            return self.x > WIDTH//2 + STOP_OFFSET
        return False

    def move(self, lights):
        # Check the relevant light
        for light in lights:
            if light.direction == self.direction:
                if self.is_emergency:
                    # Emergency vehicles ignore red light
                    pass
                elif self._is_before_stop_line(light) and light.state == "red":
                    return  # stop before stop line

        # Move
        if self.direction == "N":
            self.y += Vehicle.SPEED
        elif self.direction == "S":
            self.y -= Vehicle.SPEED
        elif self.direction == "E":
            self.x += Vehicle.SPEED
        elif self.direction == "W":
            self.x -= Vehicle.SPEED

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, Vehicle.WIDTH, Vehicle.HEIGHT))
