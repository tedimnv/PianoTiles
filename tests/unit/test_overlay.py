"""Unit tests for the overlay policy (`piano_tiles.components.overlay`).

Covers the decision layer — which color / message / alpha to show — in
isolation from pixel painting. The renderer-side tests in
`tests/ui/test_renderer.py` assert the painted pixels match.
"""

import pytest

from piano_tiles.components.overlay import OverlayInfo, overlay_for
from piano_tiles.config import (
    DEFAULT_PALETTE,
    MINT_BLUSH,
    PEACH_SORBET,
    RESTART_KEY,
)
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State

pytestmark = pytest.mark.unit


# ---- messages & default-palette colors ------------------------------------
#
# With no palette supplied, GameState falls back to DEFAULT_PALETTE, so the
# overlay colors are the classic theme's band colors.


def test_menu_overlay_uses_default_band_color_and_start_prompt() -> None:
    info = overlay_for(GameState(state=State.MENU))
    assert info == OverlayInfo(
        color=DEFAULT_PALETTE.menu_band,
        message=f"Press {RESTART_KEY.upper()} to start",
    )


def test_paused_overlay_uses_default_band_color_and_label() -> None:
    info = overlay_for(GameState(state=State.PAUSED))
    assert info == OverlayInfo(color=DEFAULT_PALETTE.paused_band, message="PAUSED")


def test_game_over_overlay_uses_default_band_color_and_label() -> None:
    info = overlay_for(GameState(state=State.GAME_OVER))
    assert info == OverlayInfo(
        color=DEFAULT_PALETTE.game_over_band, message="GAME OVER"
    )


# ---- band color follows the active palette --------------------------------
#
# Each overlay-bearing state reads its band color from the palette on the
# GameState, so a song's theme carries through to its screens.


@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET, DEFAULT_PALETTE])
def test_menu_band_color_tracks_palette(palette) -> None:
    info = overlay_for(GameState(state=State.MENU, palette=palette))
    assert info.color == palette.menu_band


@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET, DEFAULT_PALETTE])
def test_paused_band_color_tracks_palette(palette) -> None:
    info = overlay_for(GameState(state=State.PAUSED, palette=palette))
    assert info.color == palette.paused_band


@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET, DEFAULT_PALETTE])
def test_game_over_band_color_tracks_palette(palette) -> None:
    info = overlay_for(GameState(state=State.GAME_OVER, palette=palette))
    assert info.color == palette.game_over_band


def test_message_is_palette_independent() -> None:
    """Swapping the palette recolors the band but never changes the wording."""
    lav = overlay_for(GameState(state=State.GAME_OVER, palette=MINT_BLUSH))
    peach = overlay_for(GameState(state=State.GAME_OVER, palette=PEACH_SORBET))
    assert lav.message == peach.message == "GAME OVER"
    assert lav.color != peach.color


def test_playing_state_has_no_overlay() -> None:
    assert overlay_for(GameState(state=State.PLAYING)) is None


def test_dying_state_has_no_overlay() -> None:
    """During the wrong-key flash the overlay band is not yet shown."""
    assert overlay_for(GameState(state=State.DYING)) is None


def test_quit_state_has_no_overlay() -> None:
    assert overlay_for(GameState(state=State.QUIT)) is None


# ---- "no-fade" regression --------------------------------------------------
#
# Earlier versions faded GAME_OVER in over ~1 s. Against the dark background,
# the dim phase looked like a horizontal black stripe — the user-reported
# "black line for the first second". The contract now is: GAME_OVER appears
# at full opacity from frame one. The tests below pin that, so any future
# attempt to reintroduce a fade fails loudly.


def test_overlay_info_has_no_alpha_field() -> None:
    """No alpha plumbing on the overlay at all — there is no transparency state
    to expose because the overlay is always fully opaque. Any future fade has
    to first acknowledge that it's re-introducing the bug."""
    info = OverlayInfo(color=(0, 0, 0), message="x")
    assert not hasattr(info, "alpha")


def test_overlay_info_carries_no_scale_field() -> None:
    """Pin the absence of `scale` on `OverlayInfo` — scaling produced the small
    dark rectangle that initially looked like the black-line bug."""
    info = OverlayInfo(color=(0, 0, 0), message="x")
    assert not hasattr(info, "scale")


def test_game_state_carries_no_game_over_elapsed_field() -> None:
    """Pin the absence of `game_over_elapsed` on `GameState`. The timer existed
    to drive the fade — removing it makes a future fade impossible by default."""
    state = GameState(state=State.GAME_OVER)
    assert not hasattr(state, "game_over_elapsed")
