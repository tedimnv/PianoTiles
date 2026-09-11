"""Unit tests for the main-menu policy (`piano_tiles.components.main_menu`).

Covers the boot-screen content and the song-box geometry / hit-testing in
isolation. The renderer paints these and the orchestrator hit-tests clicks
against them, so both must agree on the same boxes.
"""

import pytest

from piano_tiles.components.main_menu import (
    instruction_lines,
    song_index_at,
    song_label,
    song_option_box,
)
from piano_tiles.config import (
    LANE_KEYS,
    PAUSE_KEY,
    SONG_OPTION_HEIGHT,
    SONG_OPTION_MARGIN_X,
    SONGS,
    WINDOW_W,
)

pytestmark = pytest.mark.unit


# ---- instruction lines ----------------------------------------------------


def test_instruction_lines_list_the_lane_keys_without_commas() -> None:
    lines = instruction_lines()
    assert lines[0] == "Play with D F J K"
    assert "," not in lines[0]


def test_instruction_lines_name_the_pause_key() -> None:
    assert instruction_lines()[1] == f"Press {PAUSE_KEY.upper()} to pause"


def test_instruction_lines_track_the_keymap() -> None:
    """Derived from config, so re-keying the game updates the menu for free."""
    for key in LANE_KEYS:
        assert key.upper() in instruction_lines()[0]


# ---- song label -----------------------------------------------------------


def test_song_label_is_title_dash_artist() -> None:
    assert song_label(SONGS[0]) == "Slow Dancing In The Dark - JOJI"


# ---- option box geometry --------------------------------------------------


def test_first_box_starts_at_the_left_margin_and_spans_the_inner_width() -> None:
    x, y, w, h = song_option_box(0)
    assert x == SONG_OPTION_MARGIN_X
    assert w == WINDOW_W - 2 * SONG_OPTION_MARGIN_X
    assert h == SONG_OPTION_HEIGHT


def test_boxes_stack_downward_without_overlapping() -> None:
    _, y0, _, h0 = song_option_box(0)
    _, y1, _, _ = song_option_box(1)
    assert y1 > y0 + h0  # the second box sits below the first, with a gap


# ---- hit-testing ----------------------------------------------------------


def test_click_inside_first_box_returns_index_zero() -> None:
    x, y, w, h = song_option_box(0)
    assert song_index_at((x + w // 2, y + h // 2)) == 0


def test_click_above_all_boxes_returns_none() -> None:
    x, y, w, h = song_option_box(0)
    assert song_index_at((x + w // 2, y - 5)) is None


def test_click_left_of_a_box_returns_none() -> None:
    x, y, w, h = song_option_box(0)
    assert song_index_at((x - 1, y + h // 2)) is None


def test_click_in_the_gap_between_boxes_returns_none() -> None:
    """Only meaningful with 2+ songs; with one song the gap is below box 0."""
    _, y0, _, h0 = song_option_box(0)
    cx = WINDOW_W // 2
    assert song_index_at((cx, y0 + h0 + 1)) is None


def test_click_on_an_empty_placeholder_slot_returns_none() -> None:
    """Slots past the end of SONGS are drawn but not selectable yet — clicking
    one does nothing."""
    x, y, w, h = song_option_box(len(SONGS))  # first empty slot
    assert song_index_at((x + w // 2, y + h // 2)) is None
