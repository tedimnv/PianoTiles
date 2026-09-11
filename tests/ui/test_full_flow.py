"""Phase 5 — full-flow UI smoke tests.

Verifies the whole lifecycle works end-to-end against a real Renderer and a
headless surface: Menu → Playing → GameOver → Playing → Quit, and that a
restart resets the score and clears leftover tiles.
"""

import random

import pytest

from piano_tiles.components.main_menu import song_option_box
from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.components.renderer import Renderer
from piano_tiles.config import (
    HIT_ZONE_BOTTOM,
    HIT_ZONE_TOP,
    LANE_KEYS,
    QUIT_KEY,
    RESTART_KEY,
    WRONG_KEY_FLASH_DURATION,
)
from piano_tiles.game import Game
from piano_tiles.models.state import State
from tests.scripted import ScriptedClock, ScriptedEvents, click, keydown

pytestmark = pytest.mark.ui


def _first_song_click() -> click:
    x, y, w, h = song_option_box(0)
    return click(x + w // 2, y + h // 2)


def _queue(clock: ScriptedClock, events: ScriptedEvents, dt: float, batch) -> None:
    clock.dts.append(dt)
    events.batches.append(batch)


def _select_song_then_play(game, clock, events) -> None:
    """Drive MAIN_MENU → MENU → PLAYING via a song click then SPACE."""
    _queue(clock, events, 0.0, [_first_song_click()])
    game.step()
    assert game.state is State.MENU
    _queue(clock, events, 0.0, [keydown(RESTART_KEY)])
    game.step()
    assert game.state is State.PLAYING


@pytest.fixture
def lifecycle_game(headless_surface):
    """Game with fast spawning and high fall speed for deterministic timing."""
    clock = ScriptedClock()
    events = ScriptedEvents()
    game = Game(
        clock=clock,
        events=events,
        surface=headless_surface,
        renderer=Renderer(),
        rng=random.Random(1),  # avoids same-lane consecutive spawns in the test window
        phase_schedule=PhaseSchedule(
            phases=(Phase(speed=6_000.0, duration=9_999.0),),
        ),
    )
    return game, clock, events


def test_full_flow_menu_playing_game_over_playing_quits_via_run(lifecycle_game) -> None:
    """Run drives the whole lifecycle to QUIT and terminates without intervention."""
    game, clock, events = lifecycle_game
    assert game.state is State.MAIN_MENU

    _queue(clock, events, 0.0, [_first_song_click()])   # MAIN_MENU → MENU
    _queue(clock, events, 0.0, [keydown(RESTART_KEY)])  # MENU → PLAYING
    _queue(clock, events, 0.1, [])                       # spawn first tile
    _queue(clock, events, 0.5, [])                       # tile flies past zone → GAME_OVER
    _queue(clock, events, 0.0, [keydown(RESTART_KEY)])  # GAME_OVER → PLAYING
    _queue(clock, events, 0.0, [keydown(QUIT_KEY)])     # PLAYING → QUIT

    game.run()

    assert game.state is State.QUIT


def test_no_input_first_spawned_tile_passes_zone_and_ends_game(lifecycle_game) -> None:
    """With no input after start, a tile eventually falls past the zone → GAME_OVER."""
    game, clock, events = lifecycle_game

    _select_song_then_play(game, clock, events)
    assert game.tiles == ()

    _queue(clock, events, 0.5, [])  # plenty of time — some tile flies past the zone
    game.step()
    assert game.state is State.GAME_OVER


def test_pressing_lane_with_no_tile_in_zone_ends_game_via_dying(lifecycle_game) -> None:
    """A lane press with an empty hit zone enters DYING, then GAME_OVER after the flash."""
    game, clock, events = lifecycle_game

    _select_song_then_play(game, clock, events)
    assert game.tiles == ()  # nothing has spawned yet

    _queue(clock, events, 0.0, [keydown(LANE_KEYS[0])])
    game.step()
    assert game.state is State.DYING

    _queue(clock, events, WRONG_KEY_FLASH_DURATION + 0.01, [])
    game.step()
    assert game.state is State.GAME_OVER


def test_restart_after_game_over_resets_score_and_clears_tiles(lifecycle_game) -> None:
    """After GAME_OVER → RESTART, the new run starts with score 0 and no leftover tiles."""
    game, clock, events = lifecycle_game

    # Boot into PLAYING (select song, then start).
    _select_song_then_play(game, clock, events)

    # Drop a tile into the zone and press its lane to score 1.
    _queue(clock, events, 0.15, [])  # spawns + the oldest tile reaches the zone
    game.step()
    in_zone = next(
        (
            t
            for t in game.tiles
            if t.is_hittable and t.overlaps_band(HIT_ZONE_TOP, HIT_ZONE_BOTTOM)
        ),
        None,
    )
    assert in_zone is not None

    _queue(clock, events, 0.0, [keydown(LANE_KEYS[in_zone.lane])])
    game.step()
    assert game.score == 1
    assert game.state is State.PLAYING

    # Let the field fall past untouched → GAME_OVER, leaving tiles around.
    _queue(clock, events, 0.2, [])
    game.step()
    assert game.state is State.GAME_OVER

    # Restart. The new run must look pristine.
    _queue(clock, events, 0.0, [keydown(RESTART_KEY)])
    game.step()

    assert game.state is State.PLAYING
    assert game.score == 0
    assert game.tiles == ()
