"""Unit tests for Game's music wiring — asserts which state transitions
trigger which `MusicPlayer` calls. Pure unit-level: uses ScriptedMusicPlayer
so no real audio is involved."""

import random
from typing import Any

import pytest

from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.components.state_machine import Event
from piano_tiles.config import (
    BGM_GAME_OVER_VOLUME,
    BGM_PATH,
    HIT_ZONE_BOTTOM,
    HIT_ZONE_TOP,
    LANE_KEYS,
    PAUSE_KEY,
    QUIT_KEY,
    RESTART_KEY,
    WRONG_KEY_FLASH_DURATION,
)
from piano_tiles.game import Game
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile
from tests.scripted import (
    ScriptedClock,
    ScriptedEvents,
    ScriptedMusicPlayer,
    keydown,
    window_close,
)

pytestmark = pytest.mark.unit


# ---- helpers --------------------------------------------------------------


def _single_phase(speed: float = 300.0, duration: float = 9_999.0) -> PhaseSchedule:
    return PhaseSchedule(phases=(Phase(speed=speed, duration=duration),))


def _two_phase() -> PhaseSchedule:
    return PhaseSchedule(
        phases=(
            Phase(speed=240.0, duration=2.0),
            Phase(speed=480.0, duration=2.0),
        ),
    )


def make_game(
    *,
    events: list[list[Any]] | None = None,
    dts: list[float] | None = None,
    phase_schedule: PhaseSchedule | None = None,
    select_song: bool = True,
) -> tuple[Game, ScriptedMusicPlayer]:
    music = ScriptedMusicPlayer()
    game = Game(
        clock=ScriptedClock(dts),
        events=ScriptedEvents(events),
        rng=random.Random(0),
        phase_schedule=phase_schedule or _single_phase(),
        music=music,
    )
    if select_song:
        # Advance MAIN_MENU → MENU so the scripted SPACE can START. Selecting
        # the (only) song sets the same default track, and selection itself
        # emits no music calls — so the call logs below are unaffected.
        game._state_machine.process(Event.SELECT_SONG)
    return game, music


def _start_call_log() -> list[tuple[Any, ...]]:
    """Convenience: the exact two-call sequence that `_fire(START|RESTART)` emits."""
    return [("set_volume", 1.0), ("play", str(BGM_PATH), True)]


# ---- menu / idle ----------------------------------------------------------


def test_booting_game_records_no_music_calls() -> None:
    """The menus are silent — no music until the player presses Start."""
    _, music = make_game(select_song=False)
    assert music.calls == []
    assert music.is_playing is False


def test_idling_in_menu_across_multiple_frames_records_no_music_calls() -> None:
    """Ticking from the main menu keeps the music untouched."""
    game, music = make_game(
        events=[[], [], []], dts=[0.016, 0.016, 0.016], select_song=False
    )
    game.step()
    game.step()
    game.step()
    assert music.calls == []


# ---- start ----------------------------------------------------------------


def test_start_records_set_volume_then_play_in_order() -> None:
    game, music = make_game(events=[[keydown(RESTART_KEY)]])
    game.step()
    assert music.calls == _start_call_log()
    assert music.is_playing is True


