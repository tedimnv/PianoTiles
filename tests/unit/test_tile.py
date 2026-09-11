import pytest

from piano_tiles.config import LANE_COUNT
from piano_tiles.models.tile import Tile


def _make(**overrides) -> Tile:
    defaults = dict(lane=0, y=0.0, height=100.0, speed=300.0)
    defaults.update(overrides)
    return Tile(**defaults)


# ---- movement -------------------------------------------------------------


@pytest.mark.unit
def test_update_advances_y_by_speed_times_dt() -> None:
    tile = _make(y=0.0, speed=200.0)
    tile.update(0.5)
    assert tile.y == pytest.approx(100.0)


@pytest.mark.unit
def test_update_with_dt_zero_is_a_noop() -> None:
    tile = _make(y=42.0)
    tile.update(0.0)
    assert tile.y == 42.0


@pytest.mark.unit
def test_update_on_hit_tile_still_falls() -> None:
    """Released long tiles stay in the list as `hit` so their green overlay
    keeps riding the falling tile until it's culled off-screen."""
    tile = _make(y=42.0, state="hit")
    tile.update(1.0)
    assert tile.y == 42.0 + tile.speed * 1.0


@pytest.mark.unit
def test_update_on_missed_tile_does_not_change_y() -> None:
    """Missed tiles freeze — they're already done; no reason to keep moving."""
    tile = _make(y=42.0, state="missed")
    tile.update(1.0)
    assert tile.y == 42.0


@pytest.mark.unit
def test_update_with_negative_dt_raises_value_error() -> None:
    tile = _make()
    with pytest.raises(ValueError):
        tile.update(-0.01)


@pytest.mark.unit
def test_repeated_updates_accumulate_movement() -> None:
    tile = _make(y=0.0, speed=100.0)
    for _ in range(10):
        tile.update(0.1)
    assert tile.y == pytest.approx(100.0)


# ---- construction validation ----------------------------------------------


@pytest.mark.unit
def test_construction_with_zero_speed_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _make(speed=0.0)


@pytest.mark.unit
def test_construction_with_negative_speed_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _make(speed=-1.0)


@pytest.mark.unit
def test_construction_with_lane_below_range_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _make(lane=-1)


@pytest.mark.unit
def test_construction_with_lane_above_range_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _make(lane=LANE_COUNT)


@pytest.mark.unit
def test_construction_with_each_valid_lane_succeeds() -> None:
    for lane in range(LANE_COUNT):
        assert _make(lane=lane).lane == lane


@pytest.mark.unit
def test_default_state_is_falling() -> None:
    assert _make().state == "falling"


# ---- geometry properties --------------------------------------------------


@pytest.mark.unit
def test_top_equals_y() -> None:
    tile = _make(y=123.0)
    assert tile.top == tile.y == 123.0


@pytest.mark.unit
def test_bottom_equals_y_plus_height() -> None:
    tile = _make(y=10.0, height=100.0)
    assert tile.bottom == 110.0


@pytest.mark.unit
def test_top_and_bottom_stay_consistent_after_update() -> None:
    tile = _make(y=0.0, height=100.0, speed=200.0)
    tile.update(0.25)
    assert tile.bottom == pytest.approx(tile.top + tile.height)


# ---- state predicates and mutators ----------------------------------------


@pytest.mark.unit
def test_is_hittable_is_true_only_while_falling() -> None:
    assert _make(state="falling").is_hittable is True
    assert _make(state="hit").is_hittable is False
    assert _make(state="missed").is_hittable is False


@pytest.mark.unit
def test_is_hit_is_true_only_in_hit_state() -> None:
    assert _make(state="falling").is_hit is False
    assert _make(state="hit").is_hit is True
    assert _make(state="missed").is_hit is False


@pytest.mark.unit
def test_is_missed_is_true_only_in_missed_state() -> None:
    assert _make(state="falling").is_missed is False
    assert _make(state="hit").is_missed is False
    assert _make(state="missed").is_missed is True


@pytest.mark.unit
def test_state_predicates_are_mutually_exclusive() -> None:
    """A tile is in exactly one of the three states."""
    for state in ("falling", "hit", "missed"):
        tile = _make(state=state)
        flags = (tile.is_hittable, tile.is_hit, tile.is_missed)
        assert sum(flags) == 1, f"state={state!r} flags={flags}"


@pytest.mark.unit
def test_mark_hit_changes_state_to_hit() -> None:
    tile = _make()
    tile.mark_hit()
    assert tile.state == "hit"
    assert tile.is_hittable is False


@pytest.mark.unit
def test_mark_missed_changes_state_to_missed() -> None:
    tile = _make()
    tile.mark_missed()
    assert tile.state == "missed"
    assert tile.is_hittable is False


