# dashboard.py
import pygame
import time

class Dashboard:
    """Simple dashboard overlay at bottom of screen."""
    HEIGHT = 140

    def __init__(self, width, height):
        self.width = width
        self.height = height
        if not pygame.font.get_init():
            pygame.font.init()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.last_flash = 0
        self.flash_on = True

    def draw_light_status(self, screen, light, x, y):
        box_w, box_h = 140, 28
        pygame.draw.rect(screen, (50, 50, 50), (x, y, box_w, box_h))
        color = (0, 200, 0) if light.state == "green" else (200, 0, 0)
        if light.state == "yellow":
            color = (255, 255, 0)
        txt = f"{light.direction}: {light.state.upper()}"
        surf = self.font.render(txt, True, color)
        screen.blit(surf, (x + 8, y + 6))

    def draw(self, screen, vehicles, lights, predictor):
        panel_y = self.height - Dashboard.HEIGHT
        pygame.draw.rect(screen, (30, 30, 30), (0, panel_y, self.width, Dashboard.HEIGHT))

        title = self.title_font.render("Simulation Dashboard", True, (240,240,240))
        screen.blit(title, (10, panel_y + 6))

        # Draw lights info (two columns)
        lx, ly = 10, panel_y + 36
        sorted_lights = sorted(lights, key=lambda L: L.direction)
        for i, light in enumerate(sorted_lights):
            self.draw_light_status(screen, light, lx + (i % 2) * 150, ly + (i // 2) * 34)

        # Vehicle counts by direction with small bars
        dirs = ["N", "S", "E", "W"]
        start_x = 340
        start_y = panel_y + 36
        counts = {d: sum(1 for v in vehicles if v.direction == d) for d in dirs}
        max_count = max(1, max(counts.values()))
        max_bar_w = 180
        for i, d in enumerate(dirs):
            cx = start_x + (i % 2) * 200
            cy = start_y + (i // 2) * 34
            txt = self.font.render(f"{d} queue: {counts[d]}", True, (230,230,230))
            screen.blit(txt, (cx, cy))
            bar_w = int((counts[d] / max_count) * max_bar_w)
            pygame.draw.rect(screen, (80,80,80), (cx + 100, cy + 2, max_bar_w, 20))
            pygame.draw.rect(screen, (0,160,250), (cx + 100, cy + 2, bar_w, 20))

        # --- NEW: Adaptive green time display ---
        if hasattr(predictor, "current_green_duration"):
            green_txt = self.font.render(
                f"Adaptive Green Time: {predictor.current_green_duration}s",
                True, (0, 255, 0)
            )
            screen.blit(green_txt, (10, panel_y + 92))

        
        # AI prediction (use recent history if available)
        try:
            pred = predictor.history[-1] if predictor.history else predictor.predict_next()
        except Exception:
            pred = "N/A"
        pred_txt = self.font.render(f"AI forecast (recent): {pred}", True, (180,220,255))
        screen.blit(pred_txt, (10, panel_y + 92))

        # Emergency alert (flashing)
        if any(getattr(v, 'is_emergency', False) for v in vehicles):
            now = time.time()
            if now - self.last_flash > 0.4:
                self.flash_on = not self.flash_on
                self.last_flash = now
            if self.flash_on:
                alert = self.font.render("🚨 Emergency vehicle present!", True, (255,80,80))
                screen.blit(alert, (320, panel_y + 92))
