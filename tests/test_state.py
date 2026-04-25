"""Tests for goalsense.state – score state management and goal attribution."""

from __future__ import annotations

import time
import pytest

from goalsense.state import GoalEvent, GoalSide, ScoreState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _feed(state: ScoreState, home: int, away: int, n: int = 1):
    """Feed the same reading *n* times and return the last result."""
    event = None
    for _ in range(n):
        event = state.update(home, away)
    return event


def _make_state(
    player_is_home: bool = True,
    confirm_frames: int = 3,
    cooldown_seconds: float = 0.0,
) -> ScoreState:
    return ScoreState(
        player_is_home=player_is_home,
        confirm_frames=confirm_frames,
        cooldown_seconds=cooldown_seconds,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInitialisation:
    def test_no_event_on_first_reading(self):
        state = _make_state()
        assert state.update(0, 0) is None

    def test_confirmed_score_set_on_first_reading(self):
        state = _make_state()
        state.update(0, 0)
        assert state.confirmed_score == (0, 0)

    def test_none_reading_ignored(self):
        state = _make_state()
        assert state.update(None, None) is None
        assert state.confirmed_score == (None, None)

    def test_partial_none_ignored(self):
        state = _make_state()
        state.update(0, 0)
        result = state.update(1, None)
        assert result is None
        assert state.confirmed_score == (0, 0)


# ---------------------------------------------------------------------------
# Confirmation logic
# ---------------------------------------------------------------------------

class TestConfirmation:
    def test_goal_not_fired_before_confirm_frames(self):
        state = _make_state(confirm_frames=3)
        state.update(0, 0)
        assert state.update(1, 0) is None  # frame 1
        assert state.update(1, 0) is None  # frame 2

    def test_goal_fired_at_confirm_frames(self):
        state = _make_state(confirm_frames=3)
        state.update(0, 0)
        _feed(state, 1, 0, n=2)
        event = state.update(1, 0)  # 3rd frame
        assert event is not None
        assert event.home_score == 1
        assert event.away_score == 0

    def test_reset_when_candidate_changes(self):
        state = _make_state(confirm_frames=3)
        state.update(0, 0)
        state.update(1, 0)  # start candidate (1, 0)
        state.update(0, 1)  # different candidate – resets count
        result = state.update(0, 1)  # only 2nd frame for (0, 1)
        assert result is None  # not confirmed yet


# ---------------------------------------------------------------------------
# Goal attribution
# ---------------------------------------------------------------------------

class TestGoalAttribution:
    def test_home_goal_player_is_home(self):
        state = _make_state(player_is_home=True, confirm_frames=1)
        state.update(0, 0)
        event = state.update(1, 0)
        assert event.side == GoalSide.PLAYER

    def test_away_goal_player_is_home(self):
        state = _make_state(player_is_home=True, confirm_frames=1)
        state.update(0, 0)
        event = state.update(0, 1)
        assert event.side == GoalSide.OPPONENT

    def test_away_goal_player_is_away(self):
        state = _make_state(player_is_home=False, confirm_frames=1)
        state.update(0, 0)
        event = state.update(0, 1)
        assert event.side == GoalSide.PLAYER

    def test_home_goal_player_is_away(self):
        state = _make_state(player_is_home=False, confirm_frames=1)
        state.update(0, 0)
        event = state.update(1, 0)
        assert event.side == GoalSide.OPPONENT

    def test_event_score_values(self):
        state = _make_state(confirm_frames=1)
        state.update(2, 1)
        event = state.update(3, 1)
        assert event.home_score == 3
        assert event.away_score == 1

    def test_event_score_str(self):
        state = _make_state(confirm_frames=1)
        state.update(0, 0)
        event = state.update(1, 0)
        assert event.score_str == "1 – 0"


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

class TestInvalidTransitions:
    def test_score_decrease_ignored(self):
        state = _make_state(confirm_frames=1)
        state.update(2, 2)
        result = state.update(1, 2)
        assert result is None
        assert state.confirmed_score == (2, 2)

    def test_both_scores_increase_ignored(self):
        state = _make_state(confirm_frames=1)
        state.update(0, 0)
        result = state.update(1, 1)
        assert result is None

    def test_score_jump_of_two_ignored(self):
        state = _make_state(confirm_frames=1)
        state.update(0, 0)
        result = state.update(2, 0)
        assert result is None

    def test_confirmed_score_unchanged_after_invalid(self):
        state = _make_state(confirm_frames=1)
        state.update(1, 0)
        state.update(3, 0)  # invalid jump
        assert state.confirmed_score == (1, 0)


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_second_goal_blocked_during_cooldown(self):
        state = _make_state(confirm_frames=1, cooldown_seconds=60.0)
        state.update(0, 0)
        assert state.update(1, 0) is not None  # first goal
        result = state.update(2, 0)
        assert result is None  # blocked by cooldown

    def test_goal_allowed_after_cooldown(self, monkeypatch):
        state = _make_state(confirm_frames=1, cooldown_seconds=1.0)
        state.update(0, 0)
        state.update(1, 0)
        # Advance time past cooldown
        t = time.monotonic() + 2.0
        monkeypatch.setattr(time, "monotonic", lambda: t)
        event = state.update(2, 0)
        assert event is not None


# ---------------------------------------------------------------------------
# Multiple goals in sequence
# ---------------------------------------------------------------------------

class TestSequentialGoals:
    def test_sequential_goals_recorded_correctly(self):
        state = _make_state(confirm_frames=1, cooldown_seconds=0.0)
        state.update(0, 0)
        e1 = state.update(1, 0)
        e2 = state.update(2, 0)
        e3 = state.update(2, 1)
        assert e1.home_score == 1 and e1.away_score == 0
        assert e2.home_score == 2 and e2.away_score == 0
        assert e3.home_score == 2 and e3.away_score == 1