# ---- geometry queries -----------------------------------------------------


@pytest.mark.unit
def test_overlaps_band_when_fully_inside() -> None:
    tile = _make(y=620.0, height=60.0)  # 620..680
    assert tile.overlaps_band(600.0, 700.0) is True


@pytest.mark.unit
def test_overlaps_band_when_partially_overlapping_top() -> None:
    tile = _make(y=550.0, height=100.0)  # 550..650
    assert tile.overlaps_band(600.0, 700.0) is True


@pytest.mark.unit
def test_overlaps_band_when_partially_overlapping_bottom() -> None:
    tile = _make(y=680.0, height=100.0)  # 680..780
    assert tile.overlaps_band(600.0, 700.0) is True


@pytest.mark.unit
def test_overlaps_band_at_top_boundary_is_inclusive() -> None:
    tile = _make(y=600.0, height=100.0)  # top exactly at band_top
    assert tile.overlaps_band(600.0, 700.0) is True


@pytest.mark.unit
def test_overlaps_band_at_bottom_boundary_is_inclusive() -> None:
    tile = _make(y=600.0, height=100.0)  # bottom exactly at band_bottom
    assert tile.overlaps_band(600.0, 700.0) is True


@pytest.mark.unit
def test_overlaps_band_when_entirely_above_is_false() -> None:
    tile = _make(y=100.0, height=100.0)  # bottom=200 < 600
    assert tile.overlaps_band(600.0, 700.0) is False


@pytest.mark.unit
def test_overlaps_band_when_entirely_below_is_false() -> None:
    tile = _make(y=800.0, height=100.0)  # top=800 > 700
    assert tile.overlaps_band(600.0, 700.0) is False


# ---- segments + is_long + held -------------------------------------------


@pytest.mark.unit
def test_default_segments_is_one_and_is_long_is_false() -> None:
    tile = _make()
    assert tile.segments == 1
    assert tile.is_long is False


@pytest.mark.unit
def test_segments_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"segments must be >= 1"):
        _make(segments=0)


@pytest.mark.unit
def test_segments_of_two_or_more_makes_the_tile_long() -> None:
    assert _make(segments=2).is_long is True
    assert _make(segments=5).is_long is True


@pytest.mark.unit
def test_default_held_is_false() -> None:
    assert _make().held is False


@pytest.mark.unit
def test_mark_held_sets_held_flag() -> None:
    tile = _make()
    tile.mark_held()
    assert tile.held is True


@pytest.mark.unit
def test_mark_released_clears_held_flag() -> None:
    tile = _make()
    tile.mark_held()
    tile.mark_released()
    assert tile.held is False


@pytest.mark.unit
def test_mark_hit_clears_held_flag_too() -> None:
    """Once a tile is hit, it should no longer count as held — visual sanity."""
    tile = _make()
    tile.mark_held()
    tile.mark_hit()
    assert tile.held is False


@pytest.mark.unit
def test_mark_missed_clears_held_flag_too() -> None:
    tile = _make()
    tile.mark_held()
    tile.mark_missed()
    assert tile.held is False


# ---- extend_with ----------------------------------------------------------


@pytest.mark.unit
def test_extend_with_absorbs_the_other_tile_geometry() -> None:
    """Other sits above; after extend, self spans both regions in one rect."""
    upper = _make(y=-180.0, height=180.0)
    lower = _make(y=1.0, height=180.0)  # 1 px below upper's bottom
    lower.extend_with(upper, gap=1.0)
    assert lower.y == -180.0
    assert lower.height == pytest.approx(180.0 + 180.0 + 1.0)
    assert lower.bottom == pytest.approx(181.0)


@pytest.mark.unit
def test_extend_with_increments_segments_count() -> None:
    lower = _make(y=1.0, height=180.0, segments=1)
    upper = _make(y=-180.0, height=180.0, segments=1)
    lower.extend_with(upper, gap=1.0)
    assert lower.segments == 2


@pytest.mark.unit
def test_extend_with_can_stack_multiple_times() -> None:
    """Extending repeatedly grows the tile and segments count linearly."""
    base = _make(y=2.0, height=180.0)
    base.extend_with(_make(y=-179.0, height=180.0), gap=1.0)  # 2 segments
    base.extend_with(_make(y=-360.0, height=180.0), gap=1.0)  # 3 segments
    assert base.segments == 3


@pytest.mark.unit
def test_extend_with_rejects_a_non_falling_target() -> None:
    base = _make(y=2.0, height=180.0, state="hit")
    with pytest.raises(ValueError, match=r"not falling"):
        base.extend_with(_make(y=-179.0, height=180.0), gap=1.0)


