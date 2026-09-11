"""Background-music seam and policy.

This module owns everything about *how the game talks to its soundtrack*,
split into three cohesive pieces:

- ``MusicPlayer`` — the Protocol (the seam). The orchestrator depends on this,
  not on pygame. Production wiring lives in ``piano_tiles.pygame_seams``; tests
  inject a scripted stand-in (see ``tests/scripted.py``).
- ``SilentMusicPlayer`` — a no-op implementation, the default when no audio is
  wired in, so the bulk of the test suite can boot a ``Game`` without audio.
- ``MusicDirector`` — the *policy*: which state-machine event does what to the
  music. The orchestrator tells the director about each event and stays out of
  the audio decisions entirely.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from piano_tiles.components.state_machine import Event
from piano_tiles.config import BGM_GAME_OVER_VOLUME, BGM_PATH


class MusicPlayer(Protocol):
    """Background-music seam. Production wiring lives in ``pygame_seams``."""

    def play(self, path: str, *, loop: bool = True) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def set_volume(self, level: float) -> None: ...
    @property
    def is_playing(self) -> bool: ...
    @property
    def volume(self) -> float: ...


class SilentMusicPlayer:
    """No-op music player used as the default when no audio is wired in.

    Accepts every call without raising and never reports playback. Used so the
    bulk of the test suite can boot a ``Game`` without caring about audio.
    """

    def play(self, path: str, *, loop: bool = True) -> None:
        return None

    def pause(self) -> None:
        return None

    def resume(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def set_volume(self, level: float) -> None:
        return None

    @property
    def is_playing(self) -> bool:
        return False

    @property
    def volume(self) -> float:
        return 0.0


class MusicDirector:
    """Translates game state-machine events into ``MusicPlayer`` calls.

    Owns the audio *policy* (which transition does what to the music); the
    wrapped ``MusicPlayer`` owns the *mechanism* (talking to the backend).
    Keeping the two apart leaves the orchestrator free of audio decisions and
    lets this policy be unit-tested against a scripted player.

    The event→action map is data-driven (mirroring ``StateMachine``'s own
    transition table) so ``react_to`` stays a single lookup. Events not in the
    map — ``WRONG_KEY``, ``SELECT_SONG``, and anything fired by phase
    transitions — leave the music untouched by design: music keeps playing at
    full volume during the brief red flash and across phase boundaries, ducking
    only once ``DIE`` lands the player in ``GAME_OVER``. ``TO_MAIN_MENU`` stops
    the track — the player is back at song selection and a fresh pick loads its
    own track via :meth:`use_track`.
    """

    def __init__(
        self,
        player: MusicPlayer,
        *,
        bgm_path: object = BGM_PATH,
        game_over_volume: float = BGM_GAME_OVER_VOLUME,
    ) -> None:
        self._player = player
        self._bgm_path = str(bgm_path)
        self._game_over_volume = game_over_volume
        self._actions: dict[Event, Callable[[], None]] = {
            Event.START: self._play_from_start,
            Event.RESTART: self._play_from_start,
            Event.PAUSE: player.pause,
            Event.RESUME: player.resume,
            Event.DIE: self._duck,
            Event.TO_MAIN_MENU: player.stop,
            Event.QUIT: player.stop,
        }

    def use_track(self, path: object) -> None:
        """Set the track the next START/RESTART will play. Called when the
        player picks a song on the main menu."""
        self._bgm_path = str(path)

    def react_to(self, event: Event) -> None:
        action = self._actions.get(event)
        if action is not None:
            action()

    def _play_from_start(self) -> None:
        """START / RESTART: full volume, then (re)start the track from the top."""
        self._player.set_volume(1.0)
        self._player.play(self._bgm_path, loop=True)

    def _duck(self) -> None:
        """DIE: duck to the game-over level but keep the track playing."""
        self._player.set_volume(self._game_over_volume)
