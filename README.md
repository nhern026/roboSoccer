# RoboSoccer

2-player robot soccer game. Two humans control robot cars via Bluetooth.
A laptop with an overhead USB webcam handles all game logic, computer vision,
scoring, and optional AI commentary.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Calibrate ball detection

Place your orange ping pong ball on the field under your arena lighting and run:

```bash
python hsv_calibrate.py        # camera 0
python hsv_calibrate.py 1      # camera 1 if needed
```

Drag the sliders until **only the ball** shows white in the Mask window.
Press `p` to print the values, then paste them into `cv_pipeline.py`:

```python
HSV_LOWER = np.array([H_low, S_low, V_low])
HSV_UPPER = np.array([H_high, S_high, V_high])
```

### 3. Set goal and field coordinates

Run `main.py` once and look at the small debug feed in the top-right corner
of the scoreboard. Note the pixel positions of the goal mouths and field edges,
then update these constants in `main.py`:

```python
GOAL_LEFT  = {"x1": ..., "y1": ..., "x2": ..., "y2": ...}
GOAL_RIGHT = {"x1": ..., "y1": ..., "x2": ..., "y2": ...}
FIELD_POLY = np.array([[x,y], [x,y], ...], dtype=np.int32)
```

### 4. Run the game

```bash
# Basic — no commentary
python main.py

# With AI commentary (needs ANTHROPIC_API_KEY set)
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --commentary

# Different camera index
python main.py --cam 1

# Hide CV debug feed
python main.py --no-debug
```

## Controls (keyboard on the scoreboard window)

| Key | Action |
|-----|--------|
| SPACE | Start game / advance halftime / restart after game over |
| R | Reset to waiting screen |
| Q / ESC | Quit |

## File overview

| File | Purpose |
|------|---------|
| `main.py` | Entry point — wires everything together |
| `cv_pipeline.py` | Ball detection + goal/OOB detection |
| `game_state.py` | Game clock, score, phase state machine |
| `scoreboard.py` | pygame fullscreen scoreboard UI + sounds |
| `commentary.py` | Claude API commentary + text-to-speech |
| `hsv_calibrate.py` | Standalone HSV tuning tool |

## How ball detection works

Each camera frame goes through this pipeline in [`cv_pipeline.py`](cv_pipeline.py):

1. **Gaussian blur** — smooths the frame to reduce pixel-level noise before color analysis.
2. **BGR → HSV conversion** — HSV is used instead of RGB because hue is a single channel representing color, making detection much less sensitive to lighting changes.
3. **Binary masking** — `cv2.inRange` produces a black-and-white mask: white where pixels fall within the ball's configured HSV range, black everywhere else.
4. **Morphological cleanup** — `MORPH_OPEN` (erode then dilate) removes small noise blobs; `MORPH_DILATE` fills gaps in the ball's shape so it reads as one solid contour.
5. **Contour selection** — OpenCV finds all white islands in the cleaned mask. Each is tested against two thresholds:
   - Area ≥ `MIN_BALL_AREA` (300 px²) — rejects tiny dots
   - Circularity ≥ `MIN_CIRCULARITY` (0.65) using `4π·area / perimeter²` — rejects non-round shapes (a perfect circle scores 1.0)

   The largest surviving contour is chosen as the ball.
6. **Centroid + radius** — the centroid is computed via image moments (`m10/m00`, `m01/m00`); the enclosing circle radius is found with `minEnclosingCircle` and used only for drawing the overlay on the debug feed.

## Arena build tips

- **Walls:** 2×4 or 2×6 lumber screwed into a rectangular frame flat on the floor.
  Cars bounce off cleanly and the frame doesn't shift.
- **Goals:** Cut openings in the end walls. A thin dowel zip-tied across the opening
  defines goal height.
- **Field size:** ~3× car width wide, ~5× car length long is a good starting point.
- **Camera mount:** A cheap tripod or a 2×4 arm clamped to the arena wall works.
  Mount high enough that the full field is visible with some margin.
- **Ball:** Neon green wiffle ball — easy HSV isolation under most lighting.

## Troubleshooting

**Ball not detected:**
- Rerun `hsv_calibrate.py` under the same lighting you'll use for the game.
- Increase `MIN_BALL_AREA` in `cv_pipeline.py` if noise blobs are triggering.
- Decrease `MIN_CIRCULARITY` slightly if the ball is partially occluded.

**False goal triggers:**
- Increase `CONFIRM_FRAMES` in `cv_pipeline.py` (default 3).
- Shrink the goal ROI rectangles in `main.py` so they only cover the goal line.

**Commentary not firing:**
- Check `ANTHROPIC_API_KEY` is set in your environment.
- Commentary is skipped if the previous line hasn't finished speaking — this is
  intentional to avoid overlap.
