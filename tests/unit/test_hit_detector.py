import pytest

from piano_tiles.components.hit_detector import HitDetector, Outcome, Verdict
from piano_tiles.models.tile import Tile

ZONE_TOP = 600.0
ZONE_BOTTOM = 700.0
TILE_HEIGHT = 80.0


def _tile(lane: int = 0, top: float = 0.0, state: str = "falling") -> Tile:
    return Tile(lane=lane, y=top, height=TILE_HEIGHT, speed=300.0, state=state)


# ---- HIT cases -------------------------------------------------------------


@pytest.mark.unit
def test_tile_fully_inside_zone_with_correct_lane_is_hit() -> None:
    det = HitDetector()
    tile = _tile(lane=2, top=610.0)  # 610..690 fully inside 600..700
    outcome = det.press(2, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.HIT
    assert outcome.tile is tile
    assert tile.state == "hit"


@pytest.mark.unit
def test_tile_with_top_exactly_at_zone_top_is_hit() -> None:
    """Boundary edge: top == ZONE_TOP → HIT."""
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_TOP)  # top=600, bottom=680
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.HIT
    assert tile.state == "hit"


@pytest.mark.unit
def test_tile_with_bottom_exactly_at_zone_bottom_is_hit() -> None:
    """Boundary edge: bottom == ZONE_BOTTOM → HIT."""
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM - TILE_HEIGHT)  # top=620, bottom=700
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.HIT
    assert tile.state == "hit"


# ---- WRONG_KEY cases -------------------------------------------------------


@pytest.mark.unit
def test_tile_above_zone_returns_wrong_key() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=100.0)  # bottom=180 < 600
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY
    assert outcome.tile is None
    assert tile.state == "falling"


@pytest.mark.unit
def test_tile_below_zone_returns_wrong_key() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM + 1.0)  # top=701 > 700
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY
    assert tile.state == "falling"


@pytest.mark.unit
def test_no_tile_in_pressed_lane_returns_wrong_key() -> None:
    det = HitDetector()
    outcome = det.press(1, [], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY
    assert outcome.tile is None


@pytest.mark.unit
def test_tile_in_different_lane_returns_wrong_key() -> None:
    det = HitDetector()
    tile = _tile(lane=3, top=620.0)
    outcome = det.press(1, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY
    assert tile.state == "falling"  # unchanged


# ---- multiple tiles in same lane ------------------------------------------


@pytest.mark.unit
def test_multiple_tiles_in_zone_lowest_is_hit_other_unaffected() -> None:
    det = HitDetector()
    upper = _tile(lane=0, top=605.0)  # 605..685
    lower = _tile(lane=0, top=618.0)  # 618..698 (closer to bottom)
    outcome = det.press(0, [upper, lower], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.HIT
    assert outcome.tile is lower
    assert lower.state == "hit"
    assert upper.state == "falling"


@pytest.mark.unit
def test_lowest_is_picked_regardless_of_input_order() -> None:
    det = HitDetector()
    upper = _tile(lane=0, top=605.0)
    lower = _tile(lane=0, top=618.0)
    outcome = det.press(0, [lower, upper], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.tile is lower


# ---- non-falling tiles -----------------------------------------------------


@pytest.mark.unit
def test_already_hit_tile_is_not_re_hittable() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=620.0, state="hit")
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY


@pytest.mark.unit
def test_missed_tile_is_not_hittable() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=620.0, state="missed")
    outcome = det.press(0, [tile], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.WRONG_KEY


@pytest.mark.unit
def test_already_hit_tile_is_skipped_in_favor_of_falling_tile() -> None:
    det = HitDetector()
    already_hit = _tile(lane=0, top=618.0, state="hit")  # lower
    falling = _tile(lane=0, top=605.0, state="falling")  # higher but available
    outcome = det.press(0, [already_hit, falling], ZONE_TOP, ZONE_BOTTOM)
    assert outcome.verdict == Verdict.HIT
    assert outcome.tile is falling
    assert already_hit.state == "hit"  # unchanged


# ---- mark_misses -----------------------------------------------------------


@pytest.mark.unit
def test_mark_misses_flips_tile_past_zone_to_missed() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM + 1.0)  # top=701 > 700
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "missed"
    assert newly == [tile]


@pytest.mark.unit
def test_mark_misses_leaves_tile_in_zone_alone() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=620.0)
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "falling"
    assert newly == []


@pytest.mark.unit
def test_mark_misses_leaves_tile_above_zone_alone() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=100.0)
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "falling"
    assert newly == []


@pytest.mark.unit
def test_mark_misses_does_not_reflip_already_hit_tile() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM + 50.0, state="hit")
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "hit"
    assert newly == []


@pytest.mark.unit
def test_mark_misses_does_not_reflip_already_missed_tile() -> None:
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM + 50.0, state="missed")
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "missed"
    assert newly == []


@pytest.mark.unit
def test_mark_misses_at_exact_boundary_top_equal_to_zone_bottom_is_not_missed() -> None:
    """Boundary edge: top == zone_bottom is still in-zone; not missed yet."""
    det = HitDetector()
    tile = _tile(lane=0, top=ZONE_BOTTOM)  # top exactly at boundary
    newly = det.mark_misses([tile], ZONE_BOTTOM)
    assert tile.state == "falling"
    assert newly == []


@pytest.mark.unit
def test_mark_misses_returns_only_newly_missed_tiles() -> None:
    det = HitDetector()
    a_in_zone = _tile(lane=0, top=620.0)
    b_past_zone = _tile(lane=1, top=ZONE_BOTTOM + 5.0)
    c_already_hit = _tile(lane=2, top=ZONE_BOTTOM + 50.0, state="hit")
    d_past_zone = _tile(lane=3, top=ZONE_BOTTOM + 100.0)

    newly = det.mark_misses([a_in_zone, b_past_zone, c_already_hit, d_past_zone], ZONE_BOTTOM)

    assert newly == [b_past_zone, d_past_zone]
    assert a_in_zone.state == "falling"
    assert b_past_zone.state == "missed"
    assert c_already_hit.state == "hit"
    assert d_past_zone.state == "missed"


# ---- outcome shape ---------------------------------------------------------


@pytest.mark.unit
def test_outcome_is_frozen_dataclass() -> None:
    o = Outcome(verdict=Verdict.WRONG_KEY)
    with pytest.raises(Exception):
        o.verdict = Verdict.HIT  # type: ignore[misc]


@pytest.mark.unit
def test_outcome_default_tile_is_none() -> None:
    assert Outcome(verdict=Verdict.WRONG_KEY).tile is None
