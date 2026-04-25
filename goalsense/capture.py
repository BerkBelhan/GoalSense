"""
capture.py – screen region capture using mss.

Provides a thin wrapper around mss so the rest of the application never
imports mss directly; swapping the backend later only requires changes here.
"""

from __future__ import annotations

import numpy as np
import mss
import mss.tools


class ScreenCapture:
    """Captures a fixed screen region on every call to :meth:`grab`."""

    def __init__(self, region: dict[str, int]) -> None:
        """
        Parameters
        ----------
        region:
            A dict with keys ``top``, ``left``, ``width``, ``height`` (pixels).
            This is the same format accepted by :class:`mss.mss`.
        """
        self._region = region
        self._sct = mss.mss()

    def grab(self) -> np.ndarray:
        """Return the captured region as a BGR ``uint8`` NumPy array."""
        raw = self._sct.grab(self._region)
        # mss returns BGRA; drop the alpha channel to get BGR (OpenCV default)
        frame = np.array(raw, dtype=np.uint8)[:, :, :3]
        return frame

    def close(self) -> None:
        """Release the underlying mss context."""
        self._sct.close()

    # ------------------------------------------------------------------ #
    # Context-manager support                                              #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "ScreenCapture":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
