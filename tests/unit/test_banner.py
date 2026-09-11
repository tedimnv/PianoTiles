"""Unit tests for the phase-banner policy (`piano_tiles.components.banner`)."""

import pytest

from piano_tiles.components.banner import (
    BANNER_TOTAL_SECONDS,
    BannerInfo,
    banner_for,
)
from piano_tiles.config import (
    BANNER_FADE_IN_SECONDS,
    BANNER_FADE_OUT_SECONDS,
    BANNER_HOLD_SECONDS,
    BANNER_ZOOM_FROM,
    BANNER_ZOOM_TO,
    PHASE_BANNER_ICONS,
)
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State

pytestmark = pytest.mark.unit


def _at(phase: int, elapsed: float) -> GameState:
    return GameState(
        state=State.PLAYING, banner_phase_number=phase, banner_elapsed=elapsed
    )


HOLD_MIDPOINT = BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS / 2.0
FADE_OUT_MID = BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS + BANNER_FADE_OUT_SECONDS / 2.0
FADE_OUT_END = BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS + BANNER_FADE_OUT_SECONDS


# ---- absence ---------------------------------------------------------------


def test_no_banner_when_phase_number_is_none() -> None:
    assert banner_for(GameState(state=State.PLAYING)) is None


def test_no_banner_when_elapsed_is_none() -> None:
    """Even when the phase number is set, missing elapsed means we haven't started."""
    assert banner_for(GameState(state=State.PLAYING, banner_phase_number=2)) is None


def test_no_banner_for_unknown_phase_number() -> None:
    """A phase number not in PHASE_BANNER_ICONS doesn't crash — it just goes blank."""
    assert banner_for(_at(phase=99, elapsed=0.5)) is None


def test_no_banner_before_t0() -> None:
    assert banner_for(_at(phase=2, elapsed=-0.01)) is None


def test_no_banner_after_total_window() -> None:
    assert banner_for(_at(phase=2, elapsed=BANNER_TOTAL_SECONDS + 0.01)) is None


def test_total_duration_is_three_seconds() -> None:
    """The whole banner — fade-in + hold + fade-out — fits in exactly 3 seconds."""
    assert BANNER_TOTAL_SECONDS == pytest.approx(3.0)


# ---- icon mapping (drives which art shows) --------------------------------


def test_phase_one_has_no_banner_because_it_is_the_starting_phase() -> None:
    """We start in phase 1, so no banner ever fires for it."""
    assert banner_for(_at(phase=1, elapsed=BANNER_FADE_IN_SECONDS)) is None


@pytest.mark.parametrize("phase,expected_count", [(2, 1), (3, 2), (4, 3)])
def test_phases_2_to_4_use_the_star_icon(phase: int, expected_count: int) -> None:
    info = banner_for(_at(phase=phase, elapsed=BANNER_FADE_IN_SECONDS))
    assert info is not None
    assert info.icon == "star"
    assert info.count == expected_count


@pytest.mark.parametrize("phase,expected_count", [(5, 1), (6, 2), (7, 3)])
def test_phases_5_to_7_use_the_crown_icon(phase: int, expected_count: int) -> None:
    info = banner_for(_at(phase=phase, elapsed=BANNER_FADE_IN_SECONDS))
    assert info is not None
    assert info.icon == "crown"
    assert info.count == expected_count


def test_banner_icons_match_config_mapping() -> None:
    """The banner agrees with the config table — no hidden overrides."""
    for phase, (icon, count) in PHASE_BANNER_ICONS.items():
        info = banner_for(_at(phase=phase, elapsed=BANNER_FADE_IN_SECONDS))
        assert info is not None
        assert info.icon == icon
        assert info.count == count


# ---- fade-in profile (0 → 255 over BANNER_FADE_IN_SECONDS) ----------------


def test_alpha_is_zero_at_t0() -> None:
    info = banner_for(_at(phase=2, elapsed=0.0))
    assert info is not None
    assert info.alpha == 0


def test_alpha_ramps_linearly_through_fade_in_window() -> None:
    info_half = banner_for(_at(phase=2, elapsed=BANNER_FADE_IN_SECONDS / 2.0))
    info_full = banner_for(_at(phase=2, elapsed=BANNER_FADE_IN_SECONDS))
    assert info_half is not None and info_full is not None
    assert info_half.alpha == pytest.approx(127, abs=1)
    assert info_full.alpha == 255


def test_scale_zooms_in_from_zoom_from_to_one_over_fade_in_window() -> None:
    info_start = banner_for(_at(phase=2, elapsed=0.0))
    info_full = banner_for(_at(phase=2, elapsed=BANNER_FADE_IN_SECONDS))
    assert info_start is not None and info_full is not None
    assert info_start.scale == pytest.approx(BANNER_ZOOM_FROM)
    assert info_full.scale == pytest.approx(1.0)


# ---- hold phase (alpha 255, scale 1.0) -----------------------------------


def test_hold_phase_keeps_alpha_at_full() -> None:
    info = banner_for(_at(phase=2, elapsed=HOLD_MIDPOINT))
    assert info is not None
    assert info.alpha == 255


def test_hold_phase_keeps_scale_at_one() -> None:
    info = banner_for(_at(phase=2, elapsed=HOLD_MIDPOINT))
    assert info is not None
    assert info.scale == pytest.approx(1.0)


def test_hold_phase_runs_for_the_full_configured_duration() -> None:
    """At the very last instant of the hold, before fade-out starts."""
    just_before_fade_out = BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS - 1e-6
    info = banner_for(_at(phase=2, elapsed=just_before_fade_out))
    assert info is not None
    assert info.alpha == 255
    assert info.scale == pytest.approx(1.0)


# ---- fade-out profile (255 → 0 over BANNER_FADE_OUT_SECONDS) --------------


def test_alpha_fades_through_fade_out_window() -> None:
    info_quarter_out = banner_for(_at(phase=2, elapsed=FADE_OUT_MID))
    assert info_quarter_out is not None
    assert info_quarter_out.alpha == pytest.approx(127, abs=1)


def test_scale_zooms_out_through_fade_out_window() -> None:
    info_full = banner_for(_at(phase=2, elapsed=BANNER_FADE_IN_SECONDS))
    info_quarter_out = banner_for(_at(phase=2, elapsed=FADE_OUT_MID))
    assert info_full is not None and info_quarter_out is not None
    assert info_full.scale == pytest.approx(1.0)
    assert info_quarter_out.scale == pytest.approx((1.0 + BANNER_ZOOM_TO) / 2.0)


def test_just_before_total_window_end_is_still_visible_but_tiny() -> None:
    just_before_end = FADE_OUT_END - 1e-6
    info = banner_for(_at(phase=2, elapsed=just_before_end))
    assert info is not None
    # Alpha very close to 0, scale close to ZOOM_TO.
    assert info.alpha == pytest.approx(0, abs=1)
    assert info.scale == pytest.approx(BANNER_ZOOM_TO, abs=0.01)


# ---- BannerInfo shape -----------------------------------------------------


def test_banner_info_is_frozen() -> None:
    info = BannerInfo(icon="star", count=1, alpha=128, scale=1.0)
    with pytest.raises(Exception):
        info.alpha = 0  # type: ignore[misc]
