"""
state.py – score state management and goal attribution.

Responsibilities
----------------
* Track the last confirmed home/away score.
* Buffer candidate scores until :attr:`confirm_frames` consecutive identical
  readings agree (debounce against replay / UI flash artefacts).
* Enforce a cooldown period after each confirmed goal.
* Determine whether a goal was scored by the player or the opponent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class GoalSide(Enum):
    """Who scored the goal."""
    PLAYER = auto()
    OPPONENT = auto()


@dataclass
class GoalEvent:
    """Emitted when a goal is confirmed."""
    side: GoalSide
    home_score: int
    away_score: int
    home_scored: bool  # True when the home team scored this goal
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def score_str(self) -> str:
        return f"{self.home_score} – {self.away_score}"


class ScoreState:
    """Maintains score history and emits :class:`GoalEvent` objects."""

    def __init__(
        self,
        player_is_home: bool = True,
        confirm_frames: int = 3,
        cooldown_seconds: float = 8.0,
    ) -> None:
        """
        Parameters
        ----------
        player_is_home:
            ``True`` when the local player controls the home team.
        confirm_frames:
            Number of consecutive identical readings required before a score
            change is accepted as real.
        cooldown_seconds:
            Minimum gap between two consecutive goal detections.
        """
        self._player_is_home = player_is_home
        self._confirm_frames = confirm_frames
        self._cooldown = cooldown_seconds

        # Last confirmed score
        self._home: Optional[int] = None
        self._away: Optional[int] = None

        # Candidate buffer – (home, away) → consecutive count
        self._candidate: Optional[tuple[int, int]] = None
        self._candidate_count: int = 0

        # Cooldown tracking
        self._last_goal_time: float = 0.0

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def confirmed_score(self) -> tuple[Optional[int], Optional[int]]:
        """Currently confirmed ``(home, away)`` score."""
        return self._home, self._away

    def update(
        self,
        home: Optional[int],
        away: Optional[int],
    ) -> Optional[GoalEvent]:
        """Feed a new detection reading; returns a :class:`GoalEvent` or ``None``.

        Parameters
        ----------
        home / away:
            Latest detected scores.  Pass ``None`` if detection failed for
            that side; the reading is discarded.
        """
        # Ignore incomplete reads
        if home is None or away is None:
            self._reset_candidate()
            return None

        # Initialise baseline on first valid reading
        if self._home is None:
            self._home, self._away = home, away
            return None

        candidate = (home, away)

        # Score unchanged from confirmed – reset the candidate buffer
        if candidate == (self._home, self._away):
            self._reset_candidate()
            return None

        # Accumulate candidate frames
        if candidate == self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = candidate
            self._candidate_count = 1

        if self._candidate_count < self._confirm_frames:
            return None

        # We have enough consecutive frames – check the change makes sense
        new_home, new_away = candidate

        if not self._is_valid_transition(new_home, new_away):
            # Likely a replay or UI artefact; keep the confirmed score
            self._reset_candidate()
            return None

        # Cooldown guard
        now = time.monotonic()
        if now - self._last_goal_time < self._cooldown:
            self._reset_candidate()
            return None

        # Determine which side scored
        event = self._build_event(new_home, new_away)

        # Commit new score
        self._home = new_home
        self._away = new_away
        self._last_goal_time = now
        self._reset_candidate()

        return event

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _reset_candidate(self) -> None:
        self._candidate = None
        self._candidate_count = 0

    def _is_valid_transition(self, new_home: int, new_away: int) -> bool:
        """Return True only if exactly one side scored one goal."""
        assert self._home is not None and self._away is not None
        home_diff = new_home - self._home
        away_diff = new_away - self._away
        # Allow exactly one goal on exactly one side
        return (home_diff == 1 and away_diff == 0) or (
            home_diff == 0 and away_diff == 1
        )

    def _build_event(self, new_home: int, new_away: int) -> GoalEvent:
        assert self._home is not None and self._away is not None
        home_scored = new_home > self._home

        if self._player_is_home:
            side = GoalSide.PLAYER if home_scored else GoalSide.OPPONENT
        else:
            side = GoalSide.OPPONENT if home_scored else GoalSide.PLAYER

        return GoalEvent(
            side=side,
            home_score=new_home,
            away_score=new_away,
            home_scored=home_scored,
        )
