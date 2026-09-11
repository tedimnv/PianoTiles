"""Scripted seams shared by Game-orchestrator tests.

These were previously triplicated across `test_game.py`, `test_full_flow.py`,
and `test_game_smoke.py`. Centralizing them keeps the fakes in one place so
behavior tweaks land everywhere at once.
"""

from typing import Any

import pygame

from piano_tiles.components.input_adapter import key_code


class FakeEvent:
    """Duck-typed stand-in for `pygame.event.Event`."""

    def __init__(
        self,
        type_: int,
        key: int | None = None,
        pos: tuple[int, int] | None = None,
    ) -> None:
        self.type = type_
        self.key = key
        self.pos = pos


def keydown(name: str) -> FakeEvent:
    """Build a fake KEYDOWN event for the given key name (e.g. "d", "escape")."""
    return FakeEvent(pygame.KEYDOWN, key_code(name))


def click(x: int, y: int) -> FakeEvent:
    """Build a fake left mouse-button-down event at (x, y)."""
    return FakeEvent(pygame.MOUSEBUTTONDOWN, pos=(x, y))


def keyup(name: str) -> FakeEvent:
    """Build a fake KEYUP event for the given key name (long-tile release)."""
    return FakeEvent(pygame.KEYUP, key_code(name))


def window_close() -> FakeEvent:
    """Build a fake pygame.QUIT (window-close) event."""
    return FakeEvent(pygame.QUIT)


class ScriptedClock:
    """Clock seam driven by a queue of dt values; returns 0.0 when empty."""

    def __init__(self, dts: list[float] | None = None) -> None:
        self.dts: list[float] = list(dts or [])

    def tick(self) -> float:
        return self.dts.pop(0) if self.dts else 0.0


class ScriptedEvents:
    """Event source seam driven by a queue of per-frame event batches."""

    def __init__(self, batches: list[list[Any]] | None = None) -> None:
        self.batches: list[list[Any]] = list(batches or [])

    def poll(self) -> list[Any]:
        return self.batches.pop(0) if self.batches else []


class ScriptedMusicPlayer:
    """MusicPlayer seam that records every call and tracks playback state.

    Tests assert on `calls` to verify which state transitions trigger which
    audio actions. `is_playing` and `volume` reflect what a real player would
    report after the same call sequence.

    Call log entries:
      - play(path, loop=True)  -> ("play", path, loop)
      - pause()                -> ("pause",)
      - resume()               -> ("resume",)
      - stop()                 -> ("stop",)
      - set_volume(level)      -> ("set_volume", level)  # original input, unclamped
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self._state: str = "idle"  # idle | playing | paused | stopped
        self._volume: float = 1.0

    def play(self, path: str, *, loop: bool = True) -> None:
        self.calls.append(("play", path, loop))
        self._state = "playing"

    def pause(self) -> None:
        self.calls.append(("pause",))
        if self._state == "playing":
            self._state = "paused"

    def resume(self) -> None:
        self.calls.append(("resume",))
        if self._state == "paused":
            self._state = "playing"

    def stop(self) -> None:
        self.calls.append(("stop",))
        if self._state in {"playing", "paused"}:
            self._state = "stopped"

    def set_volume(self, level: float) -> None:
        self.calls.append(("set_volume", level))
        self._volume = max(0.0, min(1.0, level))

    @property
    def is_playing(self) -> bool:
        return self._state == "playing"

    @property
    def volume(self) -> float:
        return self._volume
