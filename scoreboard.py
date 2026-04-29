import cv2
import numpy as np
import pygame
from game_state import GameState, Phase

# Colors
WHITE  = (255, 255, 255)
RED    = (220, 50,  50)
BLUE   = (50,  100, 220)
GREEN  = (50,  200,  80)
YELLOW = (255, 220,  0)
GRAY   = (80,  80,  80)
DARK   = (20,  20,  20)

SCREEN_W = 1280
SCREEN_H = 720
BAR_H    = 80       # height of the bottom scoreboard bar

TEAM_LEFT_NAME  = "Red"
TEAM_RIGHT_NAME = "Blue"


class Scoreboard:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("RoboSoccer")

        self.font_score  = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_label  = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_time   = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_event  = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_small  = pygame.font.SysFont("Arial", 22)

        self.clock = pygame.time.Clock()

        pygame.mixer.init()
        self._goal_sound    = self._load_sound("sounds/goal.mp3")
        self._whistle_sound = self._load_sound("sounds/whistle.mp3")

        self._crowd_loaded  = self._load_music("sounds/football_crowd.mp3")
        self._crowd_playing = False

        self._last_event = ""
        self._last_phase = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, gs: GameState, cv_frame=None):
        """Call once per frame. cv_frame is the annotated camera frame (BGR)."""
        # Sound events
        if gs.last_event != self._last_event:
            self._handle_sound(gs.last_event)
            self._last_event = gs.last_event

        if gs.phase != self._last_phase:
            self._handle_crowd(gs.phase)
            self._last_phase = gs.phase

        # --- Background: camera feed or solid dark ---
        if cv_frame is not None:
            self._draw_camera_bg(cv_frame)
        else:
            self.screen.fill(DARK)

        # --- Overlays ---
        self._draw_bottom_bar(gs)
        self._draw_phase_banner(gs)

        pygame.display.flip()
        self.clock.tick(60)

    def quit(self):
        pygame.quit()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_camera_bg(self, cv_frame):
        """Scale the CV frame to fill the screen and blit it as the background."""
        scaled = cv2.resize(cv_frame, (SCREEN_W, SCREEN_H))
        rgb    = cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)
        surf   = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
        self.screen.blit(surf, (0, 0))

    def _draw_bottom_bar(self, gs: GameState):
        bar_y = SCREEN_H - BAR_H

        # Semi-transparent dark background strip
        bar = pygame.Surface((SCREEN_W, BAR_H), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 200))
        self.screen.blit(bar, (0, bar_y))

        # Thin colored accent lines at the top of each team's section
        pygame.draw.rect(self.screen, RED,  (0,              bar_y, SCREEN_W // 3, 3))
        pygame.draw.rect(self.screen, BLUE, (2 * SCREEN_W // 3, bar_y, SCREEN_W // 3, 3))

        cx = SCREEN_W // 2
        cy = bar_y + BAR_H // 2

        # --- Left team (Red) ---
        name_surf = self.font_label.render(TEAM_LEFT_NAME.upper(), True, RED)
        score_surf = self.font_score.render(str(gs.score[0]), True, WHITE)
        # Right-align name+score in the left third
        total_w = name_surf.get_width() + 16 + score_surf.get_width()
        lx = SCREEN_W // 3 // 2 - total_w // 2
        self.screen.blit(name_surf,  (lx, cy - name_surf.get_height() // 2))
        self.screen.blit(score_surf, (lx + name_surf.get_width() + 16,
                                      cy - score_surf.get_height() // 2))

        # --- Center: timer + half ---
        mins = int(gs.half_time_remaining) // 60
        secs = int(gs.half_time_remaining) % 60
        time_str  = f"{mins}:{secs:02d}"
        time_color = YELLOW if gs.half_time_remaining > 30 else RED
        time_surf  = self.font_time.render(time_str, True, time_color)
        half_surf  = self.font_small.render(f"HALF {gs.half}", True, GRAY)
        self.screen.blit(time_surf, (cx - time_surf.get_width() // 2,
                                     cy - time_surf.get_height() // 2 - 6))
        self.screen.blit(half_surf, (cx - half_surf.get_width() // 2,
                                     cy + time_surf.get_height() // 2 - 8))

        # --- Right team (Blue) ---
        score_surf2 = self.font_score.render(str(gs.score[1]), True, WHITE)
        name_surf2  = self.font_label.render(TEAM_RIGHT_NAME.upper(), True, BLUE)
        total_w2 = score_surf2.get_width() + 16 + name_surf2.get_width()
        rx = 2 * SCREEN_W // 3 + (SCREEN_W // 3) // 2 - total_w2 // 2
        self.screen.blit(score_surf2, (rx, cy - score_surf2.get_height() // 2))
        self.screen.blit(name_surf2,  (rx + score_surf2.get_width() + 16,
                                       cy - name_surf2.get_height() // 2))

        # Divider lines
        pygame.draw.line(self.screen, GRAY,
                         (SCREEN_W // 3, bar_y + 4), (SCREEN_W // 3, SCREEN_H), 1)
        pygame.draw.line(self.screen, GRAY,
                         (2 * SCREEN_W // 3, bar_y + 4), (2 * SCREEN_W // 3, SCREEN_H), 1)

    def _draw_phase_banner(self, gs: GameState):
        msg   = ""
        color = WHITE

        if gs.phase == Phase.WAITING:
            msg = "Press SPACE to start"
        elif gs.phase == Phase.KICKOFF:
            msg = f"Kickoff in {int(gs.kickoff_countdown) + 1}..."
            color = YELLOW
        elif gs.phase == Phase.GOAL:
            team = TEAM_LEFT_NAME if gs.last_scorer == 0 else TEAM_RIGHT_NAME
            msg   = f"GOAL — {team}!"
            color = GREEN
        elif gs.phase == Phase.HALFTIME:
            msg   = "Half Time — Press SPACE for 2nd Half"
            color = YELLOW
        elif gs.phase == Phase.GAME_OVER:
            if gs.score[0] > gs.score[1]:
                winner = TEAM_LEFT_NAME
            elif gs.score[1] > gs.score[0]:
                winner = TEAM_RIGHT_NAME
            else:
                winner = "Nobody — it's a draw"
            msg   = f"GAME OVER  |  Winner: {winner}"
            color = GREEN

        if msg:
            surf = self.font_event.render(msg, True, color)
            x = SCREEN_W // 2 - surf.get_width() // 2
            y = SCREEN_H // 2 - surf.get_height() // 2
            pad = 20
            bg = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad),
                                 pygame.SRCALPHA)
            bg.fill((0, 0, 0, 170))
            self.screen.blit(bg,   (x - pad, y - pad // 2))
            self.screen.blit(surf, (x, y))

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------

    def _load_sound(self, path: str):
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None

    def _load_music(self, path: str) -> bool:
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            return True
        except Exception:
            return False

    def _handle_sound(self, event: str):
        if "goal" in event and self._goal_sound:
            self._goal_sound.play()
        elif event in ("kickoff", "second_half", "game_start") and self._whistle_sound:
            self._whistle_sound.play()

    def _handle_crowd(self, phase: Phase):
        if not self._crowd_loaded:
            return
        if phase in (Phase.LIVE, Phase.KICKOFF, Phase.GOAL):
            if not self._crowd_playing:
                pygame.mixer.music.play(loops=-1)
                self._crowd_playing = True
            vol = 0.2 if phase == Phase.GOAL else 0.4
            pygame.mixer.music.set_volume(vol)
        else:
            if self._crowd_playing:
                pygame.mixer.music.stop()
                self._crowd_playing = False