def test_only_first_frame_triggers_music_then_silence_during_play() -> None:
    """Ticking inside PLAYING after START does not emit additional music calls."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [], [], []],
        dts=[0.016, 0.016, 0.016, 0.016],
    )
    game.step()
    baseline = list(music.calls)
    game.step()
    game.step()
    game.step()
    assert music.calls == baseline


# ---- pause / resume -------------------------------------------------------


def test_pause_records_exactly_one_pause_call() -> None:
    game, music = make_game(events=[[keydown(RESTART_KEY)], [keydown(PAUSE_KEY)]])
    game.step()
    pre = len(music.calls)
    game.step()
    assert music.calls[pre:] == [("pause",)]
    assert music.is_playing is False


def test_resume_after_pause_records_exactly_one_resume_call() -> None:
    game, music = make_game(
        events=[
            [keydown(RESTART_KEY)],
            [keydown(PAUSE_KEY)],
            [keydown(PAUSE_KEY)],
        ],
    )
    game.step()
    game.step()
    pre = len(music.calls)
    game.step()
    assert music.calls[pre:] == [("resume",)]
    assert music.is_playing is True


def test_rapid_pause_resume_records_four_calls_in_order_no_extras() -> None:
    """Edge: tapping pause four times records pause/resume/pause/resume —
    no spurious play/stop/set_volume slipping in."""
    game, music = make_game(
        events=[
            [keydown(RESTART_KEY)],
            [keydown(PAUSE_KEY)],
            [keydown(PAUSE_KEY)],
            [keydown(PAUSE_KEY)],
            [keydown(PAUSE_KEY)],
        ],
    )
    for _ in range(5):
        game.step()
    tail = music.calls[len(_start_call_log()):]
    assert tail == [("pause",), ("resume",), ("pause",), ("resume",)]


# ---- die: missed-tile path ------------------------------------------------


def _set_up_missed_tile(game: Game) -> None:
    """Seed a tile already past the hit zone so the next tick fires DIE."""
    game._tiles.append(
        Tile(lane=0, y=float(HIT_ZONE_BOTTOM + 5), height=10.0, speed=300.0)
    )


def test_die_via_missed_tile_records_set_volume_no_stop() -> None:
    game, music = make_game(events=[[keydown(RESTART_KEY)], []], dts=[0.0, 0.016])
    game.step()
    _set_up_missed_tile(game)
    pre = len(music.calls)
    game.step()
    assert music.calls[pre:] == [("set_volume", BGM_GAME_OVER_VOLUME)]
    assert music.is_playing is True
    assert music.volume == BGM_GAME_OVER_VOLUME
    assert game.state is State.GAME_OVER


# ---- die: wrong-key path (PLAYING → DYING → GAME_OVER) --------------------


def test_wrong_key_alone_does_not_touch_music_during_flash() -> None:
    """During the brief red flash (DYING state), music stays at full volume."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [keydown(LANE_KEYS[0])]],
        dts=[0.0, 0.016],
    )
    game.step()
    pre = len(music.calls)
    game.step()
    assert game.state is State.DYING
    assert music.calls[pre:] == []  # no music event on WRONG_KEY
    assert music.is_playing is True
    assert music.volume == 1.0


def test_die_after_dying_flash_records_set_volume_only() -> None:
    """When the dying flash ends and DIE fires, music ducks but keeps playing."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [keydown(LANE_KEYS[0])], []],
        dts=[0.0, 0.016, WRONG_KEY_FLASH_DURATION + 0.01],
    )
    game.step()  # START
    game.step()  # wrong key → DYING
    pre = len(music.calls)
    game.step()  # flash ends → DIE → GAME_OVER
    assert music.calls[pre:] == [("set_volume", BGM_GAME_OVER_VOLUME)]
    assert music.is_playing is True
    assert game.state is State.GAME_OVER


# ---- game-over: ticking does nothing more ---------------------------------


def test_ticking_during_game_over_does_not_emit_music_calls() -> None:
    game, music = make_game(events=[[keydown(RESTART_KEY)], [], [], []], dts=[0.0, 0.016, 0.016, 0.016])
    game.step()
    _set_up_missed_tile(game)
    game.step()  # PLAYING → GAME_OVER, ducks
    baseline = list(music.calls)
    game.step()
    game.step()
    assert music.calls == baseline
    assert music.is_playing is True
    assert music.volume == BGM_GAME_OVER_VOLUME


# ---- restart --------------------------------------------------------------


def test_restart_after_die_records_set_volume_then_play() -> None:
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [], [keydown(RESTART_KEY)]],
        dts=[0.0, 0.016, 0.016],
    )
    game.step()
    _set_up_missed_tile(game)
    game.step()  # DIE → set_volume(0.3)
    pre = len(music.calls)
    game.step()  # RESTART → set_volume(1.0), play
    assert music.calls[pre:] == _start_call_log()
    assert music.volume == 1.0
    assert music.is_playing is True


def test_die_then_restart_call_log_has_no_stop_between() -> None:
    """The tail of the log around the DIE→RESTART boundary is
    set_volume(0.3) → set_volume(1.0) → play(...).  No stop() slips in."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [], [keydown(RESTART_KEY)]],
        dts=[0.0, 0.016, 0.016],
    )
    game.step()
    _set_up_missed_tile(game)
    game.step()
    game.step()
    tail = music.calls[-3:]
    assert tail == [
        ("set_volume", BGM_GAME_OVER_VOLUME),
        ("set_volume", 1.0),
        ("play", str(BGM_PATH), True),
    ]


# ---- phase break ----------------------------------------------------------


