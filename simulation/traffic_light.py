# traffic_light.py
import pygame

LIGHT_RADIUS = 10

class TrafficLight:
    """
    Traffic light at a given x,y; direction is the direction the light controls.
    For example, a light with direction "N" controls vehicles coming from North (top).
    """
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction  # "N","S","E","W"
        self.state = "red"

    def draw(self, screen):
        col = (0, 200, 0) if self.state == "green" else (255, 0, 0)
        if self.state == "yellow":
            col = (255, 200, 0)

        # draw the light itself
        pygame.draw.circle(screen, col, (int(self.x), int(self.y)), LIGHT_RADIUS)

        # --- NEW: show countdown above active light ---
        if hasattr(self, "remaining_time") and self.remaining_time > 0:
            font = pygame.font.SysFont("Arial", 16, bold=True)
            txt = font.render(str(self.remaining_time), True, (255, 255, 255))
            # position slightly above the light
            screen.blit(txt, (self.x - 8, self.y - 25))
        pygame.draw.circle(screen, col, (int(self.x), int(self.y)), LIGHT_RADIUS)