@pytest.mark.unit
def test_is_past_when_top_is_strictly_below_limit() -> None:
    tile = _make(y=701.0)  # top=701, limit=700
    assert tile.is_past(700.0) is True


@pytest.mark.unit
def test_is_past_is_false_when_top_equals_limit() -> None:
    """Boundary: 'past' means strictly below, not touching."""
    tile = _make(y=700.0)
    assert tile.is_past(700.0) is False


@pytest.mark.unit
def test_is_past_is_false_when_top_is_above_limit() -> None:
    tile = _make(y=500.0)
    assert tile.is_past(700.0) is False


# ---- grow_held ------------------------------------------------------------


@pytest.mark.unit
def test_grow_held_increases_held_amount_by_given_pixels() -> None:
    tile = _make(height=200.0)
    tile.grow_held(40.0)
    assert tile.held_amount == 40.0


@pytest.mark.unit
def test_grow_held_with_zero_or_negative_amount_is_a_noop() -> None:
    tile = _make(height=200.0)
    tile.grow_held(0.0)
    tile.grow_held(-15.0)
    assert tile.held_amount == 0.0


@pytest.mark.unit
def test_grow_held_caps_held_amount_at_original_height() -> None:
    """The overlay must never paint past the tile's borders — caps at the
    original height even after multiple oversized growths."""
    tile = _make(height=180.0)
    tile.grow_held(500.0)
    assert tile.held_amount == 180.0
    tile.grow_held(99999.0)
    assert tile.held_amount == 180.0


@pytest.mark.unit
def test_repeated_grow_held_accumulates_to_the_cap() -> None:
    tile = _make(height=100.0)
    for _ in range(20):
        tile.grow_held(10.0)
    assert tile.held_amount == 100.0


# ---- fill_overlay ---------------------------------------------------------


@pytest.mark.unit
def test_fill_overlay_grows_overlay_to_the_full_tile_in_one_call() -> None:
    """A short-tile hit paints the whole tile green at once."""
    tile = _make(height=180.0)
    tile.fill_overlay()
    assert tile.held_amount == tile.original_height
    assert tile.is_fully_held is True


@pytest.mark.unit
def test_fill_overlay_does_not_exceed_original_height() -> None:
    """Even called repeatedly the overlay caps at the tile's borders."""
    tile = _make(height=180.0)
    tile.fill_overlay()
    tile.fill_overlay()
    assert tile.held_amount == 180.0


# ---- update while held ----------------------------------------------------


@pytest.mark.unit
def test_update_on_held_tile_falls_and_grows_held_amount_by_speed_times_dt() -> None:
    """While held, the tile still falls — the green overlay grows at the same
    rate so its top stays anchored at the press-time tile.bottom."""
    tile = _make(y=100.0, height=200.0, speed=300.0, segments=2)
    bottom_at_press = tile.bottom
    tile.mark_held()
    tile.update(0.1)  # 30 px of fall, 30 px of held growth
    assert tile.y == pytest.approx(130.0)
    assert tile.held_amount == pytest.approx(30.0)
    # The green top sits at (tile.bottom - held_amount) — invariant during a hold.
    assert tile.bottom - tile.held_amount == pytest.approx(bottom_at_press)


@pytest.mark.unit
def test_update_on_released_tile_continues_falling_with_held_amount_frozen() -> None:
    """After release the tile keeps falling, but the overlay size stops
    growing — exactly the user-visible 'green stays where it is' guarantee."""
    tile = _make(y=100.0, height=200.0, speed=300.0, segments=2)
    tile.mark_held()
    tile.update(0.1)  # held_amount → 30
    tile.mark_hit()  # release / completion
    tile.update(0.1)  # tile falls another 30 px
    assert tile.y == pytest.approx(160.0)
    assert tile.held_amount == pytest.approx(30.0)  # frozen


@pytest.mark.unit
def test_update_on_hit_tile_keeps_falling() -> None:
    """Released long tiles must keep falling so their green overlay rides off
    the bottom of the screen alongside the tile — `is_hit` no longer freezes
    movement."""
    tile = _make(y=100.0, height=180.0, speed=200.0, state="hit")
    tile.update(0.5)
    assert tile.y == pytest.approx(200.0)


@pytest.mark.unit
def test_update_on_held_tile_caps_held_amount_with_large_dt() -> None:
    """A huge dt shouldn't drive held_amount past original_height."""
    tile = _make(y=0.0, height=50.0, speed=300.0, segments=2)
    tile.mark_held()
    tile.update(1.0)  # would grow by 300 px, but height cap = 50
    assert tile.held_amount == 50.0


# ---- is_fully_held --------------------------------------------------------


