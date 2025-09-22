import pygame

class Vehicle:
    def __init__(self, x, y, color=(0, 0, 255), speed=2, is_emergency=False):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.width = 20
        self.height = 40
        self.is_emergency = is_emergency

    def move(self):
        self.y -= self.speed if not self.is_emergency else self.speed*2

    def draw(self, win):
        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height))
