# vehicle.py
import pygame
from simulation.config import WIDTH, HEIGHT, STOP_OFFSET

VEHICLE_WIDTH = 20
VEHICLE_HEIGHT = 40
BASE_SPEED = 2.5
MIN_SPEED = 0.8


class Vehicle:
    """
    Vehicle logic:
    - Stops at red/yellow before the stop line.
    - Once it crosses the intersection center, it never stops again (like real traffic).
    - Emergency vehicles always pass.
    """
    def __init__(self, direction, is_emergency=False):
        self.direction = direction
        self.is_emergency = is_emergency
        self.color = (255, 200, 0) if is_emergency else (0, 120, 255)
        self.x, self.y = self._start_pos_for_direction(direction)
        self.speed = BASE_SPEED
        self.has_crossed = False  # flag set after passing intersection center

    def _start_pos_for_direction(self, d):
        if d == "N":
            return (WIDTH // 2 - 10, -60)         
        if d == "S":
            return (WIDTH // 2 + 10, HEIGHT + 60) 
        if d == "E":
            return (WIDTH + 60, HEIGHT // 2 - 10) 
        if d == "W":
            return (-60, HEIGHT // 2 + 10)        
        return (WIDTH // 2, HEIGHT // 2)

    def _passed_intersection(self):
        """Check if vehicle has fully entered/crossed the intersection center."""
        if self.direction == "N" and self.y > HEIGHT // 2:
            return True
        if self.direction == "S" and self.y < HEIGHT // 2:
            return True
        if self.direction == "E" and self.x < WIDTH // 2:
            return True
        if self.direction == "W" and self.x > WIDTH // 2:
            return True
        return False

    def _is_before_stop_line(self, light):
        """Check if vehicle is still before its stop line (only matters if light is red/yellow)."""
        if self.direction == "N" and self.y + VEHICLE_HEIGHT >= HEIGHT // 2 - STOP_OFFSET:
            return True
        if self.direction == "S" and self.y <= HEIGHT // 2 + STOP_OFFSET:
            return True
        if self.direction == "E" and self.x <= WIDTH // 2 + STOP_OFFSET:
            return True
        if self.direction == "W" and self.x + VEHICLE_WIDTH >= WIDTH // 2 - STOP_OFFSET:
            return True
        return False

    def move(self, lights):
        # Emergency vehicles never stop
        if self.is_emergency:
            self._advance()
            return

        # Mark as crossed once vehicle is inside the intersection
        if not self.has_crossed and self._passed_intersection():
            self.has_crossed = True

        # If already crossed → ignore signals
        if self.has_crossed:
            self._advance()
            return

        # Otherwise obey signals
        for light in lights:
            if light.direction == self.direction:
                if light.state == "red" and self._is_before_stop_line(light):
                    return  # stop
                if light.state == "yellow" and self._is_before_stop_line(light):
                    self.speed = max(MIN_SPEED, self.speed * 0.6)  # slow down
        self._advance()

    def _advance(self):
        """Move forward depending on direction."""
        if self.direction == "N":
            self.y += self.speed
        elif self.direction == "S":
            self.y -= self.speed
        elif self.direction == "E":
            self.x -= self.speed
        elif self.direction == "W":
            self.x += self.speed

    def draw(self, screen):
        rect = pygame.Rect(int(self.x), int(self.y), VEHICLE_WIDTH, VEHICLE_HEIGHT)
        pygame.draw.rect(screen, self.color, rect)