@pytest.mark.unit
def test_is_fully_held_is_false_until_overlay_reaches_original_height() -> None:
    tile = _make(height=200.0, segments=2)
    tile.mark_held()
    tile.grow_held(199.0)
    assert tile.is_fully_held is False
    tile.grow_held(1.0)
    assert tile.is_fully_held is True


@pytest.mark.unit
def test_is_fully_held_stays_true_after_release() -> None:
    """Completion is permanent — even if `held` is later cleared, the overlay
    still covers the tile."""
    tile = _make(height=100.0, segments=2)
    tile.mark_held()
    tile.grow_held(100.0)
    tile.mark_hit()
    assert tile.is_fully_held is True


# ---- is_hittable interaction with held ------------------------------------


@pytest.mark.unit
def test_held_tile_is_not_hittable() -> None:
    """Once held, the tile can't be re-targeted by hit-detection or flagged
    as a miss — the player is actively engaging with it."""
    tile = _make()
    assert tile.is_hittable is True
    tile.mark_held()
    assert tile.is_hittable is False


# ---- original_height ------------------------------------------------------


@pytest.mark.unit
def test_original_height_is_set_from_construction_height() -> None:
    tile = _make(height=361.0)
    assert tile.original_height == 361.0


@pytest.mark.unit
def test_original_height_does_not_change_when_held_amount_grows() -> None:
    """The cap reference must stay fixed even as held_amount climbs."""
    tile = _make(y=0.0, height=300.0, segments=2)
    tile.mark_held()
    tile.grow_held(120.0)
    assert tile.height == 300.0
    assert tile.original_height == 300.0


@pytest.mark.unit
def test_extend_with_refreshes_original_height_to_the_new_total() -> None:
    """After a merge, original_height = the merged height (so the held cap
    matches the new long tile)."""
    lower = _make(y=1.0, height=180.0)
    upper = _make(y=-180.0, height=180.0)
    lower.extend_with(upper, gap=1.0)
    assert lower.original_height == pytest.approx(361.0)


# ---- segments_held --------------------------------------------------------


@pytest.mark.unit
def test_segments_held_is_zero_with_no_growth() -> None:
    tile = _make(height=361.0, segments=2)
    assert tile.segments_held(gap=1.0) == 0


@pytest.mark.unit
def test_segments_held_returns_full_count_when_overlay_reaches_original_height() -> None:
    tile = _make(y=0.0, height=361.0, segments=2)
    tile.mark_held()
    tile.grow_held(361.0)
    assert tile.segments_held(gap=1.0) == 2


@pytest.mark.unit
def test_segments_held_at_first_segment_boundary() -> None:
    """For a 2-segment tile, the first 180 px of overlay covers one full
    segment → exactly 1 segment held."""
    tile = _make(y=0.0, height=361.0, segments=2)
    tile.mark_held()
    tile.grow_held(180.0)
    assert tile.segments_held(gap=1.0) == 1


@pytest.mark.unit
def test_segments_held_just_short_of_first_boundary_is_zero() -> None:
    tile = _make(y=0.0, height=361.0, segments=2)
    tile.mark_held()
    tile.grow_held(179.0)
    assert tile.segments_held(gap=1.0) == 0


@pytest.mark.unit
def test_segments_held_mid_gap_still_reports_lower_segment() -> None:
    """Inside the inter-segment gap is still 'first segment done', not 'second
    segment done'."""
    tile = _make(y=0.0, height=361.0, segments=2)
    tile.mark_held()
    tile.grow_held(180.5)
    assert tile.segments_held(gap=1.0) == 1


@pytest.mark.unit
def test_segments_held_handles_three_segment_tile_at_each_boundary() -> None:
    """N=3 boundaries: 180, 361, 542 (== original_height) — verify each."""
    height = 3 * 180.0 + 2 * 1.0  # 542
    for held_amount, expected in [
        (0.0, 0),
        (179.0, 0),
        (180.0, 1),
        (180.5, 1),  # mid-gap
        (361.0, 2),
        (361.5, 2),  # mid-gap
        (542.0, 3),
    ]:
        tile = _make(y=0.0, height=height, segments=3)
        tile.mark_held()
        tile.grow_held(held_amount)
        assert tile.segments_held(gap=1.0) == expected, (
            f"held_amount={held_amount} → expected {expected}, got "
            f"{tile.segments_held(gap=1.0)}"
        )


# ---- mark_held resets state -----------------------------------------------


@pytest.mark.unit
def test_mark_held_resets_state_to_falling_after_a_hit_detector_flagged_it() -> None:
    """HitDetector marks a pressed tile `hit` before Game realises it's a long
    tile that should stay in play; mark_held undoes that side-effect."""
    tile = _make()
    tile.mark_hit()
    assert tile.state == "hit"
    tile.mark_held()
    assert tile.state == "falling"
    assert tile.held is True
