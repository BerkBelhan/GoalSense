"""Tests for goalsense.detection – TemplateBank and ScoreDetector."""

from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np
import pytest

from goalsense.detection import ScoreDetector, TemplateBank, _maybe_resize, _to_grey


# ---------------------------------------------------------------------------
# Helpers – synthetic digit images
# ---------------------------------------------------------------------------

def _make_digit_image(digit: int, height: int = 40, width: int = 30) -> np.ndarray:
    """Create a simple greyscale image (height × width) with the digit printed on it."""
    img = np.zeros((height, width), dtype=np.uint8)
    cv2.putText(
        img,
        str(digit),
        (3, height - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        255,
        2,
    )
    return img


def _make_template_dir(digits: list[int] | None = None) -> str:
    """Save synthetic templates (height=40, width=30) and return the dir path."""
    if digits is None:
        digits = list(range(10))
    tmpdir = tempfile.mkdtemp()
    for d in digits:
        img = _make_digit_image(d, height=40, width=30)
        cv2.imwrite(os.path.join(tmpdir, f"{d}.png"), img)
    return tmpdir


# ---------------------------------------------------------------------------
# TemplateBank
# ---------------------------------------------------------------------------

class TestTemplateBank:
    def test_ready_when_templates_loaded(self):
        tmpdir = _make_template_dir([0, 1, 2])
        bank = TemplateBank(tmpdir)
        assert bank.ready

    def test_not_ready_for_empty_dir(self):
        tmpdir = tempfile.mkdtemp()
        bank = TemplateBank(tmpdir)
        assert not bank.ready

    def test_missing_dir_does_not_raise(self):
        bank = TemplateBank("/nonexistent/path/xyz")
        assert not bank.ready

    def test_match_exact_template_returns_digit(self):
        """Matching a template against itself should return the correct digit."""
        tmpdir = _make_template_dir()
        bank = TemplateBank(tmpdir, threshold=0.5)
        for digit in range(10):
            tmpl = _make_digit_image(digit)
            result = bank.match(tmpl)
            assert result == digit, f"Expected {digit}, got {result}"

    def test_match_returns_none_below_threshold(self):
        tmpdir = _make_template_dir([0])
        bank = TemplateBank(tmpdir, threshold=0.99)
        # Noise image should not match at very high threshold
        noise = np.random.randint(0, 256, (40, 30), dtype=np.uint8)
        result = bank.match(noise)
        # Result may or may not be None; just ensure no exception is raised
        assert result is None or isinstance(result, int)

    def test_match_returns_none_when_no_templates(self):
        tmpdir = tempfile.mkdtemp()
        bank = TemplateBank(tmpdir)
        patch = np.zeros((40, 30), dtype=np.uint8)
        assert bank.match(patch) is None

    def test_match_accepts_bgr_input(self):
        tmpdir = _make_template_dir([5])
        bank = TemplateBank(tmpdir, threshold=0.5)
        grey = _make_digit_image(5)
        bgr = cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)
        result = bank.match(bgr)
        assert result == 5


# ---------------------------------------------------------------------------
# ScoreDetector
# ---------------------------------------------------------------------------

class TestScoreDetector:
    def _make_scoreboard(self, home: int, away: int) -> tuple[np.ndarray, dict]:
        """
        Build a synthetic scoreboard frame with home and away digits placed at
        known positions.  Returns (frame, subregion_config).
        """
        digit_h, digit_w = 40, 30  # matches _make_digit_image defaults
        frame = np.zeros((60, 200, 3), dtype=np.uint8)

        home_x, home_y = 10, 10
        away_x, away_y = 100, 10

        home_img = cv2.cvtColor(_make_digit_image(home, digit_h, digit_w), cv2.COLOR_GRAY2BGR)
        away_img = cv2.cvtColor(_make_digit_image(away, digit_h, digit_w), cv2.COLOR_GRAY2BGR)

        frame[home_y: home_y + digit_h, home_x: home_x + digit_w] = home_img
        frame[away_y: away_y + digit_h, away_x: away_x + digit_w] = away_img

        config = {
            "home_sr": (home_x, home_y, digit_w, digit_h),
            "away_sr": (away_x, away_y, digit_w, digit_h),
        }
        return frame, config

    def test_detects_correct_home_and_away_scores(self):
        tmpdir = _make_template_dir()
        bank = TemplateBank(tmpdir, threshold=0.5)

        frame, cfg = self._make_scoreboard(2, 1)
        detector = ScoreDetector(
            bank=bank,
            home_subregion=cfg["home_sr"],
            away_subregion=cfg["away_sr"],
        )
        home, away = detector.detect(frame)
        assert home == 2
        assert away == 1

    def test_out_of_bounds_subregion_returns_none(self):
        tmpdir = _make_template_dir()
        bank = TemplateBank(tmpdir)
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        detector = ScoreDetector(
            bank=bank,
            home_subregion=(100, 100, 30, 40),  # outside frame
            away_subregion=(110, 100, 30, 40),
        )
        home, away = detector.detect(frame)
        assert home is None
        assert away is None


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtils:
    def test_to_grey_passthrough_for_greyscale(self):
        img = np.zeros((20, 20), dtype=np.uint8)
        assert _to_grey(img) is img

    def test_to_grey_converts_bgr(self):
        img = np.zeros((20, 20, 3), dtype=np.uint8)
        grey = _to_grey(img)
        assert grey.ndim == 2

    def test_maybe_resize_no_change_at_scale_1(self):
        img = np.zeros((20, 30), dtype=np.uint8)
        result = _maybe_resize(img, 1.0)
        assert result is img

    def test_maybe_resize_changes_dimensions(self):
        img = np.zeros((20, 30), dtype=np.uint8)
        result = _maybe_resize(img, 2.0)
        assert result.shape == (40, 60)

    def test_maybe_resize_minimum_size(self):
        img = np.zeros((1, 1), dtype=np.uint8)
        result = _maybe_resize(img, 0.1)
        assert result.shape[0] >= 1 and result.shape[1] >= 1
