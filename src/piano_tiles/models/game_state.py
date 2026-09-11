"""Immutable per-frame snapshot of the world, consumed by the Renderer."""

from dataclasses import dataclass

from piano_tiles.config import DEFAULT_PALETTE, HIT_ZONE_BOTTOM, HIT_ZONE_TOP, Palette
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile


@dataclass(frozen=True)
class GameState:
    state: State
    tiles: tuple[Tile, ...] = ()
    score: int = 0
    hit_zone_top: float = HIT_ZONE_TOP
    hit_zone_bottom: float = HIT_ZONE_BOTTOM
    # The active song's colour theme. Drives the play-field and overlay colours;
    # defaults to the classic theme for states with no song selected.
    palette: Palette = DEFAULT_PALETTE
    # Set while a phase banner is animating in/out. `banner_phase_number` names
    # which phase's banner this is; `banner_elapsed` is seconds since it started.
    banner_phase_number: int | None = None
    banner_elapsed: float | None = None
    # Set only while `state is State.DYING` — the wrong-key flash.
    dying_phantom: Tile | None = None
    dying_elapsed: float | None = None
