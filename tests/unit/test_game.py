import random
from typing import Any

import pytest

from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.components.state_machine import Event, StateMachine
from piano_tiles.components.banner import BANNER_TOTAL_SECONDS
from piano_tiles.config import (
    DEFAULT_PALETTE,
    HIT_ZONE_BOTTOM,
    HIT_ZONE_TOP,
    LANE_KEYS,
    MINT_BLUSH,
    MENU_KEY,
    PAUSE_KEY,
    PEACH_SORBET,
    QUIT_KEY,
    RESTART_KEY,
    TILE_VISUAL_GAP_PX,
    WINDOW_H,
    WRONG_KEY_FLASH_DURATION,
)
from piano_tiles.game import Game
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile
from piano_tiles.components.main_menu import song_option_box
from tests.scripted import (
    ScriptedClock,
    ScriptedEvents,
    click,
    keydown,
    keyup,
    window_close,
)

pytestmark = pytest.mark.unit


# ---- helpers ---------------------------------------------------------------


def _single_phase_schedule(speed: float = 300.0, duration: float = 9_999.0) -> PhaseSchedule:
    """One long phase so phase boundaries don't fire during unit tests."""
    return PhaseSchedule(phases=(Phase(speed=speed, duration=duration),))


def make_game(
    *,
    events: list[list[Any]] | None = None,
    dts: list[float] | None = None,
    phase_schedule: PhaseSchedule | None = None,
    rng_seed: int = 0,
) -> Game:
    """Build a Game without renderer/surface (headless, no rendering)."""
    return Game(
        clock=ScriptedClock(dts),
        events=ScriptedEvents(events),
        rng=random.Random(rng_seed),
        phase_schedule=phase_schedule or _single_phase_schedule(),
    )


