"""
audio.py – non-blocking audio playback via pygame.mixer.

Only pygame.mixer is initialised (not the full pygame display), keeping the
footprint minimal.  Playback runs in pygame's internal audio thread so the
detection loop is never blocked.
"""

from __future__ import annotations

import os
import threading
import logging

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Plays audio files without blocking the calling thread."""

    def __init__(self, volume: float = 1.0) -> None:
        """
        Parameters
        ----------
        volume:
            Playback volume from 0.0 (silent) to 1.0 (full).
        """
        self._volume = max(0.0, min(1.0, volume))
        self._lock = threading.Lock()
        self._initialised = False
        self._init_mixer()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def play(self, path: str) -> None:
        """Start playing *path* asynchronously.

        Does nothing (and logs a warning) if the file does not exist or if the
        mixer could not be initialised.
        """
        if not path:
            return
        if not os.path.isfile(path):
            logger.warning("Audio file not found: %s", path)
            return
        if not self._initialised:
            logger.warning("pygame.mixer not initialised – skipping playback")
            return

        # Run in a background thread to avoid any GIL / blocking risk
        threading.Thread(target=self._play_file, args=(path,), daemon=True).start()

    def stop(self) -> None:
        """Stop any currently playing sound."""
        if not self._initialised:
            return
        try:
            import pygame
            pygame.mixer.music.stop()
        except pygame.error as exc:
            logger.debug("stop() error: %s", exc)

    def close(self) -> None:
        """Quit the mixer and release resources."""
        if self._initialised:
            try:
                import pygame
                pygame.mixer.quit()
            except pygame.error as exc:
                logger.debug("close() error: %s", exc)
            self._initialised = False

    # ------------------------------------------------------------------ #
    # Context-manager support                                              #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "AudioPlayer":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _init_mixer(self) -> None:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self._volume)
            self._initialised = True
            logger.debug("pygame.mixer initialised (volume=%.2f)", self._volume)
        except pygame.error as exc:
            logger.warning("Could not initialise pygame.mixer: %s", exc)
        except ImportError as exc:
            logger.warning("pygame not installed: %s", exc)

    def _play_file(self, path: str) -> None:
        with self._lock:
            try:
                import pygame
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except pygame.error as exc:
                logger.error("Playback error (%s): %s", path, exc)
