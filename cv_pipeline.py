import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


# --- Ball HSV — tune with hsv_calibrate.py ---
HSV_LOWER = np.array([25, 145, 121])
HSV_UPPER = np.array([56, 255, 255])

# --- Red car (left team) — red wraps in HSV so two ranges are needed ---
# Tune with hsv_calibrate.py pointed at your red car
CAR_LEFT_HSV_LOWER1 = np.array([0,   120, 60])
CAR_LEFT_HSV_UPPER1 = np.array([10,  255, 255])
CAR_LEFT_HSV_LOWER2 = np.array([170, 120, 60])
CAR_LEFT_HSV_UPPER2 = np.array([180, 255, 255])

# --- Blue car (right team) ---
# Tune with hsv_calibrate.py pointed at your blue car
CAR_RIGHT_HSV_LOWER = np.array([100, 120, 60])
CAR_RIGHT_HSV_UPPER = np.array([130, 255, 255])

MIN_BALL_AREA    = 300    # pixels²
MIN_CIRCULARITY  = 0.65
MIN_CAR_AREA     = 800    # pixels² — cars are larger than the ball
CONFIRM_FRAMES   = 3


@dataclass
class BallState:
    detected: bool
    centroid: Optional[Tuple[int, int]]
    radius: float


@dataclass
class CarState:
    detected: bool
    centroid: Optional[Tuple[int, int]]


class CVPipeline:
    def __init__(self, goal_left: dict, goal_right: dict, field_polygon: np.ndarray):
        """
        goal_left / goal_right: {"x1": int, "y1": int, "x2": int, "y2": int}
        field_polygon: np.array of shape (N, 2) defining the playable field boundary
        """
        self.goal_left = goal_left
        self.goal_right = goal_right
        self.field_polygon = field_polygon

        self._goal_left_counter = 0
        self._goal_right_counter = 0

        self.homography: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, frame: np.ndarray) -> Tuple[BallState, CarState, CarState, bool, bool, np.ndarray]:
        """
        Process one frame.
        Returns (ball, car_left, car_right, goal_left_scored, goal_right_scored, debug_frame)
        """
        debug = frame.copy()

        # Compute HSV once, reuse for all detections
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        ball      = self._detect_ball(hsv)
        car_left  = self._detect_car(hsv, CAR_LEFT_HSV_LOWER1,  CAR_LEFT_HSV_UPPER1,
                                          CAR_LEFT_HSV_LOWER2,  CAR_LEFT_HSV_UPPER2)
        car_right = self._detect_car(hsv, CAR_RIGHT_HSV_LOWER, CAR_RIGHT_HSV_UPPER)

        goal_left = False
        goal_right = False

        if ball.detected and ball.centroid is not None:
            cx, cy = ball.centroid

            if self._in_rect(cx, cy, self.goal_left):
                self._goal_left_counter += 1
                self._goal_right_counter = 0
            elif self._in_rect(cx, cy, self.goal_right):
                self._goal_right_counter += 1
                self._goal_left_counter = 0
            else:
                self._goal_left_counter = 0
                self._goal_right_counter = 0

            if self._goal_left_counter >= CONFIRM_FRAMES:
                goal_left = True
                self._goal_left_counter = 0

            if self._goal_right_counter >= CONFIRM_FRAMES:
                goal_right = True
                self._goal_right_counter = 0

        self._draw_overlays(debug, ball, car_left, car_right)
        return ball, car_left, car_right, goal_left, goal_right, debug

    def reset_goal_counters(self):
        self._goal_left_counter = 0
        self._goal_right_counter = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_ball(self, hsv: np.ndarray) -> BallState:
        mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER) # binary masking to isolate pixels in the HSV range defined for the ball

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)) 
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,   kernel, iterations=2) # removes small noise blobs
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1) # fills in gaps in detected areas to help contour detection

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # finds contours in the mask (i.e. connected components of white pixels)

        # this is the logic to determine which contour is the ball based on area and circularity
        best = None
        best_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_BALL_AREA:
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter ** 2)
            if circularity < MIN_CIRCULARITY:
                continue
            if area > best_area:
                best_area = area
                best = cnt

        if best is None:
            return BallState(detected=False, centroid=None, radius=0.0)

        # compute smallest enclosing circle and centroid for the best contour
        _, radius = cv2.minEnclosingCircle(best)
        M = cv2.moments(best)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return BallState(detected=True, centroid=(cx, cy), radius=radius)

    def _detect_car(self, hsv: np.ndarray,
                    lower1: np.ndarray, upper1: np.ndarray,
                    lower2: Optional[np.ndarray] = None,
                    upper2: Optional[np.ndarray] = None) -> CarState:
        mask = cv2.inRange(hsv, lower1, upper1)
        if lower2 is not None:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower2, upper2))

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,   kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best = None
        best_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_CAR_AREA:
                continue
            if area > best_area:
                best_area = area
                best = cnt

        if best is None:
            return CarState(detected=False, centroid=None)

        M = cv2.moments(best)
        if M["m00"] == 0:
            return CarState(detected=False, centroid=None)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return CarState(detected=True, centroid=(cx, cy))

    def _in_rect(self, x: int, y: int, rect: dict) -> bool:
        return rect["x1"] <= x <= rect["x2"] and rect["y1"] <= y <= rect["y2"]

    def _draw_overlays(self, frame: np.ndarray, ball: BallState,
                       car_left: CarState, car_right: CarState):
        # Field boundary
        if self.field_polygon is not None and len(self.field_polygon) > 0:
            cv2.polylines(frame, [self.field_polygon], True, (0, 255, 0), 2)

        # Goal zones
        gl = self.goal_left
        cv2.rectangle(frame, (gl["x1"], gl["y1"]), (gl["x2"], gl["y2"]), (255, 0, 0), 2)
        cv2.putText(frame, "GOAL L", (gl["x1"], gl["y1"] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

        gr = self.goal_right
        cv2.rectangle(frame, (gr["x1"], gr["y1"]), (gr["x2"], gr["y2"]), (0, 0, 255), 2)
        cv2.putText(frame, "GOAL R", (gr["x1"], gr["y1"] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Ball
        if ball.detected and ball.centroid is not None:
            cv2.circle(frame, ball.centroid, int(ball.radius), (0, 255, 255), 2)
            cv2.circle(frame, ball.centroid, 4, (0, 255, 255), -1)

        # Cars
        if car_left.detected and car_left.centroid is not None:
            cv2.circle(frame, car_left.centroid, 12, (0, 0, 255), -1)
            cv2.putText(frame, "RED", (car_left.centroid[0] + 14, car_left.centroid[1] + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

        if car_right.detected and car_right.centroid is not None:
            cv2.circle(frame, car_right.centroid, 12, (255, 80, 0), -1)
            cv2.putText(frame, "BLUE", (car_right.centroid[0] + 14, car_right.centroid[1] + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 80, 0), 1)
