import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class Phase(Enum):
    WAITING = auto()       # Before game starts
    KICKOFF = auto()       # Countdown before each kickoff
    LIVE = auto()          # Ball in play
    GOAL = auto()          # Goal just scored — brief freeze
    HALFTIME = auto()      # Between halves
    GAME_OVER = auto()     # Match finished


KICKOFF_DURATION = 10.0    # seconds of countdown
GOAL_FREEZE = 10.0         # seconds to pause after a goal (time to reset ball)
HALF_DURATION = 180.0     # seconds per half (3 minutes)
NUM_HALVES = 2


@dataclass
class GameState:
    phase: Phase = Phase.WAITING
    score: list = field(default_factory=lambda: [0, 0])   # [left, right]
    half: int = 1
    half_time_remaining: float = HALF_DURATION
    kickoff_countdown: float = KICKOFF_DURATION
    goal_freeze_remaining: float = 0.0
    last_scorer: Optional[int] = None                      # 0 = left, 1 = right
    last_event: str = ""

    # Internal
    _last_tick: float = field(default_factory=time.time, repr=False)

    def tick(self):
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        if self.phase == Phase.KICKOFF:
            self.kickoff_countdown -= dt
            if self.kickoff_countdown <= 0:
                self.kickoff_countdown = 0
                self.phase = Phase.LIVE
                self.last_event = "kickoff"

        elif self.phase == Phase.LIVE:
            self.half_time_remaining -= dt
            if self.half_time_remaining <= 0:
                self.half_time_remaining = 0
                if self.half < NUM_HALVES:
                    self.phase = Phase.HALFTIME
                    self.last_event = "halftime"
                else:
                    self.phase = Phase.GAME_OVER
                    self.last_event = "game_over"

        elif self.phase == Phase.GOAL:
            self.goal_freeze_remaining -= dt
            if self.goal_freeze_remaining <= 0:
                self._start_kickoff()

        elif self.phase == Phase.HALFTIME:
            # Halftime advances on explicit call to start_second_half()
            pass

    def start_game(self):
        self.score = [0, 0]
        self.half = 1
        self.half_time_remaining = HALF_DURATION
        self.last_event = "game_start"
        self._start_kickoff()

    def goal_scored(self, side: int):
        """side: 0 = left team scored, 1 = right team scored"""
        if self.phase != Phase.LIVE:
            return
        self.score[side] += 1
        self.last_scorer = side
        self.phase = Phase.GOAL
        self.goal_freeze_remaining = GOAL_FREEZE
        team = "Left" if side == 0 else "Right"
        self.last_event = f"goal_{team.lower()}"

    def start_second_half(self):
        if self.phase != Phase.HALFTIME:
            return
        self.half = 2
        self.half_time_remaining = HALF_DURATION
        self.last_event = "second_half"
        self._start_kickoff()

    def _start_kickoff(self):
        self.phase = Phase.KICKOFF
        self.kickoff_countdown = KICKOFF_DURATION

    def summary_dict(self) -> dict:
        return {
            "phase": self.phase.name,
            "score_left": self.score[0],
            "score_right": self.score[1],
            "half": self.half,
            "time_remaining": round(self.half_time_remaining, 1),
            "last_event": self.last_event,
        }
