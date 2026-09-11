"""Falling tile model. Pure Python; no pygame imports."""

from dataclasses import dataclass, field
from typing import Literal

from piano_tiles.config import LANE_COUNT

TileState = Literal["falling", "hit", "missed"]


@dataclass
class Tile:
    lane: int
    y: float
    height: float
    speed: float
    state: TileState = "falling"
    # Number of merged segments. A short (un-merged) tile is 1 segment; the
    # spawner-driven merge in Game stacks 2+ when consecutive same-lane spawns
    # would have landed adjacent to one another.
    segments: int = 1
    # True while the player is currently holding the lane key on this tile.
    # Only meaningful for long tiles (segments >= 2); short tiles ignore it.
    held: bool = False
    # Height of the green overlay painted from the bottom of the tile upward.
    # Starts at 0 on press and grows at `speed * dt` each frame while held,
    # capped at `original_height`. On release the value freezes; the tile keeps
    # falling and the overlay stays attached, so the green never paints outside
    # the tile's borders.
    held_amount: float = 0.0
    # Height the tile started at — frozen once construction (or `extend_with`)
    # is done. Caps `held_amount` so the overlay can't outgrow the tile.
    original_height: float = field(init=False)

    def __post_init__(self) -> None:
        if not (0 <= self.lane < LANE_COUNT):
            raise ValueError(
                f"lane must be in 0..{LANE_COUNT - 1}, got {self.lane}"
            )
        if self.speed <= 0:
            raise ValueError(f"speed must be > 0, got {self.speed}")
        if self.segments < 1:
            raise ValueError(f"segments must be >= 1, got {self.segments}")
        self.original_height = self.height

    # ---- geometry ---------------------------------------------------------

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def overlaps_band(self, band_top: float, band_bottom: float) -> bool:
        """True if any part of the tile lies between band_top and band_bottom (inclusive)."""
        return self.top <= band_bottom and self.bottom >= band_top

    def is_past(self, y_limit: float) -> bool:
        """True if the tile has fallen entirely past the given y line (top strictly below it)."""
        return self.top > y_limit

    # ---- state predicates -------------------------------------------------

    @property
    def is_hittable(self) -> bool:
        """A tile is hittable only when it's still freely falling. Held tiles
        are excluded so a second press can't re-target the same tile and
        `mark_misses` can't flag one for slipping out of the zone."""
        return self.state == "falling" and not self.held

    @property
    def is_hit(self) -> bool:
        return self.state == "hit"

    @property
    def is_missed(self) -> bool:
        return self.state == "missed"

    @property
    def is_long(self) -> bool:
        """True iff the tile spans more than one segment — the press-and-hold tile."""
        return self.segments >= 2

    @property
    def is_fully_held(self) -> bool:
        """True iff the green overlay has grown to cover the whole tile."""
        return self.held_amount >= self.original_height

    # ---- transitions ------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance one frame.

        Missed tiles freeze in place. Every other tile keeps falling — even
        after a hit/release/completion — so the overlay (if any) travels with
        its tile and a culling pass off-screen can clean it up. While held, the
        green overlay also grows by `speed * dt`, capped at `original_height`.
        """
        if dt < 0:
            raise ValueError(f"dt must be >= 0, got {dt}")
        if self.is_missed:
            return
        self.y += self.speed * dt
        if self.held:
            self.grow_held(self.speed * dt)

    def grow_held(self, amount: float) -> None:
        """Extend the green overlay by `amount` pixels, capped at the tile's
        original height. Negative `amount` is ignored."""
        if amount <= 0:
            return
        self.held_amount = min(self.original_height, self.held_amount + amount)

    def fill_overlay(self) -> None:
        """Paint the whole tile with the green overlay in one shot. Used when a
        short tile is hit so it renders fully green — the same look as a
        completed long tile — without the caller reaching into the geometry."""
        self.held_amount = self.original_height

    def mark_hit(self) -> None:
        self.state = "hit"
        self.held = False

    def mark_missed(self) -> None:
        self.state = "missed"
        self.held = False

    def mark_held(self) -> None:
        """Begin a hold. Forces state back to `falling` because `HitDetector`
        marked the tile `hit` on the press that selected it — a long tile is
        still in play, so it shouldn't carry the `hit` state into the hold."""
        self.held = True
        self.state = "falling"

    def mark_released(self) -> None:
        self.held = False

    def segments_held(self, gap: float) -> int:
        """Number of segments the player has completed via the hold so far.

        A merged tile of N segments has total height `N*seg_h + (N-1)*gap`.
        Each segment-boundary k sits at `held_amount = k*seg_h + (k-1)*gap`, so
        the count is `floor((held_amount + gap) / (seg_h + gap))` capped at N.
        A fully-held tile returns N; no held growth returns 0.
        """
        if self.held_amount <= 0:
            return 0
        if self.held_amount >= self.original_height:
            return self.segments
        seg_h = (self.original_height - (self.segments - 1) * gap) / self.segments
        return min(self.segments, int((self.held_amount + gap) / (seg_h + gap)))

    def extend_with(self, other: "Tile", gap: float) -> None:
        """Absorb `other` (which must sit directly above this tile, separated by
        `gap` pixels) into this tile.

        After the call, `self` spans both regions as one continuous rectangle
        and its `segments` count grows by `other.segments`. `other` is left
        untouched; the caller is expected to discard it rather than insert it
        into the active list.
        """
        if not self.is_hittable:
            raise ValueError("cannot extend a tile that's not falling")
        self.height += other.height + gap
        self.y = other.y
        self.segments += other.segments
        self.original_height = self.height
