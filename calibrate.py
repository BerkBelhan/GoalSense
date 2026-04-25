"""
calibrate.py – interactive calibration tool for GoalSense.

What it does
------------
1. Captures a single screenshot of the full monitor (or the configured
   scoreboard region).
2. Lets you draw a rectangle with the mouse to select the scoreboard region
   and prints the resulting config values.
3. Within the selected region, lets you draw boxes around individual digits
   (0–9) and saves them as templates in the ``templates/`` directory.

Run this script before starting the main detection loop:

    python calibrate.py

Controls
--------
* Draw a rectangle by clicking and dragging.
* Press ENTER to confirm a selection.
* Press ESC to cancel / exit the current step.
* Press 'r' to reset the current selection.
"""

from __future__ import annotations

import os
import sys

import cv2
import mss
import numpy as np

TEMPLATES_DIR = "templates"


def _grab_full_screen() -> np.ndarray:
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        raw = sct.grab(monitor)
    frame = np.array(raw, dtype=np.uint8)[:, :, :3]
    return frame


# ---------------------------------------------------------------------------
# Mouse-drawing helper
# ---------------------------------------------------------------------------

class _RectSelector:
    """Simple mouse-driven rectangle selector."""

    def __init__(self, window: str) -> None:
        self._win = window
        self.rect: tuple[int, int, int, int] | None = None
        self._start: tuple[int, int] | None = None
        self._end: tuple[int, int] | None = None
        self._drawing = False

    def attach(self) -> None:
        cv2.setMouseCallback(self._win, self._on_mouse)

    def _on_mouse(self, event: int, x: int, y: int, *_: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self._start = (x, y)
            self._end = (x, y)
            self._drawing = True
        elif event == cv2.EVENT_MOUSEMOVE and self._drawing:
            self._end = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self._end = (x, y)
            self._drawing = False
            if self._start and self._end:
                x1 = min(self._start[0], self._end[0])
                y1 = min(self._start[1], self._end[1])
                x2 = max(self._start[0], self._end[0])
                y2 = max(self._start[1], self._end[1])
                if x2 - x1 > 2 and y2 - y1 > 2:
                    self.rect = (x1, y1, x2 - x1, y2 - y1)

    def reset(self) -> None:
        """Clear the current selection."""
        self.rect = None
        self._start = None
        self._end = None

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        if self._start and self._end:
            cv2.rectangle(display, self._start, self._end, (0, 255, 0), 2)
        return display


# ---------------------------------------------------------------------------
# Step 1 – select scoreboard region
# ---------------------------------------------------------------------------

def select_region(screenshot: np.ndarray) -> dict[str, int] | None:
    """Let the user draw a rectangle over the scoreboard area."""
    # Downscale if the monitor is very large so it fits on screen
    h, w = screenshot.shape[:2]
    scale = min(1.0, 1600 / w, 900 / h)
    display_size = (round(w * scale), round(h * scale))
    small = cv2.resize(screenshot, display_size)

    win = "GoalSense Calibration – Draw the scoreboard region, then press ENTER"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, *display_size)
    selector = _RectSelector(win)
    selector.attach()

    print("\n[Step 1]  Draw a rectangle around the scoreboard region.")
    print("  ENTER = confirm | ESC = skip | r = reset\n")

    while True:
        overlay = selector.draw_overlay(small)
        cv2.imshow(win, overlay)
        key = cv2.waitKey(20) & 0xFF

        if key == 13:  # ENTER
            break
        if key == 27:  # ESC
            cv2.destroyWindow(win)
            return None
        if key == ord("r"):
            selector.reset()

    cv2.destroyWindow(win)

    if selector.rect is None:
        return None

    # Scale rect back to original resolution
    rx, ry, rw, rh = selector.rect
    region = {
        "top": round(ry / scale),
        "left": round(rx / scale),
        "width": round(rw / scale),
        "height": round(rh / scale),
    }
    return region


# ---------------------------------------------------------------------------
# Step 2 – capture digit templates
# ---------------------------------------------------------------------------

