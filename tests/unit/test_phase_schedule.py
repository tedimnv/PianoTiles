"""Unit tests for Phase and PhaseSchedule."""

import pytest

from piano_tiles.components.phase_schedule import Phase, PhaseSchedule
from piano_tiles.config import PHASES

pytestmark = pytest.mark.unit


# ---- Phase validation -----------------------------------------------------


def test_phase_rejects_non_positive_speed() -> None:
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        Phase(speed=0.0, duration=10.0)
    with pytest.raises(ValueError, match=r"speed must be > 0"):
        Phase(speed=-1.0, duration=10.0)


def test_phase_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match=r"duration must be > 0"):
        Phase(speed=200.0, duration=0.0)
    with pytest.raises(ValueError, match=r"duration must be > 0"):
        Phase(speed=200.0, duration=-5.0)


def test_phase_is_frozen() -> None:
    import dataclasses

    p = Phase(speed=200.0, duration=10.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.speed = 300.0  # type: ignore[misc]


# ---- PhaseSchedule validation --------------------------------------------


def test_schedule_rejects_empty_phases() -> None:
    with pytest.raises(ValueError, match=r"at least one Phase"):
        PhaseSchedule(phases=())


# ---- accessors -----------------------------------------------------------


def _example_schedule() -> PhaseSchedule:
    return PhaseSchedule(
        phases=(
            Phase(speed=240.0, duration=30.0),
            Phase(speed=300.0, duration=30.0),
            Phase(speed=360.0, duration=30.0),
        ),
    )


def test_count_reflects_number_of_phases() -> None:
    assert _example_schedule().count == 3


def test_phase_lookup_by_index() -> None:
    schedule = _example_schedule()
    assert schedule.phase(0).speed == 240.0
    assert schedule.phase(1).speed == 300.0
    assert schedule.phase(2).speed == 360.0


def test_phase_index_above_count_clamps_to_last_phase() -> None:
    """Past the last phase, the schedule keeps returning the last phase's settings."""
    schedule = _example_schedule()
    assert schedule.phase(3) is schedule.phase(2)
    assert schedule.phase(100) is schedule.phase(2)


def test_negative_index_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"phase index must be >= 0"):
        _example_schedule().phase(-1)


def test_has_phase_after_is_true_when_more_phases_remain() -> None:
    schedule = _example_schedule()
    assert schedule.has_phase_after(0) is True
    assert schedule.has_phase_after(1) is True


def test_has_phase_after_is_false_on_or_past_the_last_phase() -> None:
    schedule = _example_schedule()
    assert schedule.has_phase_after(2) is False
    assert schedule.has_phase_after(100) is False


# ---- from_config factory --------------------------------------------------


def test_from_config_builds_phases_from_config_PHASES_tuple() -> None:
    schedule = PhaseSchedule.from_config()
    assert schedule.count == len(PHASES)
    for idx, (speed, duration) in enumerate(PHASES):
        assert schedule.phase(idx).speed == speed
        assert schedule.phase(idx).duration == duration