def first_song_click_pos() -> tuple[int, int]:
    """Centre of the first song's option box — a click that selects it."""
    x, y, w, h = song_option_box(0)
    return (x + w // 2, y + h // 2)


def force_menu(game: Game) -> None:
    """Advance MAIN_MENU → MENU (the 'press SPACE to start' screen)."""
    game._state_machine.process(Event.SELECT_SONG)


def force_playing(game: Game) -> None:
    game._state_machine.process(Event.SELECT_SONG)
    game._state_machine.process(Event.START)


# ---- initial state ---------------------------------------------------------


def test_initial_state_is_main_menu() -> None:
    assert make_game().state is State.MAIN_MENU


def test_initial_score_is_zero() -> None:
    assert make_game().score == 0


def test_initial_tiles_are_empty() -> None:
    assert make_game().tiles == ()


# ---- main menu → start screen ---------------------------------------------


def test_clicking_a_song_transitions_main_menu_to_menu() -> None:
    game = make_game(events=[[click(*first_song_click_pos())]])
    game.step()
    assert game.state is State.MENU


def test_clicking_a_song_records_the_selected_song() -> None:
    game = make_game(events=[[click(*first_song_click_pos())]])
    game.step()
    assert game.selected_song is not None
    assert game.selected_song.title == "Slow Dancing In The Dark"


def test_clicking_empty_space_in_main_menu_stays_in_main_menu() -> None:
    game = make_game(events=[[click(5, 5)]])  # well above the song boxes
    game.step()
    assert game.state is State.MAIN_MENU
    assert game.selected_song is None


# ---- per-song palette ------------------------------------------------------


def _song_click_pos(index: int) -> tuple[int, int]:
    x, y, w, h = song_option_box(index)
    return (x + w // 2, y + h // 2)


def test_palette_is_default_before_any_song_is_selected() -> None:
    assert make_game().palette is DEFAULT_PALETTE


def test_choosing_the_first_song_activates_its_palette() -> None:
    game = make_game(events=[[click(*_song_click_pos(0))]])
    game.step()
    assert game.selected_song.title == "Slow Dancing In The Dark"
    assert game.palette is MINT_BLUSH


def test_choosing_the_second_song_activates_its_palette() -> None:
    game = make_game(events=[[click(*_song_click_pos(1))]])
    game.step()
    assert game.selected_song.title == "Loose"
    assert game.palette is PEACH_SORBET


def test_snapshot_carries_the_active_palette() -> None:
    """The per-frame snapshot the renderer receives reflects the chosen song's
    palette, so the screen repaints in that theme."""
    game = make_game(events=[[click(*_song_click_pos(1))]])
    game.step()
    assert game._snapshot().palette is PEACH_SORBET


def test_start_key_in_main_menu_is_ignored() -> None:
    """SPACE does nothing until a song has been chosen."""
    game = make_game(events=[[keydown(RESTART_KEY)]])
    game.step()
    assert game.state is State.MAIN_MENU


# ---- start ----------------------------------------------------------------


def test_start_key_in_menu_transitions_to_playing() -> None:
    game = make_game(events=[[keydown(RESTART_KEY)]])
    force_menu(game)
    game.step()
    assert game.state is State.PLAYING


def test_lane_press_in_menu_is_ignored() -> None:
    game = make_game(events=[[keydown(LANE_KEYS[0])]])
    force_menu(game)
    game.step()
    assert game.state is State.MENU


def test_pause_in_menu_is_ignored() -> None:
    game = make_game(events=[[keydown(PAUSE_KEY)]])
    force_menu(game)
    game.step()
    assert game.state is State.MENU


# ---- scoring on hit -------------------------------------------------------


def test_correct_lane_press_in_zone_increments_score() -> None:
    game = make_game(events=[[keydown(LANE_KEYS[2])]])
    force_playing(game)
    game._tiles.append(
        Tile(lane=2, y=float(HIT_ZONE_TOP + 10), height=80.0, speed=300.0)
    )
    game.step()
    assert game.score == 1


def test_hit_keeps_short_tile_in_field_filled_with_green_overlay() -> None:
    """A short tile that's been hit stays in the active list (still falling,
    eventually culled off-screen) and gets its overlay grown to the tile's
    full height so it renders the same colour as a fully-held long tile."""
    game = make_game(events=[[keydown(LANE_KEYS[2])]])
    force_playing(game)
    short_tile = Tile(lane=2, y=float(HIT_ZONE_TOP + 10), height=80.0, speed=300.0)
    game._tiles.append(short_tile)
    game.step()
    assert short_tile in game.tiles
    assert short_tile.is_hit is True
    assert short_tile.held_amount == short_tile.original_height


def test_short_tile_hit_eventually_culled_off_screen() -> None:
    """After enough ticks the hit short tile's top passes WINDOW_H and the
    cull pass removes it — the field doesn't pile up indefinitely."""
    game = make_game()
    force_playing(game)
    short_tile = Tile(
        lane=2,
        y=float(HIT_ZONE_TOP + 10),
        height=80.0,
        speed=300.0,
        state="hit",
    )
    short_tile.held_amount = short_tile.original_height
    game._tiles.append(short_tile)
    # Run enough ticks to drive the tile past WINDOW_H.
    game._clock.dts.extend([0.5] * 10)
    game._events.batches.extend([[]] * 10)
    for _ in range(10):
        game.step()
    assert short_tile not in game.tiles


def test_hit_keeps_state_in_playing() -> None:
    game = make_game(events=[[keydown(LANE_KEYS[2])]])
    force_playing(game)
    game._tiles.append(
        Tile(lane=2, y=float(HIT_ZONE_TOP + 10), height=80.0, speed=300.0)
    )
    game.step()
    assert game.state is State.PLAYING


# ---- wrong-key flash + game-over -----------------------------------------


def test_wrong_lane_press_with_empty_field_enters_dying_state() -> None:
    """A lane press with no tile to hit triggers the red-flash transient."""
    game = make_game(events=[[keydown(LANE_KEYS[1])]])
    force_playing(game)
    game.step()
    assert game.state is State.DYING


def test_wrong_lane_press_spawns_a_phantom_in_the_pressed_lane() -> None:
    """The phantom mirrors the lane the player pressed (not the correct lane)."""
    game = make_game(events=[[keydown(LANE_KEYS[3])]])
    force_playing(game)
    correct = Tile(lane=0, y=float(HIT_ZONE_TOP + 10), height=80.0, speed=300.0)
    game._tiles.append(correct)
    game.step()
    phantom = game._dying.phantom
    assert phantom is not None
    assert phantom.lane == 3  # the pressed (wrong) lane
    assert phantom.y == correct.y  # mirrors the correct tile's height


def test_phantom_uses_hit_zone_center_when_no_correct_tile() -> None:
    """When no tile is in zone, the phantom lands at the centre of the hit zone."""
    game = make_game(events=[[keydown(LANE_KEYS[2])]])
    force_playing(game)
    game.step()
    phantom = game._dying.phantom
    assert phantom is not None
    expected_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) / 2 - phantom.height / 2
    assert phantom.y == pytest.approx(expected_y)


def test_dying_state_does_not_advance_tiles_or_spawn_new_ones() -> None:
    """Once dying, the field is frozen — the flash plays out without further gameplay."""
    game = make_game(events=[[keydown(LANE_KEYS[2])], []], dts=[0.0, 0.1])
    force_playing(game)
    falling = Tile(lane=0, y=100.0, height=80.0, speed=300.0)
    game._tiles.append(falling)
    game.step()  # WRONG_KEY → DYING
    assert game.state is State.DYING
    game.step()  # tick while DYING
    assert falling.y == 100.0


def test_dying_state_transitions_to_game_over_after_flash_duration() -> None:
    """The flash plays for WRONG_KEY_FLASH_DURATION seconds, then fires DIE."""
    game = make_game(
        events=[[keydown(LANE_KEYS[0])], []],
        dts=[0.0, WRONG_KEY_FLASH_DURATION + 0.01],
    )
    force_playing(game)
    game.step()  # enter DYING
    assert game.state is State.DYING
    game.step()  # tick past flash duration
    assert game.state is State.GAME_OVER
    assert game._dying.phantom is None  # cleaned up


def test_missed_tile_skips_dying_and_goes_straight_to_game_over() -> None:
    """A tile falling past the zone fires DIE directly — no red flash."""
    game = make_game(events=[[]], dts=[0.0])
    force_playing(game)
    game._tiles.append(
        Tile(lane=0, y=float(HIT_ZONE_BOTTOM + 5), height=10.0, speed=300.0)
    )
    game.step()
    assert game.state is State.GAME_OVER


def test_game_has_no_game_over_timer_field() -> None:
    """The fade was removed entirely — no timer to track on the orchestrator."""
    game = make_game()
    assert not hasattr(game, "_game_over_elapsed")


# ---- pause / resume -------------------------------------------------------


def test_pause_in_playing_transitions_to_paused() -> None:
    game = make_game(events=[[keydown(PAUSE_KEY)]])
    force_playing(game)
    game.step()
    assert game.state is State.PAUSED


def test_pause_in_paused_resumes_to_playing() -> None:
    game = make_game(events=[[keydown(PAUSE_KEY)], [keydown(PAUSE_KEY)]])
    force_playing(game)
    game.step()
    assert game.state is State.PAUSED
    game.step()
    assert game.state is State.PLAYING


def test_paused_tick_does_not_move_tiles_or_change_score() -> None:
    game = make_game(events=[[keydown(PAUSE_KEY)], []], dts=[0.0, 1.0])
    force_playing(game)
    tile = Tile(lane=1, y=100.0, height=80.0, speed=300.0)
    game._tiles.append(tile)
    game._score._score = 5  # type: ignore[attr-defined]
    game.step()  # PAUSE
    game.step()  # tick while paused
    assert game.state is State.PAUSED
    assert tile.y == 100.0
    assert game.score == 5


def test_pause_resume_preserves_positions_and_score() -> None:
    game = make_game(
        events=[[keydown(PAUSE_KEY)], [], [keydown(PAUSE_KEY)]],
        dts=[0.0, 5.0, 0.0],
    )
    force_playing(game)
    tile_a = Tile(lane=0, y=120.0, height=80.0, speed=300.0)
    tile_b = Tile(lane=2, y=200.0, height=80.0, speed=300.0)
    game._tiles.extend([tile_a, tile_b])
    game._score._score = 7  # type: ignore[attr-defined]

    game.step()  # PAUSE
    game.step()  # tick (1 frame) while PAUSED — no movement
    game.step()  # RESUME (dt=0.0 on the resume frame)

    assert game.state is State.PLAYING
    assert tile_a.y == 120.0
    assert tile_b.y == 200.0
    assert game.score == 7


# ---- restart from game over -----------------------------------------------


def test_restart_in_game_over_returns_to_playing() -> None:
    game = make_game(events=[[keydown(RESTART_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    assert game.state is State.GAME_OVER
    game.step()
    assert game.state is State.PLAYING


def test_restart_resets_score_to_zero() -> None:
    game = make_game(events=[[keydown(RESTART_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    game._score._score = 42  # type: ignore[attr-defined]
    game.step()
    assert game.score == 0


def test_restart_clears_leftover_tiles() -> None:
    game = make_game(events=[[keydown(RESTART_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    game._tiles.extend(
        [
            Tile(lane=0, y=100.0, height=80.0, speed=300.0),
            Tile(lane=1, y=50.0, height=80.0, speed=300.0),
        ]
    )
    game.step()
    assert game.tiles == ()


def test_restart_resets_spawner_timing() -> None:
    """After restart, the new spawner has elapsed=0 — same dt produces the same first spawn."""
    game = make_game(events=[[keydown(RESTART_KEY)]], dts=[0.0])
    force_playing(game)
    game._spawner.update(10.0)  # burn through many intervals
    assert game._spawner.elapsed == 10.0
    game._state_machine.process(Event.DIE)
    game.step()  # restart
    assert game._spawner.elapsed == 0.0


def test_restart_clears_banner_and_phantom() -> None:
    game = make_game(events=[[keydown(RESTART_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    game._banner.start(phase_number=3, initial_elapsed=0.5)
    game._dying.begin(Tile(lane=0, y=100.0, height=80.0, speed=300.0))
    game.step()
    assert game._banner.is_active is False
    assert game._banner.phase_number is None
    assert game._banner.elapsed is None
    assert game._dying.is_active is False
    assert game._dying.phantom is None
    assert game._dying.elapsed is None


# ---- return to main menu from game over -----------------------------------


def test_menu_key_in_game_over_returns_to_main_menu() -> None:
    game = make_game(events=[[keydown(MENU_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    assert game.state is State.GAME_OVER
    game.step()
    assert game.state is State.MAIN_MENU


def test_returning_to_main_menu_resets_score_and_tiles() -> None:
    game = make_game(events=[[keydown(MENU_KEY)]])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    game._score._score = 42  # type: ignore[attr-defined]
    game._tiles.append(Tile(lane=0, y=100.0, height=80.0, speed=300.0))
    game.step()
    assert game.state is State.MAIN_MENU
    assert game.score == 0
    assert game.tiles == ()


def test_menu_key_during_play_is_ignored() -> None:
    """M only returns to the menu from GAME_OVER, never mid-run."""
    game = make_game(events=[[keydown(MENU_KEY)]])
    force_playing(game)
    game.step()
    assert game.state is State.PLAYING


def test_song_click_with_no_position_is_a_silent_noop() -> None:
    """Defensive: a CLICK carrying no position never reaches the hit-test."""
    game = make_game()
    game._handle_song_click(None)
    assert game.state is State.MAIN_MENU
    assert game.selected_song is None


# ---- QUIT ------------------------------------------------------------------


@pytest.mark.parametrize(
    "pre",
    [
        [],
        [Event.SELECT_SONG],
        [Event.SELECT_SONG, Event.START],
        [Event.SELECT_SONG, Event.START, Event.PAUSE],
        [Event.SELECT_SONG, Event.START, Event.WRONG_KEY],
        [Event.SELECT_SONG, Event.START, Event.DIE],
    ],
    ids=[
        "from-main-menu",
        "from-menu",
        "from-playing",
        "from-paused",
        "from-dying",
        "from-game-over",
    ],
)
def test_quit_transitions_to_quit_state_from_anywhere(pre: list[Event]) -> None:
    game = make_game(events=[[keydown(QUIT_KEY)]])
    for ev in pre:
        game._state_machine.process(ev)
    game.step()
    assert game.state is State.QUIT


def test_window_close_event_quits_game() -> None:
    game = make_game(events=[[window_close()]])
    game.step()
    assert game.state is State.QUIT


def test_step_in_quit_state_is_a_noop() -> None:
    game = make_game(events=[[keydown(QUIT_KEY)], [keydown(LANE_KEYS[0])]])
    game.step()
    assert game.state is State.QUIT
    game.step()  # must not raise
    assert game.state is State.QUIT


def test_run_terminates_when_state_becomes_quit() -> None:
    game = make_game(events=[[keydown(QUIT_KEY)]])
    game.run()
    assert game.state is State.QUIT


def test_quit_event_short_circuits_remaining_inputs_in_same_batch() -> None:
    """After QUIT, the rest of the batch is ignored — no exceptions from invalid transitions."""
    game = make_game(events=[[keydown(QUIT_KEY), keydown(LANE_KEYS[0])]])
    game.step()
    assert game.state is State.QUIT


# ---- per-frame tile flow ---------------------------------------------------


def test_tick_moves_existing_tiles_down() -> None:
    game = make_game(events=[[]], dts=[0.5])
    force_playing(game)
    tile = Tile(lane=0, y=10.0, height=20.0, speed=200.0)
    game._tiles.append(tile)
    game.step()
    assert tile.y == pytest.approx(10.0 + 200.0 * 0.5)


def test_spawner_produces_new_tiles_during_play() -> None:
    fast_phase = PhaseSchedule(phases=(Phase(speed=4_000.0, duration=9_999.0),))
    game = make_game(events=[[]], dts=[0.6], phase_schedule=fast_phase)
    force_playing(game)
    game.step()
    assert len(game.tiles) >= 1


def test_tiles_below_window_bottom_are_culled() -> None:
    game = make_game(events=[[]], dts=[0.0])
    force_playing(game)
    above = Tile(lane=0, y=50.0, height=20.0, speed=300.0)
    below = Tile(lane=1, y=float(WINDOW_H + 10), height=20.0, speed=300.0, state="hit")
    game._tiles.extend([above, below])
    game.step()
    assert above in game.tiles
    assert below not in game.tiles


def test_menu_tick_does_not_spawn_or_move_tiles() -> None:
    game = make_game(events=[[]], dts=[1.0])
    force_menu(game)
    tile = Tile(lane=0, y=100.0, height=20.0, speed=300.0)
    game._tiles.append(tile)
    game.step()
    assert game.state is State.MENU
    assert tile.y == 100.0
    assert game.tiles == (tile,)


def test_game_over_tick_does_not_spawn_or_move_tiles() -> None:
    game = make_game(events=[[]], dts=[1.0])
    force_playing(game)
    game._state_machine.process(Event.DIE)
    tile = Tile(lane=0, y=100.0, height=20.0, speed=300.0)
    game._tiles.append(tile)
    game.step()
    assert game.state is State.GAME_OVER
    assert tile.y == 100.0


# ---- rendering seam -------------------------------------------------------


class _RecordingRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def render(self, state: Any, surface: Any) -> None:
        self.calls.append((state.state, surface))


def test_render_called_when_surface_and_renderer_provided() -> None:
    renderer = _RecordingRenderer()
    sentinel = object()
    game = Game(
        clock=ScriptedClock([0.0]),
        events=ScriptedEvents([[]]),
        surface=sentinel,
        renderer=renderer,
        rng=random.Random(0),
        phase_schedule=_single_phase_schedule(),
    )
    game.step()
    assert renderer.calls == [(State.MAIN_MENU, sentinel)]


def test_render_skipped_when_no_surface() -> None:
    """Without a surface there's nothing to draw on — orchestrator just ticks logic."""
    renderer = _RecordingRenderer()
    game = Game(
        clock=ScriptedClock([0.0]),
        events=ScriptedEvents([[]]),
        renderer=renderer,
        rng=random.Random(0),
        phase_schedule=_single_phase_schedule(),
    )
    game.step()
    assert renderer.calls == []


# ---- default-construction sanity check -----------------------------------


def test_uses_real_state_machine_and_score_keeper_by_default() -> None:
    """The default-constructed game wires real components — no silent stubbing."""
    game = make_game()
    assert isinstance(game._state_machine, StateMachine)


# ---- discrete phase transitions -------------------------------------------


def _two_phase_schedule() -> PhaseSchedule:
    return PhaseSchedule(
        phases=(
            Phase(speed=240.0, duration=2.0),
            Phase(speed=480.0, duration=2.0),
        ),
    )


def test_phase_boundary_swaps_spawner_speed_to_the_next_phase() -> None:
    """A tick that crosses a phase boundary immediately uses the new phase's speed."""
    game = make_game(events=[[]], dts=[2.05], phase_schedule=_two_phase_schedule())
    force_playing(game)
    game.step()
    assert game.state is State.PLAYING  # no break popup any more
    assert game.phase_number == 2
    assert game._spawner.speed == 480.0


def test_phase_boundary_starts_a_banner_for_the_new_phase() -> None:
    game = make_game(events=[[]], dts=[2.05], phase_schedule=_two_phase_schedule())
    force_playing(game)
    game.step()
    assert game._banner.phase_number == 2
    assert game._banner.elapsed == pytest.approx(0.05)


def test_banner_advances_on_subsequent_ticks_while_still_active() -> None:
    """Once the banner has started, additional ticks within its window grow elapsed."""
    game = make_game(
        events=[[], []],
        dts=[2.05, 0.5],
        phase_schedule=_two_phase_schedule(),
    )
    force_playing(game)
    game.step()  # phase 1 → phase 2; banner_elapsed = 0.05
    game.step()  # tick within the banner window
    assert game._banner.phase_number == 2
    assert game._banner.elapsed == pytest.approx(0.55)


def test_spawner_does_not_advance_while_banner_is_showing() -> None:
    """Regression: no new tiles spawn during the phase-change banner.

    Without this guard, fresh tiles spawn at the top of the screen and pass
    through the banner area while the banner is still animating. Pausing the
    spawner keeps the banner area free of new tiles — old tiles already in
    flight continue to fall and clear out naturally.
    """
    schedule = PhaseSchedule(
        phases=(
            Phase(speed=240.0, duration=2.0),
            Phase(speed=240.0, duration=9_999.0),
        ),
    )
    game = make_game(events=[[], []], dts=[2.05, 1.0], phase_schedule=schedule)
    force_playing(game)
    game.step()  # cross to phase 2; banner starts; spawner is fresh
    assert game._banner.phase_number == 2
    spawner_elapsed_at_boundary = game._spawner.elapsed
    # In particular, the leftover (0.05 s) did NOT advance the new spawner —
    # the banner was active by the time spawn would have run.
    assert spawner_elapsed_at_boundary == 0.0

    game.step()  # tick during banner — spawner stays paused
    assert game._banner.phase_number == 2  # banner still on screen
    assert game._spawner.elapsed == 0.0


def test_spawner_resumes_after_banner_ends() -> None:
    """Once the banner clears, spawning picks up again from a clean slate."""
    schedule = PhaseSchedule(
        phases=(
            Phase(speed=240.0, duration=2.0),
            Phase(speed=240.0, duration=9_999.0),
        ),
    )
    game = make_game(
        events=[[], [], []],
        dts=[2.05, 0.1, BANNER_TOTAL_SECONDS],
        phase_schedule=schedule,
    )
    force_playing(game)
    game.step()  # cross to phase 2; banner_elapsed=0.05, spawner.elapsed=0
    assert game._banner.phase_number == 2
    assert game._spawner.elapsed == 0.0
    game.step()  # mid-banner tick — no spawn
    assert game._banner.phase_number == 2
    assert game._spawner.elapsed == 0.0
    game.step()  # banner clears mid-tick; spawner resumes
    assert game._banner.phase_number is None
    assert game._spawner.elapsed > 0.0


def test_banner_clears_after_its_total_window_expires() -> None:
    game = make_game(
        events=[[], []],
        dts=[2.05, BANNER_TOTAL_SECONDS + 0.1],
        phase_schedule=_two_phase_schedule(),
    )
    force_playing(game)
    game.step()  # phase 1 → phase 2; banner starts at leftover=0.05
    assert game._banner.phase_number == 2
    game.step()  # tick past banner total — should clear
    assert game._banner.phase_number is None
    assert game._banner.elapsed is None


def test_phase_boundary_does_not_clear_falling_tiles() -> None:
    """Without the break popup, tiles in flight carry over — gameplay is continuous."""
    game = make_game(events=[[]], dts=[2.05], phase_schedule=_two_phase_schedule())
    force_playing(game)
    in_flight = Tile(lane=0, y=200.0, height=80.0, speed=240.0)
    game._tiles.append(in_flight)
    game.step()
    assert in_flight in game._tiles  # still around in phase 2


def test_no_phase_advance_on_the_final_phase_no_matter_how_long() -> None:
    """After the last phase's duration elapses, the game stays on phase N."""
    final_only = PhaseSchedule(phases=(Phase(speed=1.0, duration=1.0),))
    game = make_game(events=[[]], dts=[5.0], phase_schedule=final_only)
    force_playing(game)
    game.step()
    assert game.phase_number == 1
    assert game._banner.phase_number is None  # no banner because no advance


def test_restart_resets_phase_state_back_to_phase_one() -> None:
    schedule = _two_phase_schedule()
    game = make_game(
        events=[[], [keydown(RESTART_KEY)]],
        dts=[2.05, 0.0],
        phase_schedule=schedule,
    )
    force_playing(game)
    game.step()  # cross to phase 2
    assert game.phase_number == 2
    game._state_machine.process(Event.DIE)
    game.step()  # restart
    assert game.state is State.PLAYING
    assert game.phase_number == 1
    assert game._spawner.speed == 240.0


# ---- merging consecutive same-lane spawns --------------------------------


def _make_held_long_tile_in_zone(lane: int = 0, segments: int = 2) -> Tile:
    """Build a long tile straddling the hit zone for direct injection into Game._tiles."""
    height = segments * 180.0 + (segments - 1) * 1.0
    return Tile(
        lane=lane,
        y=float(HIT_ZONE_TOP + 10),
        height=height,
        speed=300.0,
        segments=segments,
    )


def _held_tile_with_overlay(
    *, lane: int, segments: int, held_fraction: float
) -> Tile:
    """Build a held long tile whose green overlay already covers
    `held_fraction` (∈ [0,1]) of its original height. The tile is positioned
    near the hit zone so it represents a believable mid-hold state."""
    original_height = segments * 180.0 + (segments - 1) * TILE_VISUAL_GAP_PX
    tile = Tile(
        lane=lane,
        y=float(HIT_ZONE_BOTTOM) - original_height,
        height=original_height,
        speed=300.0,
        segments=segments,
        held=True,
    )
    tile.grow_held(original_height * held_fraction)
    return tile


def test_two_consecutive_same_lane_spawns_merge_into_one_long_tile() -> None:
    """Inject the spawner output by hand to assert the merge contract directly."""
    game = make_game()
    force_playing(game)
    older = Tile(lane=2, y=1.0, height=180.0, speed=300.0)
    newer = Tile(lane=2, y=-180.0, height=180.0, speed=300.0)
    game._tiles.append(older)
    assert game._merge_into_previous(newer) is True
    assert len(game.tiles) == 1
    merged = game.tiles[0]
    assert merged.is_long is True
    assert merged.segments == 2
    assert merged.y == -180.0
    assert merged.bottom == pytest.approx(181.0)


def test_three_consecutive_same_lane_spawns_merge_into_one_three_segment_tile() -> None:
    game = make_game()
    force_playing(game)
    first = Tile(lane=1, y=2.0, height=180.0, speed=300.0)
    second = Tile(lane=1, y=-179.0, height=180.0, speed=300.0)
    third = Tile(lane=1, y=-360.0, height=180.0, speed=300.0)
    game._tiles.append(first)
    assert game._merge_into_previous(second) is True
    assert game._merge_into_previous(third) is True
    assert len(game.tiles) == 1
    assert game.tiles[0].segments == 3


def test_spawn_in_different_lane_is_appended_not_merged() -> None:
    game = make_game()
    force_playing(game)
    older = Tile(lane=0, y=1.0, height=180.0, speed=300.0)
    newer = Tile(lane=1, y=-180.0, height=180.0, speed=300.0)
    game._tiles.append(older)
    assert game._merge_into_previous(newer) is False


def test_spawn_does_not_merge_across_a_phase_speed_change() -> None:
    """At a phase boundary the old falling tile keeps its speed; the new one is
    faster. Merging them would mash two different fall speeds into one rect."""
    game = make_game()
    force_playing(game)
    slow = Tile(lane=0, y=1.0, height=180.0, speed=240.0)
    fast = Tile(lane=0, y=-180.0, height=180.0, speed=400.0)
    game._tiles.append(slow)
    assert game._merge_into_previous(fast) is False


def test_spawn_does_not_merge_with_a_far_apart_same_lane_tile() -> None:
    """An existing tile already mid-screen is too far from the top-of-screen new
    spawn — append a fresh tile, don't merge."""
    game = make_game()
    force_playing(game)
    far = Tile(lane=0, y=300.0, height=180.0, speed=300.0)
    new = Tile(lane=0, y=-180.0, height=180.0, speed=300.0)
    game._tiles.append(far)
    assert game._merge_into_previous(new) is False


# ---- pressing long tiles (hold + completion) -----------------------------


def test_press_on_a_short_tile_scores_immediately() -> None:
    """Short-tile press: score goes up by one and the tile stays on the field
    filled with the held overlay (so it shows the same green colour as a
    fully-held long tile while it rides off the bottom)."""
    game = make_game(events=[[keydown(LANE_KEYS[2])]])
    force_playing(game)
    short = Tile(lane=2, y=float(HIT_ZONE_TOP + 10), height=80.0, speed=300.0)
    game._tiles.append(short)
    game.step()
    assert game.score == 1
    assert short in game.tiles
    assert short.held_amount == short.original_height


def test_press_on_a_long_tile_starts_a_hold_without_scoring_yet() -> None:
    game = make_game(events=[[keydown(LANE_KEYS[0])]])
    force_playing(game)
    long_tile = _make_held_long_tile_in_zone(lane=0, segments=2)
    long_tile.held = False
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING
    assert game.score == 0
    assert long_tile.held is True


def test_press_on_a_long_tile_does_not_move_the_tile() -> None:
    """The press starts a hold but doesn't snap the tile to a new position —
    the green overlay will grow from the tile's actual press-time bottom."""
    game = make_game(events=[[keydown(LANE_KEYS[0])]])
    force_playing(game)
    long_tile = Tile(
        lane=0,
        y=float(HIT_ZONE_TOP + 30),
        height=361.0,
        speed=300.0,
        segments=2,
    )
    y_before, height_before = long_tile.y, long_tile.height
    game._tiles.append(long_tile)
    game.step()  # dt = 0 (no dts queued) so no fall this frame
    assert long_tile.y == y_before
    assert long_tile.height == height_before
    assert long_tile.held is True
    assert long_tile.held_amount == 0.0  # overlay starts at size 0


def test_tick_on_held_tile_grows_overlay_and_keeps_tile_falling() -> None:
    """While held, the tile falls AND the overlay grows by the same amount,
    so the green top stays anchored at the press-time tile.bottom."""
    game = make_game(events=[[]], dts=[0.1])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=3, held_fraction=0.0)
    bottom_at_press = long_tile.bottom
    game._tiles.append(long_tile)
    game.step()
    assert long_tile.held_amount == pytest.approx(30.0)
    assert long_tile.y == pytest.approx(long_tile.original_height * 0 + (long_tile.bottom - long_tile.original_height))
    # Held overlay top stays anchored where the tile.bottom was at press time:
    assert long_tile.bottom - long_tile.held_amount == pytest.approx(bottom_at_press)


def test_tick_grows_overlay_to_full_then_auto_completes() -> None:
    """One dt big enough to grow the overlay to the tile's full height —
    held tile auto-completes, scoring all segments, no DIE."""
    game = make_game(events=[[]], dts=[1.5])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=2, held_fraction=0.0)
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING
    assert game.score == 2
    assert long_tile.is_hit is True
    assert long_tile.held is False


def test_held_tile_is_never_marked_missed() -> None:
    """A held tile is not `is_hittable` (held tiles are excluded), so the
    miss-detection pass leaves it alone — the player is actively engaging."""
    game = make_game(events=[[]], dts=[0.5])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=3, held_fraction=0.0)
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING  # not GAME_OVER
    assert long_tile.held is True


def test_released_long_tile_continues_falling_with_frozen_overlay() -> None:
    """After release the tile keeps falling, but its green overlay size is
    frozen — the visible green stays attached to the tile (moves with it)
    and never grows past the tile's borders."""
    game = make_game(events=[[keyup(LANE_KEYS[0])], []], dts=[0.0, 0.1])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=3, held_fraction=0.5)
    game._tiles.append(long_tile)
    y_before = long_tile.y
    held_after_release = long_tile.held_amount  # captured before grow stops
    game.step()  # release
    assert long_tile.held is False
    overlay_at_release = long_tile.held_amount
    game.step()  # one more tick — tile falls but overlay stays the same
    assert long_tile.y > y_before
    assert long_tile.held_amount == pytest.approx(overlay_at_release)
    # The overlay never breaches the original tile's borders.
    assert long_tile.held_amount <= long_tile.original_height
    # We also captured pre-release held_amount only as a sanity prop; release
    # didn't artificially shrink it.
    assert overlay_at_release == pytest.approx(held_after_release)


def test_merge_skips_into_a_held_tile() -> None:
    """Held tiles are not is_hittable, so the merge guard naturally rejects
    them — no need to mash a fresh same-lane spawn onto a tile the player is
    actively interacting with."""
    game = make_game()
    force_playing(game)
    held = Tile(lane=0, y=520.0, height=180.0, speed=300.0, segments=2, held=True)
    new_spawn = Tile(lane=0, y=339.0, height=180.0, speed=300.0)
    game._tiles.append(held)
    assert game._merge_into_previous(new_spawn) is False


def test_held_long_tile_scores_segments_when_overlay_reaches_full_height() -> None:
    """Once the held overlay covers the whole tile, the tick auto-completes
    it: score += segments, tile leaves play (state=hit), no DIE."""
    game = make_game(events=[[]], dts=[0.0])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=2, held_fraction=1.0)
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING
    assert game.score == 2
    assert long_tile.is_hit is True
    assert long_tile.held is False


def test_released_long_tile_mid_hold_pro_rates_score() -> None:
    """LANE_RELEASE while the overlay only covers part of the tile is a
    pro-rated success — credit for whichever segments the overlay reached,
    no DIE."""
    game = make_game(events=[[keyup(LANE_KEYS[1])]])
    force_playing(game)
    long_tile = _held_tile_with_overlay(
        lane=1,
        segments=3,
        held_fraction=2 / 3,  # two of three segments covered
    )
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING  # never DIE
    assert game.score == 2  # 2 of 3 segments awarded
    assert long_tile.held is False  # hold ended
    assert long_tile.is_hit is True  # out of play


def test_released_long_tile_with_no_overlay_scores_zero_no_die() -> None:
    """A release the very same frame as the press: held_amount is still 0,
    so no points — but still no DIE."""
    game = make_game(events=[[keyup(LANE_KEYS[0])]])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=2, held_fraction=0.0)
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.PLAYING
    assert game.score == 0
    assert long_tile.is_hit is True


def test_release_after_full_overlay_scores_all_segments() -> None:
    """A late release on a fully-held tile awards every segment (the
    auto-complete path may not have run yet — release does the same job)."""
    game = make_game()
    force_playing(game)
    tile = _held_tile_with_overlay(lane=0, segments=2, held_fraction=1.0)
    game._tiles.append(tile)
    game._handle_lane_release(0)
    assert game.score == 2
    assert tile.is_hit is True
    assert game.state is State.PLAYING


def test_find_held_tile_skips_tiles_in_other_lanes_and_unheld_tiles() -> None:
    """Multiple tiles in flight — only the matching lane + held one is found."""
    game = make_game()
    force_playing(game)
    not_held = Tile(lane=0, y=100.0, height=180.0, speed=300.0)
    target = Tile(lane=1, y=100.0, height=361.0, speed=300.0, segments=2, held=True)
    game._tiles.extend([not_held, target])
    assert game._find_held_tile(1) is target
    assert game._find_held_tile(0) is None  # tile in lane 0 isn't held
    assert game._find_held_tile(2) is None  # no tile in lane 2


def test_merge_does_not_extend_a_non_hittable_same_lane_tile() -> None:
    """Defensive: a same-lane existing tile that's already hit/missed can't be
    merged into. The new tile is appended fresh instead."""
    game = make_game()
    force_playing(game)
    earlier = Tile(lane=0, y=1.0, height=180.0, speed=300.0)
    earlier.mark_hit()
    new_tile = Tile(lane=0, y=-180.0, height=180.0, speed=300.0)
    game._tiles.append(earlier)
    assert game._merge_into_previous(new_tile) is False


def test_release_after_auto_completion_is_a_silent_noop() -> None:
    """A late release (player held a bit past the auto-complete) doesn't
    matter — by the time the release event arrives the tile is no longer
    held (state=hit), so the release finds nothing to act on."""
    game = make_game(events=[[]], dts=[0.0])
    force_playing(game)
    long_tile = _held_tile_with_overlay(lane=0, segments=2, held_fraction=1.0)
    game._tiles.append(long_tile)
    game.step()  # auto-completes the held tile
    assert game.score == 2
    assert game.state is State.PLAYING
    assert long_tile.held is False

    # A late release on this lane is a no-op now.
    score_after_complete = game.score
    game._clock.dts.append(0.0)
    game._events.batches.append([keyup(LANE_KEYS[0])])
    game.step()
    assert game.state is State.PLAYING
    assert game.score == score_after_complete  # no double-scoring


def test_release_when_not_holding_anything_is_a_silent_noop() -> None:
    """Releasing a key the player wasn't holding (rare but possible after a
    short-tile tap finishes) must not trigger DIE."""
    game = make_game(events=[[keyup(LANE_KEYS[0])]])
    force_playing(game)
    game.step()
    assert game.state is State.PLAYING


def test_unheld_long_tile_past_zone_still_dies_like_a_normal_miss() -> None:
    """If the player never presses, a long tile falling past the zone is a miss
    just like a short tile — held only protects against the miss."""
    game = make_game(events=[[]], dts=[0.0])
    force_playing(game)
    long_tile = Tile(
        lane=0,
        y=float(HIT_ZONE_BOTTOM + 1),
        height=361.0,
        speed=300.0,
        segments=2,
    )
    game._tiles.append(long_tile)
    game.step()
    assert game.state is State.GAME_OVER
