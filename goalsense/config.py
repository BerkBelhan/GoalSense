"""
GoalSense – central configuration.

All values can be overridden by creating a ``config_local.py`` file in the
project root that imports this module and then reassigns any of the constants
below.  ``main.py`` imports from this module, so changing it here is enough
for most use cases.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Screen region
# ---------------------------------------------------------------------------
# Pixel coordinates of the scoreboard region on your monitor.
# Adjust these values after running ``calibrate.py``.
#
# Format: {"top": int, "left": int, "width": int, "height": int}
SCOREBOARD_REGION: dict[str, int] = {
    "top": 30,
    "left": 830,
    "width": 260,
    "height": 50,
}

# Within SCOREBOARD_REGION, the sub-regions that contain the home and away
# score digits.  Coordinates are relative to the top-left of SCOREBOARD_REGION.
# Each entry is (x, y, w, h).
HOME_SCORE_SUBREGION: tuple[int, int, int, int] = (70, 8, 35, 34)
AWAY_SCORE_SUBREGION: tuple[int, int, int, int] = (155, 8, 35, 34)

# ---------------------------------------------------------------------------
# Template matching
# ---------------------------------------------------------------------------
# Directory that contains one PNG per digit named ``0.png`` through ``9.png``.
TEMPLATES_DIR: str = "templates"

# Minimum normalised cross-correlation score for a digit match (0–1).
TEMPLATE_MATCH_THRESHOLD: float = 0.75

# Scale factors to try when matching templates (handles minor resolution
# differences).  Each value is a multiplier applied to the template size.
TEMPLATE_SCALES: list[float] = [0.9, 1.0, 1.1]

# ---------------------------------------------------------------------------
# Detection loop
# ---------------------------------------------------------------------------
# How many consecutive frames must agree on a new score before it is accepted.
# Reduces false positives caused by replays or UI flashes.
SCORE_CONFIRM_FRAMES: int = 3

# Seconds to wait after a confirmed goal before the next goal can be detected.
GOAL_COOLDOWN_SECONDS: float = 8.0

# Target detection loop frequency (frames per second).
CAPTURE_FPS: int = 10

# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------
# Human-readable labels shown in logs and (future) UI.
HOME_TEAM_NAME: str = "Home"
AWAY_TEAM_NAME: str = "Away"

# Set to True if *you* are controlling the home team, False if you are the
# away team.  This determines the wording of goal-scored vs goal-conceded
# audio/log messages.
PLAYER_IS_HOME: bool = True

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
# Path to the audio file played when the player scores.
PLAYER_GOAL_SOUND: str = "sounds/goal.mp3"

# Path to the audio file played when the opponent scores.  Set to ``""`` to
# disable.
OPPONENT_GOAL_SOUND: str = ""

# Audio playback volume (0.0 – 1.0).
AUDIO_VOLUME: float = 1.0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Log file path.  Set to ``""`` to disable file logging (console only).
LOG_FILE: str = "goalsense.log"
