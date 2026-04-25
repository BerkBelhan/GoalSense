"""
main.py – GoalSense detection loop entry point.

Usage
-----
    python main.py

Adjust settings in ``goalsense/config.py`` (or ``config_local.py``) before
running.  Run ``calibrate.py`` first to capture digit templates and confirm
the screen region is correct.
"""

from __future__ import annotations

import logging
import signal
import sys
import time

from goalsense import config
from goalsense.audio import AudioPlayer
from goalsense.capture import ScreenCapture
from goalsense.detection import ScoreDetector, TemplateBank
from goalsense.logger import log_goal, setup_logging
from goalsense.state import GoalSide, ScoreState


def main() -> None:
    setup_logging(log_file=config.LOG_FILE)
    logger = logging.getLogger("goalsense.main")

    logger.info("GoalSense starting …")

    # ------------------------------------------------------------------ #
    # Validate templates                                                   #
    # ------------------------------------------------------------------ #
    bank = TemplateBank(
        templates_dir=config.TEMPLATES_DIR,
        threshold=config.TEMPLATE_MATCH_THRESHOLD,
    )
    if not bank.ready:
        logger.error(
            "No digit templates found in '%s'.  Run calibrate.py first.",
            config.TEMPLATES_DIR,
        )
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Build components                                                     #
    # ------------------------------------------------------------------ #
    detector = ScoreDetector(
        bank=bank,
        home_subregion=config.HOME_SCORE_SUBREGION,
        away_subregion=config.AWAY_SCORE_SUBREGION,
        scales=config.TEMPLATE_SCALES,
    )

    state = ScoreState(
        player_is_home=config.PLAYER_IS_HOME,
        confirm_frames=config.SCORE_CONFIRM_FRAMES,
        cooldown_seconds=config.GOAL_COOLDOWN_SECONDS,
    )

    # ------------------------------------------------------------------ #
    # Graceful shutdown                                                    #
    # ------------------------------------------------------------------ #
    running = True

    def _shutdown(signum: int, _frame: object) -> None:
        nonlocal running
        logger.info("Shutdown signal received.")
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ------------------------------------------------------------------ #
    # Detection loop                                                       #
    # ------------------------------------------------------------------ #
    frame_interval = 1.0 / config.CAPTURE_FPS

    with ScreenCapture(config.SCOREBOARD_REGION) as capture, \
            AudioPlayer(volume=config.AUDIO_VOLUME) as audio:

        logger.info(
            "Detection active  |  region=%s  fps=%d",
            config.SCOREBOARD_REGION,
            config.CAPTURE_FPS,
        )

        while running:
            loop_start = time.monotonic()

            frame = capture.grab()
            home, away = detector.detect(frame)
            event = state.update(home, away)

            if event is not None:
                log_goal(
                    event,
                    home_team=config.HOME_TEAM_NAME,
                    away_team=config.AWAY_TEAM_NAME,
                )
                if event.side == GoalSide.PLAYER:
                    audio.play(config.PLAYER_GOAL_SOUND)
                elif config.OPPONENT_GOAL_SOUND:
                    audio.play(config.OPPONENT_GOAL_SOUND)

            # Maintain target FPS
            elapsed = time.monotonic() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    logger.info("GoalSense stopped.")


if __name__ == "__main__":
    main()