def capture_templates(scoreboard: np.ndarray) -> None:
    """For each digit 0–9, let the user draw a bounding box and save it."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    h, w = scoreboard.shape[:2]
    # Upscale small scoreboards so they're easier to work with
    scale = max(1.0, min(4.0, 200 / h, 600 / w))
    display_size = (round(w * scale), round(h * scale))
    big = cv2.resize(scoreboard, display_size, interpolation=cv2.INTER_CUBIC)

    print("\n[Step 2]  For each digit draw a bounding box, then press ENTER.")
    print("  ENTER = save template | ESC = skip digit | r = reset\n")

    for digit in range(10):
        win = f"GoalSense Calibration – Select digit  '{digit}'  (ENTER=save, ESC=skip, r=reset)"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, *display_size)
        selector = _RectSelector(win)
        selector.attach()

        while True:
            overlay = selector.draw_overlay(big)
            cv2.imshow(win, overlay)
            key = cv2.waitKey(20) & 0xFF

            if key == 13:  # ENTER
                break
            if key == 27:  # ESC
                print(f"  Skipped digit {digit}")
                break
            if key == ord("r"):
                selector.reset()

        cv2.destroyWindow(win)

        if key == 27 or selector.rect is None:
            continue

        rx, ry, rw, rh = selector.rect
        # Scale coords back to scoreboard resolution
        x1 = round(rx / scale)
        y1 = round(ry / scale)
        x2 = round((rx + rw) / scale)
        y2 = round((ry + rh) / scale)
        patch = scoreboard[y1:y2, x1:x2]
        grey = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY) if patch.ndim == 3 else patch
        out_path = os.path.join(TEMPLATES_DIR, f"{digit}.png")
        cv2.imwrite(out_path, grey)
        print(f"  Saved template for digit {digit} → {out_path}")


# ---------------------------------------------------------------------------
# Step 3 – select home / away digit sub-regions
# ---------------------------------------------------------------------------

def select_score_subregions(
    scoreboard: np.ndarray,
) -> tuple[tuple[int, int, int, int] | None, tuple[int, int, int, int] | None]:
    """Return (home_subregion, away_subregion) relative to scoreboard frame."""
    h, w = scoreboard.shape[:2]
    scale = max(1.0, min(4.0, 200 / h, 600 / w))
    display_size = (round(w * scale), round(h * scale))
    big = cv2.resize(scoreboard, display_size, interpolation=cv2.INTER_CUBIC)

    results: list[tuple[int, int, int, int] | None] = []

    for label in ("HOME score digit area", "AWAY score digit area"):
        win = f"GoalSense Calibration – Select {label}  (ENTER=confirm, ESC=skip)"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, *display_size)
        selector = _RectSelector(win)
        selector.attach()

        print(f"\n  Draw a box around the {label}, then press ENTER.")

        while True:
            overlay = selector.draw_overlay(big)
            cv2.imshow(win, overlay)
            key = cv2.waitKey(20) & 0xFF
            if key == 13:
                break
            if key == 27:
                break
            if key == ord("r"):
                selector.reset()

        cv2.destroyWindow(win)

        if key == 27 or selector.rect is None:
            results.append(None)
        else:
            rx, ry, rw, rh = selector.rect
            results.append((
                round(rx / scale),
                round(ry / scale),
                round(rw / scale),
                round(rh / scale),
            ))

    home_sr, away_sr = results[0], results[1]
    return home_sr, away_sr


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  GoalSense Calibration")
    print("=" * 60)

    screenshot = _grab_full_screen()

    # --- Step 1: scoreboard region ---
    region = select_region(screenshot)
    if region:
        print("\n[Config]  Copy these values into goalsense/config.py:\n")
        print(f"  SCOREBOARD_REGION = {region!r}")
        scoreboard = screenshot[
            region["top"]: region["top"] + region["height"],
            region["left"]: region["left"] + region["width"],
        ]
    else:
        print("\n  Scoreboard region step skipped – using full screenshot.")
        scoreboard = screenshot

    # --- Step 2: digit templates ---
    answer = input("\nCapture digit templates now? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        capture_templates(scoreboard)

    # --- Step 3: score sub-regions ---
    answer = input("\nSelect HOME / AWAY score sub-regions now? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        home_sr, away_sr = select_score_subregions(scoreboard)
        if home_sr:
            print(f"\n  HOME_SCORE_SUBREGION = {home_sr!r}")
        if away_sr:
            print(f"  AWAY_SCORE_SUBREGION = {away_sr!r}")
        print("\n  Copy the lines above into goalsense/config.py.")

    print("\nCalibration complete.  Run  python main.py  to start detection.")


if __name__ == "__main__":
    main()
