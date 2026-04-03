"""
Smart Traffic Management System — Main Entry Point

Run:
    python -m simulation.main
  or from project root:
    python simulation/main.py

Controls:
  N         — Normal traffic mode
  R         — Rush hour (high vehicle density)
  G         — Night mode (low density)
  E         — Manually spawn emergency vehicle
  P / Space — Pause / Resume
  S         — Export stats snapshot to CSV
  ESC / Q   — Quit (auto-exports session stats)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from simulation.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, WINDOW_TITLE, C,
    SIM_PANEL_W, DASH_PANEL_X, DASH_PANEL_W,
)
from simulation.intersection import Intersection
from simulation.dashboard    import Dashboard
from simulation.logger       import SimLogger
from simulation.stats        import StatsCollector


def _export_session(intersection, stats, logger, tick):
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = os.path.join("data", f"run_{ts}.csv")
    json_path = os.path.join("data", f"summary_{ts}.json")
    stats.export_csv(csv_path)
    stats.export_json(json_path)
    stats.summary()
    logger.event("session_end", tick=tick,
                 total_passed=intersection.total_vehicles_passed,
                 emergency_events=intersection.emergency_events)
    logger.close()


def main():
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock  = pygame.time.Clock()

    sim_surface  = pygame.Surface((SIM_PANEL_W, WINDOW_HEIGHT))
    intersection = Intersection()
    dashboard    = Dashboard(intersection)
    dashboard.init_fonts()

    logger = SimLogger(enabled=True)
    stats  = StatsCollector()

    font_hud = pygame.font.SysFont("monospace", 11)
    logger.event("session_start", tick=0, mode=intersection.mode)

    tick    = 0
    running = True

    print("=" * 60)
    print("  Smart Traffic Management System  v1.0")
    print("  N=Normal  R=RushHour  G=Night  E=Emergency")
    print("  P/Space=Pause  S=Export  ESC=Quit")
    print("=" * 60)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_n:
                    intersection.set_mode("normal")
                    dashboard._set_mode_active("normal")
                    logger.event("mode_change", tick=tick, mode="normal")
                elif event.key == pygame.K_r:
                    intersection.set_mode("rush_hour")
                    dashboard._set_mode_active("rush_hour")
                    logger.event("mode_change", tick=tick, mode="rush_hour")
                elif event.key == pygame.K_g:
                    intersection.set_mode("night")
                    dashboard._set_mode_active("night")
                    logger.event("mode_change", tick=tick, mode="night")
                elif event.key == pygame.K_e:
                    intersection.spawn_emergency()
                    logger.event("manual_emergency", tick=tick)
                elif event.key in (pygame.K_p, pygame.K_SPACE):
                    intersection.paused = not intersection.paused
                    logger.event("pause_toggle", tick=tick, paused=intersection.paused)
                elif event.key == pygame.K_s:
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    stats.export_csv(os.path.join("data", f"snapshot_{ts}.csv"))

            action = dashboard.handle_event(event)
            if action == "mode:normal":
                intersection.set_mode("normal")
                logger.event("mode_change", tick=tick, mode="normal")
            elif action == "mode:rush_hour":
                intersection.set_mode("rush_hour")
                logger.event("mode_change", tick=tick, mode="rush_hour")
            elif action == "mode:night":
                intersection.set_mode("night")
                logger.event("mode_change", tick=tick, mode="night")
            elif action == "emergency":
                intersection.spawn_emergency()
                logger.event("manual_emergency", tick=tick)
            elif action == "pause":
                intersection.paused = not intersection.paused

        if not intersection.paused:
            intersection.update()
            dashboard.update(tick)

            ctrl = intersection.controller
            if ctrl.phase_timer == 1 and ctrl.state == "green":
                logger.event("phase_change", tick=tick,
                             phase=ctrl.phase,
                             adaptive_green_s=round(ctrl.green_duration / FPS, 1))
            if ctrl.emergency_active and ctrl.emergency_countdown == 6 * FPS - 1:
                logger.event("emergency_preemption", tick=tick, phase=ctrl.emergency_phase)

            ml_pred = intersection.predictor.predict(tick)
            stats.record(tick, intersection, ml_pred)
            logger.snapshot(tick, intersection, ml_pred)
            tick += 1

        screen.fill(C["bg"])
        sim_surface.fill(C["bg"])
        intersection.draw(sim_surface, tick)
        screen.blit(sim_surface, (0, 0))
        pygame.draw.line(screen, C["accent_dim"],
                         (SIM_PANEL_W, 0), (SIM_PANEL_W, WINDOW_HEIGHT), 1)
        dashboard.draw(screen, tick)

        fps_surf = font_hud.render(f"FPS {clock.get_fps():.0f}  |  tick {tick}", True, C["text_dim"])
        screen.blit(fps_surf, (8, 8))

        if intersection.paused:
            overlay = pygame.Surface((SIM_PANEL_W, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            fnt = pygame.font.SysFont("segoeui", 36, bold=True)
            ps  = fnt.render("PAUSED", True, C["text_bright"])
            screen.blit(ps, ps.get_rect(center=(SIM_PANEL_W // 2, WINDOW_HEIGHT // 2)))
            hint = font_hud.render("Press P or Space to resume", True, C["text_dim"])
            screen.blit(hint, hint.get_rect(center=(SIM_PANEL_W // 2, WINDOW_HEIGHT // 2 + 40)))

        pygame.display.flip()
        clock.tick(FPS)

    _export_session(intersection, stats, logger, tick)
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
