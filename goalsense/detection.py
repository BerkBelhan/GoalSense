"""
detection.py – scoreboard digit recognition via OpenCV template matching.

Architecture
------------
* :class:`TemplateBank` loads ``0.png`` … ``9.png`` from a directory and
  exposes a :meth:`match` method that returns the best-matching digit for a
  given image patch.
* :class:`ScoreDetector` uses a :class:`TemplateBank` plus two configured
  sub-regions to read the home and away scores from a scoreboard frame.

Template images
---------------
Place one greyscale (or colour – we convert internally) PNG per digit named
``0.png`` through ``9.png`` inside the ``templates/`` directory.  Run
``calibrate.py`` to capture them interactively from the live game.
"""

from __future__ import annotations

import os
from typing import Optional

import cv2
import numpy as np


class TemplateBank:
    """Loads digit templates and performs normalised cross-correlation matching."""

    def __init__(self, templates_dir: str, threshold: float = 0.75) -> None:
        """
        Parameters
        ----------
        templates_dir:
            Directory containing ``0.png`` – ``9.png``.
        threshold:
            Minimum ``cv2.TM_CCOEFF_NORMED`` score required to accept a match.
        """
        self._threshold = threshold
        self._templates: dict[int, list[np.ndarray]] = {}
        self._load(templates_dir)

    # ------------------------------------------------------------------ #
    # Loading                                                              #
    # ------------------------------------------------------------------ #

    def _load(self, directory: str) -> None:
        for digit in range(10):
            path = os.path.join(directory, f"{digit}.png")
            if not os.path.exists(path):
                continue
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            self._templates[digit] = [img]

    @property
    def ready(self) -> bool:
        """True when at least one template has been loaded."""
        return bool(self._templates)

    # ------------------------------------------------------------------ #
    # Matching                                                             #
    # ------------------------------------------------------------------ #

    def match(
        self,
        patch: np.ndarray,
        scales: list[float] | None = None,
    ) -> Optional[int]:
        """Return the digit (0–9) that best matches *patch*, or ``None``.

        Parameters
        ----------
        patch:
            Greyscale image to match against the templates.
        scales:
            Optional list of scale multipliers applied to each template before
            matching.  Helps handle minor size discrepancies.
        """
        if not self._templates:
            return None

        if scales is None:
            scales = [1.0]

        grey = _to_grey(patch)

        best_score = -1.0
        best_digit: Optional[int] = None

        for digit, templates in self._templates.items():
            for tmpl in templates:
                for scale in scales:
                    candidate = _maybe_resize(tmpl, scale)
                    th, tw = candidate.shape[:2]
                    ph, pw = grey.shape[:2]
                    if th > ph or tw > pw:
                        continue
                    result = cv2.matchTemplate(grey, candidate, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val > best_score:
                        best_score = max_val
                        best_digit = digit

        if best_score >= self._threshold:
            return best_digit
        return None


class ScoreDetector:
    """Reads the home and away score from a scoreboard frame."""

    def __init__(
        self,
        bank: TemplateBank,
        home_subregion: tuple[int, int, int, int],
        away_subregion: tuple[int, int, int, int],
        scales: list[float] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        bank:
            Pre-loaded :class:`TemplateBank`.
        home_subregion:
            ``(x, y, w, h)`` of the home-score digit area relative to the
            scoreboard frame top-left.
        away_subregion:
            Same for the away score.
        scales:
            Scale factors forwarded to :meth:`TemplateBank.match`.
        """
        self._bank = bank
        self._home_sr = home_subregion
        self._away_sr = away_subregion
        self._scales = scales or [1.0]

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def detect(self, frame: np.ndarray) -> tuple[Optional[int], Optional[int]]:
        """Return ``(home_score, away_score)`` or ``(None, None)`` on failure.

        Parameters
        ----------
        frame:
            Full scoreboard BGR frame captured by :class:`~goalsense.capture.ScreenCapture`.
        """
        home = self._read_digit(frame, self._home_sr)
        away = self._read_digit(frame, self._away_sr)
        return home, away

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _read_digit(
        self,
        frame: np.ndarray,
        subregion: tuple[int, int, int, int],
    ) -> Optional[int]:
        x, y, w, h = subregion
        fh, fw = frame.shape[:2]
        # Clamp to frame boundaries
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(fw, x + w)
        y2 = min(fh, y + h)
        if x2 <= x1 or y2 <= y1:
            return None
        patch = frame[y1:y2, x1:x2]
        return self._bank.match(patch, scales=self._scales)


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _to_grey(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _maybe_resize(img: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return img
    h, w = img.shape[:2]
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
