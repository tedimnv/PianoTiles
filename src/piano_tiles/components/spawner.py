"""Decides when and where tiles spawn. Pure Python; no pygame imports."""

import random
from dataclasses import dataclass, field

from piano_tiles.config import LANE_COUNT, TILE_HEIGHT, TILE_VISUAL_GAP_PX
from piano_tiles.models.tile import Tile

# Float safety buffer. Adding it to the spawn distance guarantees that, even
# after the round-trip `(distance / speed) * speed`, the actual float distance
# stays strictly above (TILE_HEIGHT + TILE_VISUAL_GAP_PX), so the rendered gap
# never collapses to zero pixels due to floor(0.99999...) rounding down.
_FLOAT_SAFETY_BUFFER = 1e-3


def interval_for_speed(speed: float, gap_px: float = TILE_VISUAL_GAP_PX) -> float:
    """Spawn interval that places same-lane tiles `gap_px` pixels apart visually.

    Uses `TILE_HEIGHT` and a tiny float-safety buffer so the visual gap is
    `gap_px` (with at most a single-pixel rounding flicker) across all speeds.
    """
    if speed <= 0:
        raise ValueError(f"speed must be > 0, got {speed}")
    return (TILE_HEIGHT + gap_px + _FLOAT_SAFETY_BUFFER) / speed


@dataclass
class TileSpawner:
    """Spawns tiles at a fixed interval and a fixed fall speed.

    Both interval and speed are constant for the lifetime of the spawner.
    When the game enters a new difficulty phase, the orchestrator builds a
    fresh spawner with the new phase's values.
    """

    rng: random.Random
    interval: float
    speed: float
    tile_height: float = TILE_HEIGHT

    elapsed: float = field(default=0.0, init=False)
    last_spawn_time: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError(f"interval must be > 0, got {self.interval}")
        if self.speed <= 0:
            raise ValueError(f"speed must be > 0, got {self.speed}")

    def update(self, dt: float) -> list[Tile]:
        if dt < 0:
            raise ValueError(f"dt must be >= 0, got {dt}")

        end_time = self.elapsed + dt
        new_tiles: list[Tile] = []
        while True:
            next_spawn_time = self.last_spawn_time + self.interval
            if next_spawn_time > end_time:
                break
            new_tiles.append(self._spawn_tile(end_time - next_spawn_time))
            self.last_spawn_time = next_spawn_time
        self.elapsed = end_time
        return new_tiles

    def _spawn_tile(self, time_since_spawn: float) -> Tile:
        return Tile(
            lane=self.rng.randrange(LANE_COUNT),
            y=-self.tile_height + self.speed * time_since_spawn,
            height=self.tile_height,
            speed=self.speed,
        )
