import random

import pytest

from piano_tiles.components.spawner import (
    TileSpawner,
    interval_for_speed,
)
from piano_tiles.config import LANE_COUNT, TILE_HEIGHT, TILE_VISUAL_GAP_PX
from piano_tiles.models.tile import Tile


def _spawner(
    seed: int = 0,
    interval: float = 0.6,
    speed: float = 100.0,
    tile_height: float = TILE_HEIGHT,
) -> TileSpawner:
    return TileSpawner(
        rng=random.Random(seed),
        interval=interval,
        speed=speed,
        tile_height=tile_height,
    )


# ---- validation -----------------------------------------------------------


@pytest.mark.unit
def test_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError, match=r"interval must be > 0"):
        TileSpawner(rng=random.Random(0), interval=0.0, speed=100.0)
    with pytest.raises(ValueError, match=r"interval must be > 0"):
        TileSpawner(rng=random.Random(0), interval=-0.1, speed=100.0)


@pytest.mark.unit
def test_rejects_non_positive_speed() -> None:
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        TileSpawner(rng=random.Random(0), interval=0.5, speed=0.0)
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        TileSpawner(rng=random.Random(0), interval=0.5, speed=-100.0)


@pytest.mark.unit
def test_update_rejects_negative_dt() -> None:
    sp = _spawner()
    with pytest.raises(ValueError, match=r"dt must be >= 0"):
        sp.update(-0.001)


# ---- spawn timing ----------------------------------------------------------


@pytest.mark.unit
def test_spawns_zero_tiles_when_dt_smaller_than_interval() -> None:
    sp = _spawner(interval=0.6)
    assert sp.update(0.5) == []


@pytest.mark.unit
def test_zero_dt_spawns_nothing() -> None:
    assert _spawner().update(0.0) == []


@pytest.mark.unit
def test_spawns_one_tile_per_interval() -> None:
    sp = _spawner(interval=0.6)
    total = 0
    for _ in range(5):
        total += len(sp.update(0.6))
    assert total == 5


@pytest.mark.unit
def test_spawn_at_exact_interval_boundary_emits_tile() -> None:
    sp = _spawner(interval=0.6)
    assert len(sp.update(0.6)) == 1


@pytest.mark.unit
def test_large_dt_spawns_multiple_tiles_in_one_call() -> None:
    sp = _spawner(interval=0.6)
    # spawns at 0.6, 1.2, 1.8, 2.4, 3.0 = 5
    assert len(sp.update(3.0)) == 5


# ---- lane bounds -----------------------------------------------------------


@pytest.mark.unit
def test_lane_indices_always_in_valid_range() -> None:
    sp = _spawner(interval=0.1)
    tiles = sp.update(50.0)
    assert len(tiles) > 100
    for t in tiles:
        assert 0 <= t.lane < LANE_COUNT


# ---- determinism -----------------------------------------------------------


@pytest.mark.unit
def test_same_seed_and_dt_sequence_produces_identical_lanes() -> None:
    dts = [0.1, 0.6, 0.3, 1.2, 0.05, 2.0]
    a = _spawner(seed=42, interval=0.4)
    b = _spawner(seed=42, interval=0.4)
    seq_a = [tile.lane for dt in dts for tile in a.update(dt)]
    seq_b = [tile.lane for dt in dts for tile in b.update(dt)]
    assert seq_a == seq_b
    assert seq_a


# ---- spawned tile properties ----------------------------------------------


@pytest.mark.unit
def test_spawned_tile_uses_configured_speed_and_height() -> None:
    sp = _spawner(interval=0.1, speed=250.0, tile_height=80.0)
    tile = sp.update(0.1)[0]
    assert isinstance(tile, Tile)
    assert tile.speed == 250.0
    assert tile.height == 80.0
    assert tile.state == "falling"


@pytest.mark.unit
def test_spawned_tile_starts_above_screen() -> None:
    """At the exact spawn-boundary frame, y == -tile_height (no pre-fall to apply)."""
    sp = _spawner(interval=0.1, speed=100.0, tile_height=100.0)
    tile = sp.update(0.1)[0]
    assert tile.y == -100.0
    assert tile.bottom == 0.0


@pytest.mark.unit
def test_tile_pre_falls_when_spawned_mid_frame() -> None:
    """A tile spawned partway through a frame already has its sub-frame fall."""
    sp = _spawner(interval=1.0, speed=100.0, tile_height=50.0)
    # Spawn at exact t=1.0; frame ends at t=1.5 (0.5 s of pre-fall).
    tile = sp.update(1.5)[0]
    assert tile.y == pytest.approx(-50.0 + 100.0 * 0.5)


@pytest.mark.unit
def test_consecutive_spawns_in_one_call_are_exactly_interval_apart() -> None:
    sp = _spawner(interval=0.5, speed=200.0, tile_height=40.0)
    tiles = sp.update(1.0)
    assert len(tiles) == 2
    older, newer = tiles
    assert older.y - newer.y == pytest.approx(0.5 * 200.0)


# ---- interval_for_speed helper --------------------------------------------


@pytest.mark.unit
def test_interval_for_speed_keeps_visual_gap_constant() -> None:
    """Across speeds, the spawn distance differs from TILE_HEIGHT by ~TILE_VISUAL_GAP_PX."""
    for speed in (240.0, 290.0, 340.0, 390.0, 440.0):
        interval = interval_for_speed(speed)
        distance = interval * speed
        # Distance equals TILE_HEIGHT + visual_gap + tiny float buffer.
        assert distance > TILE_HEIGHT + TILE_VISUAL_GAP_PX
        assert distance < TILE_HEIGHT + TILE_VISUAL_GAP_PX + 0.1


@pytest.mark.unit
def test_interval_for_speed_rejects_non_positive_speed() -> None:
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        interval_for_speed(0.0)
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        interval_for_speed(-100.0)


@pytest.mark.unit
def test_interval_for_speed_produces_one_pixel_gap_across_phases() -> None:
    """For every PHASES speed, the float pixel gap stays in (1, 2) — renders as 1 px."""
    for speed in (240.0, 290.0, 340.0, 390.0, 440.0):
        interval = interval_for_speed(speed)
        gap = interval * speed - TILE_HEIGHT
        assert 1.0 < gap < 2.0


# ---- initial state ---------------------------------------------------------


@pytest.mark.unit
def test_initial_state_is_zero() -> None:
    sp = _spawner()
    assert sp.elapsed == 0.0
    assert sp.last_spawn_time == 0.0
