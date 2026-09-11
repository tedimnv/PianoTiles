"""Translates raw pygame events into game-level input events.

Pure-logic boundary: this is the only place outside `Renderer` and `Game`
that knows about `pygame`. Downstream consumers (Game, StateMachine) speak
in `InputEvent`s.

Lane keys produce both press (KEYDOWN → LANE_PRESS) and release (KEYUP →
LANE_RELEASE) events — long, merged tiles require the player to hold the
key, so the orchestrator needs both edges of the input. The control keys
(pause / restart / quit / menu) fire on KEYDOWN only. A mouse button press
becomes a CLICK carrying its position — the main menu hit-tests it against
the song boxes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

import pygame

from piano_tiles.config import (
    LANE_KEYS,
    MENU_KEY,
    PAUSE_KEY,
    QUIT_KEY,
    RESTART_KEY,
)


class InputEventKind(Enum):
    LANE_PRESS = "lane_press"
    LANE_RELEASE = "lane_release"
    PAUSE = "pause"
    RESTART = "restart"
    MENU = "menu"
    QUIT = "quit"
    CLICK = "click"


@dataclass(frozen=True)
class InputEvent:
    kind: InputEventKind
    lane: int | None = None
    pos: tuple[int, int] | None = None  # set only for CLICK


def key_code(name: str) -> int:
    """Resolve a key name to a pygame key constant.

    pygame uses ``K_<lowercase>`` for letters / digits (e.g. ``K_d``) and
    ``K_<UPPERCASE>`` for named keys (e.g. ``K_ESCAPE``). Try both.
    """
    for attr in (f"K_{name.lower()}", f"K_{name.upper()}"):
        if hasattr(pygame, attr):
            return getattr(pygame, attr)
    raise ValueError(f"key name must resolve to a pygame key, got {name!r}")


class InputAdapter:
    def __init__(
        self,
        lane_keys: tuple[str, ...] = LANE_KEYS,
        pause_key: str = PAUSE_KEY,
        restart_key: str = RESTART_KEY,
        quit_key: str = QUIT_KEY,
        menu_key: str = MENU_KEY,
    ) -> None:
        self._keydown_map: dict[int, InputEvent] = {}
        self._keyup_map: dict[int, InputEvent] = {}
        for lane_idx, name in enumerate(lane_keys):
            code = key_code(name)
            self._keydown_map[code] = InputEvent(
                InputEventKind.LANE_PRESS, lane=lane_idx
            )
            self._keyup_map[code] = InputEvent(
                InputEventKind.LANE_RELEASE, lane=lane_idx
            )
        self._keydown_map[key_code(pause_key)] = InputEvent(InputEventKind.PAUSE)
        self._keydown_map[key_code(restart_key)] = InputEvent(InputEventKind.RESTART)
        self._keydown_map[key_code(quit_key)] = InputEvent(InputEventKind.QUIT)
        self._keydown_map[key_code(menu_key)] = InputEvent(InputEventKind.MENU)

    def translate(self, raw_events: Iterable[Any]) -> list[InputEvent]:
        out: list[InputEvent] = []
        for ev in raw_events:
            translated = self._translate_one(ev)
            if translated is not None:
                out.append(translated)
        return out

    def _translate_one(self, ev: Any) -> InputEvent | None:
        if ev.type == pygame.QUIT:
            return InputEvent(InputEventKind.QUIT)
        if ev.type == pygame.KEYDOWN:
            return self._keydown_map.get(ev.key)
        if ev.type == pygame.KEYUP:
            return self._keyup_map.get(ev.key)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            return InputEvent(InputEventKind.CLICK, pos=tuple(ev.pos))
        return None