def test_phase_boundary_does_not_touch_music() -> None:
    """Regression: crossing a phase boundary (banner pops up) emits no music
    events. Music keeps playing through the boundary unchanged."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], []],
        dts=[0.0, 2.05],
        phase_schedule=_two_phase(),
    )
    game.step()  # START
    baseline = list(music.calls)
    game.step()  # crosses phase boundary; banner starts
    assert game.phase_number == 2
    assert game._banner.is_active
    assert music.calls == baseline, "no music events on phase boundary"


def test_die_during_active_banner_still_ducks_volume() -> None:
    """Edge: DIE-ing while the phase banner is showing still ducks volume —
    the audio decision is independent of the banner timer."""
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [], []],
        dts=[0.0, 2.05, 0.016],
        phase_schedule=_two_phase(),
    )
    game.step()  # START
    game.step()  # cross into phase 2; banner is up
    assert game._banner.is_active
    _set_up_missed_tile(game)
    pre = len(music.calls)
    game.step()  # miss → DIE during banner
    assert music.calls[pre:] == [("set_volume", BGM_GAME_OVER_VOLUME)]
    assert game.state is State.GAME_OVER


# ---- restart-then-die edge case -------------------------------------------


def test_restart_then_immediate_die_records_full_sequence_with_no_stop() -> None:
    """Edge: from GAME_OVER, press Space (RESTART) then on the same frame's
    next tick fail (missed tile). Tail of log: set_volume(1.0), play(...),
    set_volume(0.3) — no stop() between."""
    game, music = make_game(
        events=[
            [keydown(RESTART_KEY)],  # START
            [],                       # miss
            [keydown(RESTART_KEY)],  # RESTART
            [],                       # miss again
        ],
        dts=[0.0, 0.016, 0.016, 0.016],
    )
    game.step()  # START
    _set_up_missed_tile(game)
    game.step()  # DIE → GAME_OVER
    game.step()  # RESTART → PLAYING
    _set_up_missed_tile(game)
    pre = len(music.calls)
    game.step()  # DIE again
    assert music.calls[pre:] == [("set_volume", BGM_GAME_OVER_VOLUME)]
    # Combined RESTART → DIE tail (no stop between):
    assert music.calls[-3:] == [
        ("set_volume", 1.0),
        ("play", str(BGM_PATH), True),
        ("set_volume", BGM_GAME_OVER_VOLUME),
    ]


# ---- quit -----------------------------------------------------------------


def test_quit_from_menu_records_exactly_one_stop() -> None:
    game, music = make_game(events=[[keydown(QUIT_KEY)]])
    game.step()
    assert music.calls == [("stop",)]
    assert game.state is State.QUIT


def test_quit_from_playing_records_exactly_one_stop() -> None:
    game, music = make_game(events=[[keydown(RESTART_KEY)], [keydown(QUIT_KEY)]])
    game.step()
    pre = len(music.calls)
    game.step()
    assert music.calls[pre:] == [("stop",)]


def test_quit_from_paused_records_exactly_one_stop() -> None:
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [keydown(PAUSE_KEY)], [keydown(QUIT_KEY)]],
    )
    game.step()
    game.step()
    pre = len(music.calls)
    game.step()
    assert music.calls[pre:] == [("stop",)]


def test_quit_from_game_over_records_exactly_one_stop() -> None:
    game, music = make_game(
        events=[[keydown(RESTART_KEY)], [], [keydown(QUIT_KEY)]],
        dts=[0.0, 0.016, 0.016],
    )
    game.step()
    _set_up_missed_tile(game)
    game.step()  # DIE
    pre = len(music.calls)
    game.step()  # QUIT
    assert music.calls[pre:] == [("stop",)]


def test_window_close_event_triggers_stop() -> None:
    game, music = make_game(events=[[window_close()]])
    game.step()
    assert music.calls == [("stop",)]


# ---- default silent player -----------------------------------------------


def test_game_defaults_to_silent_music_player_when_none_given() -> None:
    """Existing tests that don't pass `music` continue to work — Game wraps
    a SilentMusicPlayer that swallows every call. Confirms the default arg
    contract is the one Step 1 promised."""
    game = Game(
        clock=ScriptedClock([0.0]),
        events=ScriptedEvents([[keydown(RESTART_KEY)]]),
        rng=random.Random(0),
        phase_schedule=_single_phase(),
    )
    game._state_machine.process(Event.SELECT_SONG)  # reach the start screen
    game.step()  # would explode if music were None and not guarded
    assert game.state is State.PLAYING
