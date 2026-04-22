import pygame
from game_state import GameState, Phase

# Colors
BLACK  = (0,   0,   0)
WHITE  = (255, 255, 255)
RED    = (220, 50,  50)
BLUE   = (50,  100, 220)
GREEN  = (50,  200,  80)
YELLOW = (255, 220,  0)
GRAY   = (80,  80,  80)
DARK   = (20,  20,  20)

SCREEN_W = 1280
SCREEN_H = 720

TEAM_LEFT_NAME  = "Red"
TEAM_RIGHT_NAME = "Blue"


class Scoreboard:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("RoboSoccer")

        self.font_score  = pygame.font.SysFont("Arial", 160, bold=True)
        self.font_time   = pygame.font.SysFont("Arial", 72,  bold=True)
        self.font_label  = pygame.font.SysFont("Arial", 36)
        self.font_event  = pygame.font.SysFont("Arial", 48,  bold=True)
        self.font_small  = pygame.font.SysFont("Arial", 28)

        self.clock = pygame.time.Clock()

        # Load optional sound effects (fails silently if files missing)
        pygame.mixer.init()
        self._goal_sound    = self._load_sound("sounds/goal.mp3")
        self._whistle_sound = self._load_sound("sounds/whistle.mp3")

        # Crowd noise — loops during live play
        self._crowd_loaded = self._load_music("sounds/football_crowd.mp3")
        self._crowd_playing = False

        self._last_event = ""
        self._last_phase = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, gs: GameState, debug_frame=None):
        """Call once per frame with the current GameState.
        Note: pygame events are handled by the caller (main.py); do not drain
        the event queue here or keyboard/quit events will be silently dropped.
        """
        # Play sounds on new events
        if gs.last_event != self._last_event:
            self._handle_sound(gs.last_event)
            self._last_event = gs.last_event

        # Manage crowd noise based on phase
        if gs.phase != self._last_phase:
            self._handle_crowd(gs.phase)
            self._last_phase = gs.phase

        self.screen.fill(DARK)
        self._draw_field_bg()
        self._draw_scores(gs)
        self._draw_timer(gs)
        self._draw_phase_banner(gs)

        if debug_frame is not None:
            self._draw_debug_feed(debug_frame)

        pygame.display.flip()
        self.clock.tick(60)

    def quit(self):
        pygame.quit()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_field_bg(self):
        # Simple two-color halves to visually indicate team sides
        pygame.draw.rect(self.screen, (40, 10, 10),   (0, 0, SCREEN_W // 2, SCREEN_H))
        pygame.draw.rect(self.screen, (10, 10, 40),   (SCREEN_W // 2, 0, SCREEN_W // 2, SCREEN_H))
        pygame.draw.line(self.screen, GRAY, (SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H), 3)

    def _draw_scores(self, gs: GameState):
        # Left score
        surf = self.font_score.render(str(gs.score[0]), True, RED)
        self.screen.blit(surf, (SCREEN_W // 4 - surf.get_width() // 2, SCREEN_H // 2 - surf.get_height() // 2 - 40))

        # Right score
        surf = self.font_score.render(str(gs.score[1]), True, BLUE)
        self.screen.blit(surf, (3 * SCREEN_W // 4 - surf.get_width() // 2, SCREEN_H // 2 - surf.get_height() // 2 - 40))

        # Team labels
        left_lbl = self.font_label.render(TEAM_LEFT_NAME, True, RED)
        self.screen.blit(left_lbl, (SCREEN_W // 4 - left_lbl.get_width() // 2, 30))

        right_lbl = self.font_label.render(TEAM_RIGHT_NAME, True, BLUE)
        self.screen.blit(right_lbl, (3 * SCREEN_W // 4 - right_lbl.get_width() // 2, 30))

    def _draw_timer(self, gs: GameState):
        mins = int(gs.half_time_remaining) // 60
        secs = int(gs.half_time_remaining) % 60
        time_str = f"{mins}:{secs:02d}"
        color = YELLOW if gs.half_time_remaining > 30 else RED
        surf = self.font_time.render(time_str, True, color)
        self.screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, SCREEN_H - 120))

        half_str = f"Half {gs.half}"
        hs = self.font_small.render(half_str, True, WHITE)
        self.screen.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, SCREEN_H - 55))

    def _draw_phase_banner(self, gs: GameState):
        msg = ""
        color = WHITE

        if gs.phase == Phase.WAITING:
            msg = "Press SPACE to start"
        elif gs.phase == Phase.KICKOFF:
            msg = f"Kickoff in {int(gs.kickoff_countdown) + 1}..."
            color = YELLOW
        elif gs.phase == Phase.GOAL:
            team = TEAM_LEFT_NAME if gs.last_scorer == 0 else TEAM_RIGHT_NAME
            msg = f"GOAL — {team}!"
            color = GREEN
        elif gs.phase == Phase.HALFTIME:
            msg = "Half Time — Press SPACE for 2nd Half"
            color = YELLOW
        elif gs.phase == Phase.GAME_OVER:
            if gs.score[0] > gs.score[1]:
                winner = TEAM_LEFT_NAME
            elif gs.score[1] > gs.score[0]:
                winner = TEAM_RIGHT_NAME
            else:
                winner = "Nobody — it's a draw"
            msg = f"GAME OVER  |  Winner: {winner}"
            color = GREEN

        if msg:
            surf = self.font_event.render(msg, True, color)
            x = SCREEN_W // 2 - surf.get_width() // 2
            y = SCREEN_H // 2 + 120
            # Semi-transparent background pill
            pad = 16
            bg = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            self.screen.blit(bg, (x - pad, y - pad // 2))
            self.screen.blit(surf, (x, y))

    def _draw_debug_feed(self, cv_frame):
        """Shrink the OpenCV debug frame and draw it in the corner."""
        import cv2
        import numpy as np
        h, w = cv_frame.shape[:2]
        scale = 280 / w
        small = cv2.resize(cv_frame, (280, int(h * scale)))
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(np.transpose(small_rgb, (1, 0, 2)))
        self.screen.blit(surf, (SCREEN_W - 290, 10))

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
