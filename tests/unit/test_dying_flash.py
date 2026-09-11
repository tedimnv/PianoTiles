"""Unit tests for DyingFlash — the runtime state of the wrong-key red flash."""

import pytest

from piano_tiles.components.dying_flash import DyingFlash
from piano_tiles.config import WRONG_KEY_FLASH_DURATION
from piano_tiles.models.tile import Tile

pytestmark = pytest.mark.unit


def _phantom(lane: int = 0) -> Tile:
    return Tile(lane=lane, y=580.0, height=80.0, speed=300.0)


# ---- initial state --------------------------------------------------------


def test_initial_state_is_inactive() -> None:
    flash = DyingFlash()
    assert flash.is_active is False
    assert flash.phantom is None
    assert flash.elapsed is None


# ---- begin ----------------------------------------------------------------


def test_begin_activates_the_flash_with_the_supplied_phantom() -> None:
    flash = DyingFlash()
    phantom = _phantom(lane=2)
    flash.begin(phantom)
    assert flash.is_active is True
    assert flash.phantom is phantom
    assert flash.elapsed == 0.0


# ---- tick -----------------------------------------------------------------


def test_tick_returns_false_when_inactive() -> None:
    """The orchestrator can tick blindly in the DYING state without a guard."""
    flash = DyingFlash()
    assert flash.tick(0.1) is False


def test_tick_returns_false_while_flash_is_still_running() -> None:
    flash = DyingFlash()
    flash.begin(_phantom())
    assert flash.tick(WRONG_KEY_FLASH_DURATION / 4) is False
    assert flash.elapsed == pytest.approx(WRONG_KEY_FLASH_DURATION / 4)
    assert flash.is_active is True


def test_tick_returns_true_when_the_flash_finishes_this_tick() -> None:
    flash = DyingFlash()
    flash.begin(_phantom())
    assert flash.tick(WRONG_KEY_FLASH_DURATION + 0.01) is True


def test_finishing_tick_clears_the_flash() -> None:
    flash = DyingFlash()
    flash.begin(_phantom())
    flash.tick(WRONG_KEY_FLASH_DURATION + 0.01)
    assert flash.is_active is False
    assert flash.phantom is None
    assert flash.elapsed is None


def test_tick_at_exactly_the_flash_boundary_finishes() -> None:
    flash = DyingFlash()
    flash.begin(_phantom())
    assert flash.tick(WRONG_KEY_FLASH_DURATION) is True


# ---- clear ----------------------------------------------------------------


def test_clear_returns_the_flash_to_its_initial_state() -> None:
    flash = DyingFlash()
    flash.begin(_phantom())
    flash.tick(WRONG_KEY_FLASH_DURATION / 4)
    flash.clear()
    assert flash.is_active is False
    assert flash.phantom is None
    assert flash.elapsed is None


def test_clear_is_idempotent() -> None:
    flash = DyingFlash()
    flash.clear()
    flash.clear()
    assert flash.is_active is False
