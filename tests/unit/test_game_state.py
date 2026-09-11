import dataclasses

import pytest

from piano_tiles.config import HIT_ZONE_BOTTOM, HIT_ZONE_TOP
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile


@pytest.mark.unit
def test_game_state_is_frozen() -> None:
    s = GameState(state=State.MENU)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.score = 5  # type: ignore[misc]


@pytest.mark.unit
def test_default_tiles_is_empty_tuple() -> None:
    s = GameState(state=State.MENU)
    assert s.tiles == ()


@pytest.mark.unit
def test_default_score_is_zero() -> None:
    assert GameState(state=State.MENU).score == 0


@pytest.mark.unit
def test_default_hit_zone_matches_config() -> None:
    s = GameState(state=State.PLAYING)
    assert s.hit_zone_top == HIT_ZONE_TOP
    assert s.hit_zone_bottom == HIT_ZONE_BOTTOM


@pytest.mark.unit
def test_fields_are_preserved() -> None:
    tile = Tile(lane=2, y=100.0, height=80.0, speed=300.0)
    s = GameState(
        state=State.PLAYING,
        tiles=(tile,),
        score=42,
        hit_zone_top=500.0,
        hit_zone_bottom=600.0,
    )
    assert s.state == State.PLAYING
    assert s.tiles == (tile,)
    assert s.score == 42
    assert s.hit_zone_top == 500.0
    assert s.hit_zone_bottom == 600.0


@pytest.mark.unit
def test_two_game_states_with_same_fields_are_equal() -> None:
    a = GameState(state=State.MENU, score=3)
    b = GameState(state=State.MENU, score=3)
    assert a == b


@pytest.mark.unit
def test_banner_fields_default_to_none() -> None:
    s = GameState(state=State.PLAYING)
    assert s.banner_phase_number is None
    assert s.banner_elapsed is None


@pytest.mark.unit
def test_banner_fields_are_carried_through() -> None:
    s = GameState(state=State.PLAYING, banner_phase_number=3, banner_elapsed=0.5)
    assert s.banner_phase_number == 3
    assert s.banner_elapsed == 0.5


@pytest.mark.unit
def test_dying_fields_default_to_none() -> None:
    s = GameState(state=State.PLAYING)
    assert s.dying_phantom is None
    assert s.dying_elapsed is None


@pytest.mark.unit
def test_dying_fields_are_carried_through() -> None:
    phantom = Tile(lane=1, y=580.0, height=80.0, speed=300.0)
    s = GameState(state=State.DYING, dying_phantom=phantom, dying_elapsed=0.2)
    assert s.dying_phantom is phantom
    assert s.dying_elapsed == 0.2


@pytest.mark.unit
def test_game_state_has_no_game_over_timer() -> None:
    """GAME_OVER is instantaneous; no per-frame timer field is needed."""
    assert not hasattr(GameState(state=State.MENU), "game_over_elapsed")
