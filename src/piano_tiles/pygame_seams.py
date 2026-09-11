"""Concrete pygame-backed implementations of the orchestrator's seams.

`Clock` and `EventSource` are declared as Protocols in `game.py`; the
`MusicPlayer` Protocol lives in `piano_tiles.music`. These are the production
implementations that read from / write to real pygame. Tests substitute
scripted stand-ins (see `tests/scripted.py`).
"""

from typing import Any

import pygame


class PygameClock:
    """Wall-clock backed by `pygame.time.Clock`. `tick()` returns seconds since previous tick."""

    def __init__(self, fps: int = 60) -> None:
        self._fps = fps
        self._clock = pygame.time.Clock()

    def tick(self) -> float:
        return self._clock.tick(self._fps) / 1000.0


class PygameEventSource:
    """Raw event source backed by `pygame.event.get()`."""

    def poll(self) -> list[Any]:
        return pygame.event.get()


class PygameMusicPlayer:
    """Background-music seam backed by `pygame.mixer.music`.

    Callers must have initialized pygame first (`pygame.init()` is enough; it
    initializes the mixer subsystem too). The constructor is idempotent: if
    the mixer is already initialized it leaves it alone, so it's safe to
    construct multiple instances in the same process (e.g. across tests).

    `play()` loads then plays in one call — that's how `pygame.mixer.music`
    is meant to be driven. `loop=True` maps to pygame's `-1` (loop forever);
    `loop=False` maps to `0` (one-shot). Volume is clamped to `0.0..1.0` to
    match the abstract `MusicPlayer` contract; pygame's own `set_volume`
    silently saturates anyway but explicit clamping keeps `volume` queries
    predictable.
    """

    def __init__(self) -> None:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()

    def play(self, path: str, *, loop: bool = True) -> None:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1 if loop else 0)

    def pause(self) -> None:
        pygame.mixer.music.pause()

    def resume(self) -> None:
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def set_volume(self, level: float) -> None:
        pygame.mixer.music.set_volume(max(0.0, min(1.0, level)))

    @property
    def is_playing(self) -> bool:
        return bool(pygame.mixer.music.get_busy())

    @property
    def volume(self) -> float:
        return float(pygame.mixer.music.get_volume())
