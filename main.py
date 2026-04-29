"""
RoboSoccer — main entry point

Usage:
    python main.py              # camera index 0, no commentary
    python main.py --cam 1      # use camera index 1
    python main.py --commentary # enable AI commentary (needs ANTHROPIC_API_KEY)
    python main.py --no-debug   # hide the CV debug feed on the scoreboard
"""

import argparse
import sys
import cv2
import numpy as np
import pygame

from cv_pipeline import CVPipeline
from game_state import GameState, Phase
from scoreboard import Scoreboard
from commentary import Commentary


# -----------------------------------------------------------------------
# FIELD SETUP — calibrate these to your physical arena
#
# Run the game once and look at the debug feed in the corner of the
# scoreboard window. Adjust the pixel coordinates below to match:
#
#   GOAL_LEFT  — rectangle covering the left goal mouth
#   GOAL_RIGHT — rectangle covering the right goal mouth
#   FIELD_POLY — polygon tracing the inner edge of your arena walls
#
# Tip: press 'c' while the game is running to print the current mouse
#      position to the terminal — useful for picking coordinates.
# -----------------------------------------------------------------------

GOAL_LEFT  = {"x1": 66,  "y1": 173, "x2": 114, "y2": 265}
GOAL_RIGHT = {"x1": 569, "y1": 171, "x2": 612, "y2": 246}

FIELD_POLY = np.array([
    [109, 57],
    [560, 59],
    [589, 372],
    [102, 388],
], dtype=np.int32)

CAMERA_INDEX = 0


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam",         type=int,  default=CAMERA_INDEX)
    ap.add_argument("--commentary",  action="store_true")
    ap.add_argument("--no-debug",    action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()

    # --- Camera ---
    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {args.cam}")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # --- Subsystems ---
    pipeline    = CVPipeline(GOAL_LEFT, GOAL_RIGHT, FIELD_POLY)
    gs          = GameState()
    scoreboard  = Scoreboard()
    commentary  = Commentary() if args.commentary else None
    show_debug  = not args.no_debug

    print("RoboSoccer started.")
    print("  SPACE  — start game / advance halftime")
    print("  R      — reset to waiting screen")
    print("  Q/ESC  — quit")

    pending_goal_state = None   # queued commentary fired at kickoff, not at goal

    while True:
        # --- Keyboard input (pygame) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _quit(cap, scoreboard)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    _quit(cap, scoreboard)
                elif event.key == pygame.K_SPACE:
                    if gs.phase == Phase.WAITING:
                        gs.start_game()
                    elif gs.phase == Phase.HALFTIME:
                        gs.start_second_half()
                    elif gs.phase == Phase.GAME_OVER:
                        gs = GameState()   # full reset
                elif event.key == pygame.K_r:
                    gs = GameState()
                    pipeline.reset_goal_counters()
                elif event.key == pygame.K_c:
                    mx, my = pygame.mouse.get_pos()
                    # Debug feed is drawn at (SCREEN_W-290, 10), scaled to 280px wide
                    scale = 280 / 640
                    cam_x = int((mx - (1280 - 290)) / scale)
                    cam_y = int((my - 10) / scale)
                    print(f"camera pixel: ({cam_x}, {cam_y})")

        # --- CV frame ---
        ret, frame = cap.read()
        if not ret:
            continue

        ball, car_left, car_right, goal_left, goal_right, debug_frame = pipeline.process(frame)

        def _build_state():
            state = gs.summary_dict()
            if ball.detected and ball.centroid:
                state["ball_x"], state["ball_y"] = ball.centroid
            if car_left.detected and car_left.centroid:
                state["red_car_x"], state["red_car_y"] = car_left.centroid
            if car_right.detected and car_right.centroid:
                state["blue_car_x"], state["blue_car_y"] = car_right.centroid
            return state

        # --- Goal events ---
        prev_phase = gs.phase
        if gs.phase == Phase.LIVE:
            if goal_left:
                gs.goal_scored(1)   # ball entered left goal → right team scores
                if commentary:
                    pending_goal_state = _build_state()
            elif goal_right:
                gs.goal_scored(0)   # ball entered right goal → left team scores
                if commentary:
                    pending_goal_state = _build_state()
            elif commentary:
                commentary.maybe_announce(_build_state())

        # --- Tick game clock ---
        gs.tick()

        # Fire queued goal commentary once the reset period ends and kickoff begins
        if prev_phase == Phase.GOAL and gs.phase == Phase.KICKOFF:
            if commentary and pending_goal_state:
                commentary.announce(pending_goal_state)
                pending_goal_state = None

        # --- Scoreboard ---
        scoreboard.update(gs, debug_frame if show_debug else None)


def _quit(cap, scoreboard):
    cap.release()
    scoreboard.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
