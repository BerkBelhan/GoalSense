"""
logger.py – structured event logging for GoalSense.

Sets up a root logger that writes to both stdout and (optionally) a log file.
Also exposes :func:`log_goal` as a convenience helper used by the main loop.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from goalsense.state import GoalEvent, GoalSide


def setup_logging(log_file: str = "", level: int = logging.INFO) -> None:
    """Configure the root logger.

    Parameters
    ----------
    log_file:
        If non-empty, a :class:`~logging.FileHandler` is added so that events
        are also persisted to disk.
    level:
        Logging level (e.g. ``logging.DEBUG``).
    """
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(console)

    # Optional file handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt, datefmt))
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Could not open log file %r: %s", log_file, exc)


def log_goal(
    event: GoalEvent,
    home_team: str = "Home",
    away_team: str = "Away",
) -> None:
    """Log a :class:`~goalsense.state.GoalEvent` with human-readable context.

    Parameters
    ----------
    event:
        The goal event to log.
    home_team / away_team:
        Display names used in the log message.
    """
    _logger = logging.getLogger("goalsense.events")

    scorer = home_team if event.home_scored else away_team
    tag = "PLAYER GOAL" if event.side == GoalSide.PLAYER else "OPPONENT GOAL"

    _logger.info(
        "[%s] %s scored  |  %s %s – %s %s",
        tag,
        scorer,
        home_team,
        event.home_score,
        event.away_score,
        away_team,
    )
