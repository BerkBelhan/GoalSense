# GoalSense

**Real-time, anti-cheat-safe goal detection overlay for EA FC 26.**

GoalSense watches a configurable region of your screen, detects when the scoreboard changes, and instantly plays a custom goal song — all without touching game memory or processes.

---

## Features

| Feature | Details |
|---|---|
| Screen capture | `mss` – low-overhead, cross-platform |
| Digit recognition | OpenCV template matching (no OCR dependency) |
| False-positive filter | Requires N consecutive identical frames before accepting a score change |
| Cooldown guard | Configurable quiet period after each goal |
| Audio playback | `pygame.mixer` in a background thread (non-blocking) |
| Goal attribution | Home / Away → Player / Opponent based on a single config flag |
| Logging | Timestamped events to stdout and optional log file |
| Calibration tool | Interactive GUI to select the screen region and capture digit templates |

---

## Quick start

### 1  Install dependencies

```bash
pip install -r requirements.txt
```

### 2  Calibrate

Run the interactive calibration tool **while the game is visible on screen**:

```bash
python calibrate.py
```

The tool will guide you through three steps:

1. **Draw a rectangle** around the scoreboard region.
2. **Capture digit templates** – draw a box around each digit (0–9) as it appears on the scoreboard.
3. **Select sub-regions** – draw boxes for the home and away score digits separately.

Copy the printed config values into `goalsense/config.py`.

### 3  Add your goal sound

Drop an audio file (MP3, OGG, WAV …) into the `sounds/` directory and set the path in `goalsense/config.py`:

```python
PLAYER_GOAL_SOUND = "sounds/goal.mp3"
```

### 4  Run

```bash
python main.py
```

Press **Ctrl+C** to stop.

---

## Configuration

All settings live in **`goalsense/config.py`**:

```python
# Screen region (pixels on your monitor)
SCOREBOARD_REGION = {"top": 30, "left": 830, "width": 260, "height": 50}

# Score digit sub-regions (relative to SCOREBOARD_REGION)
HOME_SCORE_SUBREGION = (70, 8, 35, 34)   # (x, y, width, height)
AWAY_SCORE_SUBREGION = (155, 8, 35, 34)

# True if you control the home team
PLAYER_IS_HOME = True

# Audio
PLAYER_GOAL_SOUND   = "sounds/goal.mp3"
OPPONENT_GOAL_SOUND = ""                  # leave empty to disable

# Detection tuning
CAPTURE_FPS           = 10     # frames per second
SCORE_CONFIRM_FRAMES  = 3      # consecutive identical frames required
GOAL_COOLDOWN_SECONDS = 8.0    # seconds between detections
TEMPLATE_MATCH_THRESHOLD = 0.75
```

---

## Project structure

```
GoalSense/
├── main.py               # Entry point – detection loop
├── calibrate.py          # Interactive calibration GUI
├── requirements.txt
├── goalsense/
│   ├── config.py         # All configuration constants
│   ├── capture.py        # Screen capture (mss wrapper)
│   ├── detection.py      # Template matching digit recognition
│   ├── state.py          # Score state, debounce, goal attribution
│   ├── audio.py          # Non-blocking pygame audio playback
│   └── logger.py         # Structured event logging
├── templates/            # Digit template PNGs (0.png – 9.png)
└── sounds/               # Audio files
```

---

## Running the tests

```bash
pip install pytest
pytest tests/ -v
```

---

## How it works

```
  Screen → ScreenCapture.grab()
         → ScoreDetector.detect()    ← TemplateBank (0.png…9.png)
         → ScoreState.update()       ← debounce + cooldown
         → GoalEvent                 → AudioPlayer.play()
                                     → log_goal()
```

1. Every frame (`1 / CAPTURE_FPS` seconds) a small region of the screen is captured.
2. Two digit sub-regions (home score, away score) are cropped and matched against the pre-captured templates using OpenCV normalised cross-correlation.
3. `ScoreState` buffers readings until `SCORE_CONFIRM_FRAMES` consecutive identical readings agree, then validates the transition (must be exactly +1 on exactly one side).
4. A cooldown prevents a second trigger for `GOAL_COOLDOWN_SECONDS` seconds.
5. On a confirmed goal, `AudioPlayer` queues the sound file on a daemon thread and `log_goal` writes a timestamped line.

---

## Notes

- **Anti-cheat safe** – GoalSense only reads pixels from the screen; it never attaches to or reads game memory.
- **Multi-digit scores** – The current sub-region approach covers single-digit scores (0–9).  For double-digit scores you would widen the sub-regions and extend `ScoreDetector` to parse two digits sequentially.
- **Resolution** – Digit templates must be captured at your game's native resolution.  The `TEMPLATE_SCALES` list (default `[0.9, 1.0, 1.1]`) handles minor size differences automatically.
