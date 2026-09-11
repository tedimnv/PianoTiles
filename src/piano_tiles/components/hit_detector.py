"""Hit / miss judgement. Pure Python; no pygame imports."""

from dataclasses import dataclass
from enum import Enum

from piano_tiles.models.tile import Tile


class Verdict(Enum):
    HIT = "hit"
    WRONG_KEY = "wrong_key"


@dataclass(frozen=True)
class Outcome:
    verdict: Verdict
    tile: Tile | None = None
    # On WRONG_KEY: the tile the player *should* have hit (lowest tile in any
    # lane that's in the zone and still hittable), if any. Used by the
    # orchestrator to position the wrong-key phantom flash. None when no tile
    # was in the zone at all.
    target_tile: Tile | None = None


class HitDetector:
    def press(
        self,
        lane: int,
        tiles: list[Tile],
        zone_top: float,
        zone_bottom: float,
    ) -> Outcome:
        in_zone = [
            t for t in tiles if t.is_hittable and t.overlaps_band(zone_top, zone_bottom)
        ]
        same_lane = [t for t in in_zone if t.lane == lane]
        if same_lane:
            best = max(same_lane, key=lambda t: t.bottom)
            best.mark_hit()
            return Outcome(verdict=Verdict.HIT, tile=best)
        target = max(in_zone, key=lambda t: t.bottom) if in_zone else None
        return Outcome(verdict=Verdict.WRONG_KEY, target_tile=target)

    def mark_misses(self, tiles: list[Tile], zone_bottom: float) -> list[Tile]:
        newly_missed: list[Tile] = []
        for t in tiles:
            if t.is_hittable and t.is_past(zone_bottom):
                t.mark_missed()
                newly_missed.append(t)
        return newly_missed
