"""Headless end-to-end smoke for the Game orchestrator.

These tests drive the full pipeline (InputAdapter → StateMachine → Spawner →
HitDetector → ScoreKeeper → Renderer) against a dummy SDL surface — no real
window. They verify both a successful hit path and the miss-loses path.
"""

import random
from unittest import mock

import pygame
import pytest

from piano_tiles.components.main_menu import song_option_box
from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.components.renderer import Renderer
from piano_tiles.config import HIT_ZONE_BOTTOM, HIT_ZONE_TOP, LANE_KEYS, RESTART_KEY
from piano_tiles.game import Game
from piano_tiles.models.state import State
from piano_tiles.pygame_seams import PygameClock, PygameEventSource
from tests.scripted import ScriptedClock, ScriptedEvents, click, keydown

pytestmark = pytest.mark.ui


def _fast_phase_schedule() -> PhaseSchedule:
    """One long phase with a fast fall speed so the smoke tests time deterministically."""
    return PhaseSchedule(phases=(Phase(speed=6_000.0, duration=9_999.0),))


def _first_song_click() -> click:
    """A click on the first song's box — selects it on the main menu."""
    x, y, w, h = song_option_box(0)
    return click(x + w // 2, y + h // 2)


def _frame(clock: ScriptedClock, events: ScriptedEvents, dt: float, batch) -> None:
    clock.dts.append(dt)
    events.batches.append(batch)


@pytest.fixture
def smoke_game(headless_surface):
    clock = ScriptedClock()
    events = ScriptedEvents()
    game = Game(
        clock=clock,
        events=events,
        surface=headless_surface,
        renderer=Renderer(),
        rng=random.Random(1),  # avoids same-lane consecutive spawns in the test window
        phase_schedule=_fast_phase_schedule(),
    )
    return game, clock, events


def test_full_flow_start_spawn_hit_scores(smoke_game) -> None:
    """Boot, start, drop a tile into the zone, press its lane → score 1."""
    game, clock, events = smoke_game

    _frame(clock, events, 0.0, [_first_song_click()])  # main menu → start screen
    game.step()
    assert game.state is State.MENU

    _frame(clock, events, 0.0, [keydown(RESTART_KEY)])
    game.step()
    assert game.state is State.PLAYING

    _frame(clock, events, 0.15, [])  # spawns + the oldest tile reaches the zone
    game.step()
    assert game.state is State.PLAYING

    in_zone = next(
        (
            t
            for t in game.tiles
            if t.is_hittable and t.overlaps_band(HIT_ZONE_TOP, HIT_ZONE_BOTTOM)
        ),
        None,
    )
    assert in_zone is not None, "expected at least one tile in the hit zone"

    _frame(clock, events, 0.0, [keydown(LANE_KEYS[in_zone.lane])])
    game.step()
    assert game.state is State.PLAYING
    assert game.score == 1


def test_full_flow_missed_tile_ends_game(smoke_game) -> None:
    """Boot, start, no input — a tile falls past the zone and the game ends."""
    game, clock, events = smoke_game

    _frame(clock, events, 0.0, [_first_song_click()])  # select song
    _frame(clock, events, 0.0, [keydown(RESTART_KEY)])  # start
    _frame(clock, events, 0.1, [])  # spawn
    _frame(clock, events, 0.5, [])  # tile flies past the zone

    for _ in range(4):
        game.step()
    assert game.state is State.GAME_OVER


# ---- pygame-backed seams ---------------------------------------------------


def test_pygame_clock_tick_returns_nonnegative_seconds(headless_surface) -> None:
    """The real pygame clock seam returns a non-negative float on each tick."""
    clock = PygameClock(fps=240)
    dt = clock.tick()
    assert isinstance(dt, float)
    assert dt >= 0.0


def test_pygame_event_source_poll_returns_posted_events(headless_surface) -> None:
    """Polling drains pygame's event queue and returns the queued events."""
    pygame.event.clear()
    posted = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_d})
    pygame.event.post(posted)
    source = PygameEventSource()
    drained = source.poll()
    assert any(
        ev.type == pygame.KEYDOWN and getattr(ev, "key", None) == pygame.K_d
        for ev in drained
    )


def test_render_flips_display_when_drawing_to_the_real_display() -> None:
    """Rendering to the live display surface must call `pygame.display.flip()`.

    Without flip(), the back buffer is never presented and the window stays
    black — even though drawing succeeded. This regression test pins the call.
    """
    pygame.display.init()
    surface = pygame.display.set_mode((480, 720))
    try:
        clock = ScriptedClock([0.0])
        events = ScriptedEvents([[]])
        game = Game(
            clock=clock,
            events=events,
            surface=surface,
            renderer=Renderer(),
            rng=random.Random(1),  # avoids same-lane consecutive spawns in the test window
            phase_schedule=_fast_phase_schedule(),
        )
        with mock.patch.object(pygame.display, "flip") as flip_mock:
            game.step()
        assert flip_mock.call_count == 1
    finally:
        pygame.display.quit()


def test_render_does_not_flip_when_drawing_to_an_offscreen_surface(headless_surface) -> None:
    """Rendering to a plain off-screen Surface (not the display) must NOT flip.

    Off-screen surfaces aren't presented — calling flip() either does nothing
    or, with no display set, raises. The render path guards against this.
    """
    clock = ScriptedClock([0.0])
    events = ScriptedEvents([[]])
    game = Game(
        clock=clock,
        events=events,
        surface=headless_surface,
        renderer=Renderer(),
        rng=random.Random(1),  # avoids same-lane consecutive spawns in the test window
        phase_schedule=_fast_phase_schedule(),
    )
    with mock.patch.object(pygame.display, "flip") as flip_mock:
        game.step()
    assert flip_mock.call_count == 0
