"""Unit tests for PhaseTracker — the runtime position within a PhaseSchedule."""

import pytest

from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.components.phase_tracker import PhaseTracker

pytestmark = pytest.mark.unit


def _schedule(*phases: Phase) -> PhaseSchedule:
    return PhaseSchedule(phases=phases)


def _two_phase_tracker() -> PhaseTracker:
    return PhaseTracker(
        _schedule(
            Phase(speed=240.0, duration=2.0),
            Phase(speed=480.0, duration=3.0),
        )
    )


# ---- initial state --------------------------------------------------------


def test_initial_phase_number_is_one() -> None:
    assert _two_phase_tracker().phase_number == 1


def test_initial_current_phase_is_the_first_phase() -> None:
    tracker = _two_phase_tracker()
    assert tracker.current_phase.speed == 240.0


# ---- advance_play / auto-advance -----------------------------------------


def test_advance_play_returns_none_while_phase_duration_remains() -> None:
    tracker = _two_phase_tracker()
    assert tracker.advance_play(0.5) is None
    assert tracker.advance_play(1.0) is None
    assert tracker.phase_number == 1


def test_advance_play_returns_leftover_when_phase_advances() -> None:
    tracker = _two_phase_tracker()
    tracker.advance_play(1.0)
    leftover = tracker.advance_play(1.5)  # crosses boundary at 2.0; 0.5 spills over
    assert leftover == pytest.approx(0.5)
    assert tracker.phase_number == 2
    assert tracker.current_phase.speed == 480.0


def test_advance_play_returns_none_on_the_final_phase_no_matter_how_long() -> None:
    """The schedule sticks to the last phase forever — no transition can fire."""
    tracker = PhaseTracker(_schedule(Phase(speed=200.0, duration=1.0)))
    assert tracker.advance_play(100.0) is None
    assert tracker.phase_number == 1


def test_advance_play_carries_overshoot_into_next_phase() -> None:
    """A dt that crosses a phase boundary keeps the leftover time on the new phase."""
    tracker = _two_phase_tracker()
    # phase 1 duration is 2.0; dt of 2.5 advances to phase 2 with 0.5s already elapsed
    assert tracker.advance_play(2.5) == pytest.approx(0.5)
    # Another 2.4s on phase 2 (duration 3.0) — still in phase 2 (0.5 + 2.4 = 2.9 < 3.0)
    assert tracker.advance_play(2.4) is None
    assert tracker.phase_number == 2
    # One more 0.2s — now 2.9 + 0.2 = 3.1 ≥ 3.0 BUT there's no phase 3, so still None
    assert tracker.advance_play(0.2) is None


def test_advance_play_only_advances_one_phase_per_call_even_with_huge_dt() -> None:
    """If dt covers multiple phases, we still cross one boundary per call.

    The banner and spawner only need to fire once per crossing; the orchestrator
    can call again next frame to catch up if needed.
    """
    tracker = PhaseTracker(
        _schedule(
            Phase(speed=200.0, duration=1.0),
            Phase(speed=300.0, duration=1.0),
            Phase(speed=400.0, duration=1.0),
        )
    )
    leftover = tracker.advance_play(10.0)
    assert leftover is not None
    assert tracker.phase_number == 2  # not 3


# ---- reset ----------------------------------------------------------------


def test_reset_returns_to_phase_one() -> None:
    tracker = _two_phase_tracker()
    tracker.advance_play(2.5)
    assert tracker.phase_number == 2
    tracker.reset()
    assert tracker.phase_number == 1
    assert tracker.current_phase.speed == 240.0
