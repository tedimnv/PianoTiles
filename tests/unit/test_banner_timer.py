"""Unit tests for BannerTimer — the runtime state of the phase-change banner."""

import pytest

from piano_tiles.components.banner import BANNER_TOTAL_SECONDS
from piano_tiles.components.banner_timer import BannerTimer

pytestmark = pytest.mark.unit


# ---- initial state --------------------------------------------------------


def test_initial_state_is_inactive() -> None:
    timer = BannerTimer()
    assert timer.is_active is False
    assert timer.phase_number is None
    assert timer.elapsed is None


# ---- start ----------------------------------------------------------------


def test_start_activates_the_timer_with_zero_elapsed_by_default() -> None:
    timer = BannerTimer()
    timer.start(phase_number=2)
    assert timer.is_active is True
    assert timer.phase_number == 2
    assert timer.elapsed == 0.0


def test_start_accepts_initial_elapsed_for_mid_tick_boundary_crossings() -> None:
    """When a phase boundary is crossed mid-tick, the banner must time-stamp at
    the crossing instant — not be artificially set back to zero."""
    timer = BannerTimer()
    timer.start(phase_number=3, initial_elapsed=0.08)
    assert timer.elapsed == pytest.approx(0.08)


def test_start_can_replace_a_running_banner() -> None:
    """If two phase boundaries fire in quick succession, the later one wins."""
    timer = BannerTimer()
    timer.start(phase_number=2, initial_elapsed=0.5)
    timer.start(phase_number=3, initial_elapsed=0.0)
    assert timer.phase_number == 3
    assert timer.elapsed == 0.0


# ---- tick -----------------------------------------------------------------


def test_tick_is_a_noop_when_inactive() -> None:
    timer = BannerTimer()
    timer.tick(1.0)
    assert timer.is_active is False
    assert timer.elapsed is None


def test_tick_advances_elapsed_while_active() -> None:
    timer = BannerTimer()
    timer.start(phase_number=2)
    timer.tick(0.25)
    assert timer.elapsed == pytest.approx(0.25)
    timer.tick(0.50)
    assert timer.elapsed == pytest.approx(0.75)


def test_tick_clears_the_timer_when_total_window_expires() -> None:
    timer = BannerTimer()
    timer.start(phase_number=2)
    timer.tick(BANNER_TOTAL_SECONDS + 0.01)
    assert timer.is_active is False
    assert timer.phase_number is None
    assert timer.elapsed is None


def test_tick_at_exactly_the_total_window_boundary_clears() -> None:
    timer = BannerTimer()
    timer.start(phase_number=2)
    timer.tick(BANNER_TOTAL_SECONDS)
    assert timer.is_active is False


def test_tick_just_below_total_window_keeps_running() -> None:
    timer = BannerTimer()
    timer.start(phase_number=2)
    timer.tick(BANNER_TOTAL_SECONDS - 0.001)
    assert timer.is_active is True
    assert timer.elapsed == pytest.approx(BANNER_TOTAL_SECONDS - 0.001)


# ---- clear ----------------------------------------------------------------


def test_clear_returns_the_timer_to_its_initial_state() -> None:
    timer = BannerTimer()
    timer.start(phase_number=5, initial_elapsed=1.0)
    timer.clear()
    assert timer.is_active is False
    assert timer.phase_number is None
    assert timer.elapsed is None


def test_clear_is_idempotent() -> None:
    """Calling clear on an already-inactive timer must not raise."""
    timer = BannerTimer()
    timer.clear()
    timer.clear()
    assert timer.is_active is False
