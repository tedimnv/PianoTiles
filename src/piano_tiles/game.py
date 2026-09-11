"""Game orchestrator. Owns the main loop and wires the components together.

Logic lives in the components; this module is glue. The `Clock` and
`EventSource` seams let the game run headless with scripted inputs in tests;
production-mode pygame implementations live in `piano_tiles.pygame_seams`.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any, Protocol

import pygame

from piano_tiles.components.banner_timer import BannerTimer
from piano_tiles.components.dying_flash import DyingFlash
from piano_tiles.components.hit_detector import HitDetector, Verdict
from piano_tiles.components.input_adapter import (
    InputAdapter,
    InputEvent,
    InputEventKind,
)
from piano_tiles.components.main_menu import song_index_at
from piano_tiles.components.phase_schedule import PhaseSchedule
from piano_tiles.components.phase_tracker import PhaseTracker
from piano_tiles.components.score import ScoreKeeper
from piano_tiles.components.spawner import TileSpawner, interval_for_speed
from piano_tiles.components.state_machine import Event, StateMachine
from piano_tiles.config import (
    DEFAULT_PALETTE,
    HIT_ZONE_BOTTOM,
    HIT_ZONE_TOP,
    SONGS,
    TILE_HEIGHT,
    TILE_VISUAL_GAP_PX,
    WINDOW_H,
    Palette,
    Song,
)
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile
from piano_tiles.music import MusicDirector, MusicPlayer, SilentMusicPlayer


class Clock(Protocol):
    def tick(self) -> float:
        """Advance one frame; return seconds since the previous tick."""


class EventSource(Protocol):
    def poll(self) -> Iterable[Any]:
        """Return the raw events that have arrived since the last call."""


class _RendererProto(Protocol):
    def render(self, state: GameState, surface: Any) -> None: ...


class Game:
    def __init__(
        self,
        *,
        clock: Clock,
        events: EventSource,
        surface: Any = None,
        renderer: _RendererProto | None = None,
        rng: random.Random | None = None,
        phase_schedule: PhaseSchedule | None = None,
        input_adapter: InputAdapter | None = None,
        state_machine: StateMachine | None = None,
        score_keeper: ScoreKeeper | None = None,
        hit_detector: HitDetector | None = None,
        music: MusicPlayer | None = None,
    ) -> None:
        self._clock = clock
        self._events = events
        self._surface = surface
        self._renderer = renderer
        self._rng = rng if rng is not None else random.Random()
        self._input = input_adapter or InputAdapter()
        self._state_machine = state_machine or StateMachine()
        self._score = score_keeper or ScoreKeeper()
        self._detector = hit_detector or HitDetector()
        self._music = MusicDirector(music if music is not None else SilentMusicPlayer())
        self._tiles: list[Tile] = []
        self._phases = PhaseTracker(phase_schedule or PhaseSchedule.from_config())
        self._spawner = self._make_spawner()
        self._banner = BannerTimer()
        self._dying = DyingFlash()
        self._selected_song: Song | None = None

    # ---- public read-only surface -----------------------------------------

    @property
    def state(self) -> State:
        return self._state_machine.state

    @property
    def score(self) -> int:
        return self._score.score

    @property
    def tiles(self) -> tuple[Tile, ...]:
        return tuple(self._tiles)

    @property
    def phase_number(self) -> int:
        return self._phases.phase_number

    @property
    def selected_song(self) -> Song | None:
        """The song chosen on the main menu, or None before any selection."""
        return self._selected_song

    @property
    def palette(self) -> Palette:
        """The active colour theme: the chosen song's palette, or the default
        theme before any song is picked."""
        if self._selected_song is None:
            return DEFAULT_PALETTE
        return self._selected_song.palette

    # ---- main loop --------------------------------------------------------

    def step(self) -> None:
        """One frame: handle queued input, advance time, render."""
        self._handle_inputs()
        if self.state is State.QUIT:
            return
        dt = self._clock.tick()
        self._tick(dt)
        self._render()

    def run(self) -> None:
        while self.state is not State.QUIT:
            self.step()

    def _tick(self, dt: float) -> None:
        if self.state is State.PLAYING:
            self._tick_playing(dt)
        elif self.state is State.DYING:
            self._tick_dying(dt)

    # ---- input ------------------------------------------------------------

    def _handle_inputs(self) -> None:
        for event in self._input.translate(self._events.poll()):
            self._dispatch(event)
            if self.state is State.QUIT:
                return

    def _dispatch(self, event: InputEvent) -> None:
        if event.kind is InputEventKind.QUIT:
            self._fire(Event.QUIT)
            return
        match (self.state, event.kind):
            case (State.MAIN_MENU, InputEventKind.CLICK):
                self._handle_song_click(event.pos)
            case (State.MENU, InputEventKind.RESTART):
                self._fire(Event.START)
            case (State.PLAYING, InputEventKind.PAUSE):
                self._fire(Event.PAUSE)
            case (State.PLAYING, InputEventKind.LANE_PRESS):
                self._handle_lane_press(event.lane)
            case (State.PLAYING, InputEventKind.LANE_RELEASE):
                self._handle_lane_release(event.lane)
            case (State.PAUSED, InputEventKind.PAUSE):
                self._fire(Event.RESUME)
            case (State.GAME_OVER, InputEventKind.RESTART):
                self._restart_run()
            case (State.GAME_OVER, InputEventKind.MENU):
                self._to_main_menu()

    def _handle_song_click(self, pos: tuple[int, int] | None) -> None:
        """A click on the main menu: if it landed on a song box, choose that
        song and advance to the start screen. A click on empty space is a
        silent no-op."""
        if pos is None:
            return
        index = song_index_at(pos)
        if index is not None:
            self._choose_song(index)

    def _choose_song(self, index: int) -> None:
        song = SONGS[index]
        self._selected_song = song
        self._music.use_track(song.path)
        self._fire(Event.SELECT_SONG)

    def _handle_lane_press(self, lane: int) -> None:
        outcome = self._detector.press(
            lane, self._tiles, HIT_ZONE_TOP, HIT_ZONE_BOTTOM
        )
        if outcome.verdict is Verdict.WRONG_KEY:
            self._begin_dying(lane, outcome.target_tile)
            return
        tile = outcome.tile
        assert tile is not None
        if tile.is_long:
            # Long tile: start the hold. The tile keeps falling and grows its
            # overlay while held; score lands per-segment as the overlay
            # reaches each boundary (auto on full hold, pro-rated on release).
            tile.mark_held()
            return
        # Short tile: count the one hit and paint it fully green. It's already
        # `hit` from `HitDetector`, so it stays on the field (miss-check skips
        # it) and keeps falling until it's culled off-screen.
        self._score.on_hit()
        tile.fill_overlay()

    def _handle_lane_release(self, lane: int) -> None:
        """End a hold. Early release is never a mistake — the player banks
        whichever segments the overlay reached before letting go. Releasing
        nothing is a silent no-op.
        """
        held = self._find_held_tile(lane)
        if held is not None:
            self._complete_long_tile(held)

    def _complete_long_tile(self, tile: Tile) -> None:
        """Bank the segments the overlay has reached and take the tile out of
        play. Shared by both completion paths: the auto-complete tick (a
        fully-held tile, so `segments_held` returns every segment) and an
        early release (pro-rated to the overlay's progress). The tile stays in
        the list with its green overlay frozen until it's culled off-screen.
        """
        self._award_segments(tile.segments_held(TILE_VISUAL_GAP_PX))
        tile.mark_hit()

    def _award_segments(self, count: int) -> None:
        for _ in range(count):
            self._score.on_hit()

    def _find_held_tile(self, lane: int) -> Tile | None:
        for tile in self._tiles:
            if tile.lane == lane and tile.held:
                return tile
        return None

    # ---- per-frame tick ---------------------------------------------------

    def _tick_playing(self, dt: float) -> None:
        spawn_dt = self._sync_phase(dt)
        self._update_falling_tiles(dt)
        self._spawn_new_tiles(spawn_dt)
        self._complete_held_tiles()
        if self._handle_misses():
            return
        self._cull_offscreen_tiles()

    def _tick_dying(self, dt: float) -> None:
        if self._dying.tick(dt):
            self._fire(Event.DIE)

    def _sync_phase(self, dt: float) -> float:
        """Advance the phase clock and start a banner if a boundary crossed.

        Returns the dt the spawner should use this tick — the post-boundary
        leftover when we just crossed into a new phase, otherwise the full dt.
        """
        leftover = self._phases.advance_play(dt)
        if leftover is None:
            self._banner.tick(dt)
            return dt
        self._spawner = self._make_spawner()
        self._banner.start(self._phases.phase_number, initial_elapsed=leftover)
        return leftover

    def _update_falling_tiles(self, dt: float) -> None:
        for tile in self._tiles:
            tile.update(dt)

    def _spawn_new_tiles(self, spawn_dt: float) -> None:
        # Spawning pauses while the phase-change banner is showing — gives the
        # banner area a clean canvas (old tiles fall through and clear out,
        # no new tiles enter to overlap with it).
        if self._banner.is_active:
            return
        for new_tile in self._spawner.update(spawn_dt):
            if not self._merge_into_previous(new_tile):
                self._tiles.append(new_tile)

    def _merge_into_previous(self, new_tile: Tile) -> bool:
        """If the new spawn continues the previous same-lane tile's run, extend
        that tile to absorb it and return True. Otherwise return False so the
        caller appends a fresh tile.

        Same-lane consecutive spawns are exactly TILE_VISUAL_GAP_PX apart by
        the spawner's interval choice. Merging them turns the random run into
        one long continuous tile that the player presses-and-holds.
        """
        existing = self._most_recent_in_lane(new_tile.lane)
        if existing is None or not self._continues_run(existing, new_tile):
            return False
        existing.extend_with(new_tile, gap=TILE_VISUAL_GAP_PX)
        return True

    def _most_recent_in_lane(self, lane: int) -> Tile | None:
        for tile in reversed(self._tiles):
            if tile.lane == lane:
                return tile
        return None

    @staticmethod
    def _continues_run(existing: Tile, new_tile: Tile) -> bool:
        """True iff `new_tile` extends `existing`'s run: that tile must still
        be freely falling (not hit/missed/held), moving at the same speed (a
        phase boundary changes it), and sit exactly one visual gap below the
        new spawn."""
        return (
            existing.is_hittable
            and existing.speed == new_tile.speed
            and abs(existing.top - new_tile.bottom) <= TILE_VISUAL_GAP_PX + 0.1
        )

    def _complete_held_tiles(self) -> None:
        """Auto-complete held tiles whose overlay has covered the whole tile.

        Fires once `is_fully_held` — the player has held the lane long enough
        to cover every segment. Runs before `_handle_misses` so a fully-held
        tile never trips a miss.
        """
        for tile in [t for t in self._tiles if t.held and t.is_fully_held]:
            self._complete_long_tile(tile)

    def _handle_misses(self) -> bool:
        """Mark tiles past the zone as missed; fire DIE if any were caught."""
        if self._detector.mark_misses(self._tiles, HIT_ZONE_BOTTOM):
            self._fire(Event.DIE)
            return True
        return False

    def _cull_offscreen_tiles(self) -> None:
        self._tiles = [t for t in self._tiles if t.top <= WINDOW_H]

    # ---- dying lifecycle --------------------------------------------------

    def _begin_dying(self, lane: int, target: Tile | None) -> None:
        self._dying.begin(self._make_phantom(lane, target))
        self._fire(Event.WRONG_KEY)

    def _make_phantom(self, lane: int, target: Tile | None) -> Tile:
        y = target.y if target is not None else _hit_zone_center_y()
        return Tile(
            lane=lane,
            y=y,
            height=TILE_HEIGHT,
            speed=self._phases.current_phase.speed,
        )

    # ---- lifecycle --------------------------------------------------------

    def _fire(self, event: Event) -> None:
        self._state_machine.process(event)
        self._music.react_to(event)

    def _reset_run(self) -> None:
        """Clear the field back to a fresh-run state. Shared by restart (back
        to PLAYING) and return-to-menu (back to MAIN_MENU)."""
        self._tiles.clear()
        self._score.reset()
        self._phases.reset()
        self._spawner = self._make_spawner()
        self._banner.clear()
        self._dying.clear()

    def _restart_run(self) -> None:
        self._reset_run()
        self._fire(Event.RESTART)

    def _to_main_menu(self) -> None:
        self._reset_run()
        self._fire(Event.TO_MAIN_MENU)

    def _make_spawner(self) -> TileSpawner:
        phase = self._phases.current_phase
        return TileSpawner(
            rng=self._rng,
            interval=interval_for_speed(phase.speed),
            speed=phase.speed,
        )

    def _render(self) -> None:
        if self._renderer is None or self._surface is None:
            return
        self._renderer.render(self._snapshot(), self._surface)
        if self._surface is pygame.display.get_surface():
            pygame.display.flip()

    def _snapshot(self) -> GameState:
        return GameState(
            state=self.state,
            tiles=tuple(self._tiles),
            score=self._score.score,
            banner_phase_number=self._banner.phase_number,
            banner_elapsed=self._banner.elapsed,
            dying_phantom=self._dying.phantom,
            dying_elapsed=self._dying.elapsed,
            palette=self.palette,
        )


def _hit_zone_center_y() -> float:
    """Y for a phantom tile when there's no target tile in the hit zone.

    Centres a tile vertically in the hit zone. The phantom mirrors the lane
    the player pressed; this gives it a credible Y to flash at when nothing
    was there to hit in the first place.
    """
    return (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) / 2 - TILE_HEIGHT / 2
