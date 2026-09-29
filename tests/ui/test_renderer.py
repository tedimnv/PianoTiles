import time

import pytest

from piano_tiles.components.renderer import Renderer
from piano_tiles.config import (
    BG_COLOR,
    GAME_OVER_OVERLAY_COLOR,
    HIT_ZONE_BOTTOM,
    HIT_ZONE_COLOR,
    HIT_ZONE_TOP,
    LANE_WIDTH,
    MINT_BLUSH,
    MENU_OVERLAY_COLOR,
    OVERLAY_BAND_BOTTOM,
    OVERLAY_BAND_TOP,
    OVERLAY_TEXT_COLOR,
    PAUSED_OVERLAY_COLOR,
    PEACH_SORBET,
    SCORE_POS_X,
    SCORE_POS_Y,
    TILE_FALLING_COLOR,
    TILE_HELD_COLOR,
    WINDOW_W,
    WRONG_KEY_FLASH_COLOR,
)
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile


def _lane_center_x(lane: int) -> int:
    return lane * LANE_WIDTH + LANE_WIDTH // 2


def _rgb(surface, x: int, y: int) -> tuple[int, int, int]:
    return tuple(surface.get_at((x, y))[:3])  # type: ignore[return-value]


def _any_non_bg_pixel(surface, x0: int, y0: int, w: int, h: int) -> bool:
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if _rgb(surface, x, y) != BG_COLOR:
                return True
    return False


def _band_center_y() -> int:
    return (OVERLAY_BAND_TOP + OVERLAY_BAND_BOTTOM) // 2


# ---- main menu -------------------------------------------------------------


@pytest.mark.ui
def test_main_menu_draws_song_box_in_option_color(headless_surface) -> None:
    """The clickable song box is painted in the muted-purple option color."""
    from piano_tiles.components.main_menu import song_option_box
    from piano_tiles.config import SONG_OPTION_COLOR

    renderer = Renderer()
    renderer.render(GameState(state=State.MAIN_MENU), headless_surface)
    x, y, w, h = song_option_box(0)
    # Left edge of the box, vertically centered — away from the centered label.
    assert _rgb(headless_surface, x + 4, y + h // 2) == SONG_OPTION_COLOR


@pytest.mark.ui
def test_main_menu_draws_empty_slot_in_empty_color(headless_surface) -> None:
    """Slots past the end of SONGS render as empty placeholder boxes."""
    from piano_tiles.components.main_menu import song_option_box
    from piano_tiles.config import SONG_EMPTY_SLOT_COLOR, SONGS

    renderer = Renderer()
    renderer.render(GameState(state=State.MAIN_MENU), headless_surface)
    x, y, w, h = song_option_box(len(SONGS))  # first empty slot
    assert _rgb(headless_surface, x + 4, y + h // 2) == SONG_EMPTY_SLOT_COLOR


@pytest.mark.ui
def test_main_menu_paints_title_text_in_dark_ink(headless_surface) -> None:
    """Against the light photo background, the title is near-black."""
    from piano_tiles.config import MAIN_MENU_TITLE_Y

    renderer = Renderer()
    renderer.render(GameState(state=State.MAIN_MENU), headless_surface)
    has_dark_pixel = any(
        sum(_rgb(headless_surface, x, MAIN_MENU_TITLE_Y)) < 120
        for x in range(WINDOW_W)
    )
    assert has_dark_pixel, "expected near-black title text against the light photo"


# ---- background / MENU -----------------------------------------------------


@pytest.mark.ui
def test_menu_state_fills_background_with_bg_color(headless_surface) -> None:
    renderer = Renderer()
    state = GameState(state=State.MENU)
    renderer.render(state, headless_surface)
    # A pixel above the overlay band and outside the score text (mid-y=200) is just background.
    assert _rgb(headless_surface, 200, 200) == BG_COLOR


@pytest.mark.ui
def test_menu_state_overlay_band_is_menu_color(headless_surface) -> None:
    """The default-palette MENU band is the flat classic menu color."""
    renderer = Renderer()
    renderer.render(GameState(state=State.MENU), headless_surface)
    # Sample 10 px from left edge — far from the centered text.
    assert _rgb(headless_surface, 10, _band_center_y()) == MENU_OVERLAY_COLOR


@pytest.mark.ui
def test_menu_state_overlay_text_region_is_non_background(headless_surface) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.MENU), headless_surface)
    # Center of the band contains the text — must differ from the bare background.
    assert _rgb(headless_surface, WINDOW_W // 2, _band_center_y()) != BG_COLOR


# ---- tiles -----------------------------------------------------------------


@pytest.mark.ui
def test_falling_tile_in_lane_2_paints_that_column_only(headless_surface) -> None:
    renderer = Renderer()
    tile = Tile(lane=2, y=100.0, height=80.0, speed=300.0)
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)

    y = 140  # within the tile's vertical span (100..180)
    assert _rgb(headless_surface, _lane_center_x(2), y) == TILE_FALLING_COLOR
    for other_lane in (0, 1, 3):
        assert _rgb(headless_surface, _lane_center_x(other_lane), y) == BG_COLOR


@pytest.mark.ui
def test_held_tile_with_partial_overlay_paints_cyan_top_green_bottom(headless_surface) -> None:
    """A long tile mid-hold splits into a cyan top and a green bottom: cyan
    covers (tile.height - held_amount) at the top, green covers held_amount
    at the bottom. Both bands together exactly fill the tile."""
    renderer = Renderer()
    tile = Tile(lane=2, y=100.0, height=200.0, speed=300.0, segments=2, held=True)
    tile.grow_held(80.0)  # green takes the bottom 80 px (y=220..300)
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    # Inside the cyan band (top portion) → falling color.
    assert _rgb(headless_surface, _lane_center_x(2), 150) == TILE_FALLING_COLOR
    # Inside the green band (bottom portion) → held color.
    assert _rgb(headless_surface, _lane_center_x(2), 280) == TILE_HELD_COLOR
    assert TILE_HELD_COLOR != TILE_FALLING_COLOR  # sanity


@pytest.mark.ui
def test_held_tile_visual_top_matches_tile_top_exactly(headless_surface) -> None:
    """The top of the green overlay must sit at `tile.bottom - held_amount`,
    never crossing the tile's top edge. Sampling one row above the tile's
    top must show background, not held color."""
    renderer = Renderer()
    tile = Tile(lane=0, y=300.0, height=180.0, speed=300.0, segments=2, held=True)
    tile.grow_held(180.0)  # overlay covers the whole tile
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    # Inside the tile → held color.
    assert _rgb(headless_surface, _lane_center_x(0), 301) == TILE_HELD_COLOR
    # One pixel above the tile's top → must NOT be held color.
    assert _rgb(headless_surface, _lane_center_x(0), 299) != TILE_HELD_COLOR


@pytest.mark.ui
def test_held_overlay_never_paints_past_the_tile_borders(headless_surface) -> None:
    """The user-facing invariant: the green overlay sits inside the tile's
    rectangle no matter how big held_amount has grown — capped at
    original_height. Pixels outside the tile's bounds (left/right of lane,
    above tile.top, below tile.bottom) must not be held color."""
    renderer = Renderer()
    tile = Tile(lane=1, y=200.0, height=180.0, speed=300.0, segments=2, held=True)
    tile.grow_held(99999.0)  # extreme; the cap at original_height kicks in
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    # Inside → held color.
    assert _rgb(headless_surface, _lane_center_x(1), 280) == TILE_HELD_COLOR
    # Above tile.top → background.
    assert _rgb(headless_surface, _lane_center_x(1), 199) != TILE_HELD_COLOR
    # Below tile.bottom → background.
    assert _rgb(headless_surface, _lane_center_x(1), 380) != TILE_HELD_COLOR


@pytest.mark.ui
def test_released_long_tile_keeps_its_frozen_overlay_painted(headless_surface) -> None:
    """After release the tile is `hit` (held=False), but its held_amount is
    frozen — the renderer must still paint the green band at the bottom and
    cyan above it. This is exactly what the player asked for: 'green stops
    growing and stays where it is'."""
    renderer = Renderer()
    tile = Tile(lane=3, y=100.0, height=200.0, speed=300.0, segments=2)
    tile.mark_held()
    tile.grow_held(60.0)
    tile.mark_hit()  # release
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, _lane_center_x(3), 130) == TILE_FALLING_COLOR
    assert _rgb(headless_surface, _lane_center_x(3), 270) == TILE_HELD_COLOR


@pytest.mark.ui
def test_short_tile_fully_held_renders_in_held_color(headless_surface) -> None:
    """A hit short tile is filled with the overlay (held_amount = height), so
    the renderer paints it entirely in the held color — the same colour as a
    fully-held long tile."""
    renderer = Renderer()
    tile = Tile(lane=0, y=100.0, height=80.0, speed=300.0)
    tile.held_amount = tile.original_height
    tile.mark_hit()  # state=hit, held=False; held_amount untouched
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, _lane_center_x(0), 140) == TILE_HELD_COLOR
    assert TILE_HELD_COLOR != TILE_FALLING_COLOR  # sanity


@pytest.mark.ui
def test_missed_tile_is_not_drawn(headless_surface) -> None:
    """Missed tiles are removed from view — sampling their bbox shows background."""
    renderer = Renderer()
    tile = Tile(lane=1, y=100.0, height=80.0, speed=300.0, state="missed")
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, _lane_center_x(1), 140) == BG_COLOR


# ---- hit zone --------------------------------------------------------------


@pytest.mark.ui
def test_hit_zone_band_spans_full_width(headless_surface) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.PLAYING), headless_surface)
    mid_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) // 2
    # Sample every lane's center column inside the band.
    for lane in range(4):
        assert _rgb(headless_surface, _lane_center_x(lane), mid_y) == HIT_ZONE_COLOR
    # And both window edges.
    assert _rgb(headless_surface, 0, mid_y) == HIT_ZONE_COLOR
    assert _rgb(headless_surface, WINDOW_W - 1, mid_y) == HIT_ZONE_COLOR


@pytest.mark.ui
def test_hit_zone_does_not_bleed_above_top(headless_surface) -> None:
    """Pixels just above HIT_ZONE_TOP must still be background."""
    renderer = Renderer()
    renderer.render(GameState(state=State.PLAYING), headless_surface)
    assert _rgb(headless_surface, _lane_center_x(0), HIT_ZONE_TOP - 1) == BG_COLOR


# ---- score -----------------------------------------------------------------


@pytest.mark.ui
def test_score_text_region_is_non_background_when_score_is_positive(
    headless_surface,
) -> None:
    renderer = Renderer()
    state = GameState(state=State.PLAYING, score=42)
    renderer.render(state, headless_surface)
    # Modest box around the score's top-left corner.
    assert _any_non_bg_pixel(
        headless_surface, SCORE_POS_X, SCORE_POS_Y, 60, 40
    )


# ---- per-state overlays ----------------------------------------------------


@pytest.mark.ui
def test_game_over_overlay_uses_game_over_color(headless_surface) -> None:
    """The default-palette band fills with the game-over color the instant the
    state enters."""
    renderer = Renderer()
    renderer.render(
        GameState(state=State.GAME_OVER, score=10),
        headless_surface,
    )
    assert _rgb(headless_surface, 10, _band_center_y()) == GAME_OVER_OVERLAY_COLOR


def _has_color_in_rows(surface, y0: int, y1: int, color) -> bool:
    """True if any pixel in the horizontal strip [y0, y1) matches `color`."""
    for y in range(y0, y1):
        for x in range(WINDOW_W):
            if _rgb(surface, x, y) == color:
                return True
    return False


@pytest.mark.ui
def test_game_over_overlay_paints_main_menu_hint_below_the_label(headless_surface) -> None:
    """The GAME_OVER band carries a small white hint beneath the main label. We
    sample the lower strip of the band (below where the big text sits) for the
    overlay text color."""
    renderer = Renderer()
    renderer.render(GameState(state=State.GAME_OVER, score=10), headless_surface)
    subtitle_strip_top = _band_center_y() + 15
    assert _has_color_in_rows(
        headless_surface, subtitle_strip_top, OVERLAY_BAND_BOTTOM, OVERLAY_TEXT_COLOR
    )


@pytest.mark.ui
def test_paused_overlay_has_no_subtitle_strip(headless_surface) -> None:
    """PAUSED shows no secondary hint — the lower band strip is bare of text."""
    renderer = Renderer()
    renderer.render(GameState(state=State.PAUSED), headless_surface)
    subtitle_strip_top = _band_center_y() + 15
    assert not _has_color_in_rows(
        headless_surface, subtitle_strip_top, OVERLAY_BAND_BOTTOM, OVERLAY_TEXT_COLOR
    )


@pytest.mark.ui
def test_paused_overlay_uses_paused_color(headless_surface) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.PAUSED), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == PAUSED_OVERLAY_COLOR


@pytest.mark.ui
def test_playing_state_has_no_overlay_band(headless_surface) -> None:
    """In PLAYING, the band area is just background (no overlay drawn)."""
    renderer = Renderer()
    renderer.render(GameState(state=State.PLAYING), headless_surface)
    color = _rgb(headless_surface, 10, _band_center_y())
    assert color == BG_COLOR
    assert color not in (
        MENU_OVERLAY_COLOR,
        PAUSED_OVERLAY_COLOR,
        GAME_OVER_OVERLAY_COLOR,
    )


# ---- game-over: no fade phase --------------------------------------------
#
# Regression tests for the "black line for the first second" bug. Earlier
# versions faded GAME_OVER in over ~1 s; against the dark background the dim
# phase looked like a horizontal black stripe. The contract now is: GAME_OVER
# appears at full opacity from the very first rendered frame.


@pytest.mark.ui
def test_game_over_overlay_is_fully_opaque_from_frame_one(headless_surface) -> None:
    """The first frame after entering GAME_OVER already shows the full color band.

    There must be no intermediate frame where the band reads as a dark blend of
    GAME_OVER_OVERLAY_COLOR and BG_COLOR — that intermediate frame was what
    looked like a black line across the screen.
    """
    renderer = Renderer()
    renderer.render(GameState(state=State.GAME_OVER), headless_surface)
    band_y = _band_center_y()
    # Sample the band edge (well left of the centred text) — should already be
    # full GAME_OVER_OVERLAY_COLOR, not a blend.
    assert _rgb(headless_surface, 10, band_y) == GAME_OVER_OVERLAY_COLOR
    # And the right edge.
    assert _rgb(headless_surface, WINDOW_W - 6, band_y) == GAME_OVER_OVERLAY_COLOR


# ---- wrong-key phantom ----------------------------------------------------


@pytest.mark.ui
def test_dying_phantom_is_painted_red_at_the_start_of_the_flash(headless_surface) -> None:
    """On the first ON beat of the flash, the phantom tile is visible in red."""
    renderer = Renderer()
    phantom = Tile(lane=1, y=580.0, height=80.0, speed=300.0)
    state = GameState(
        state=State.DYING, dying_phantom=phantom, dying_elapsed=0.0
    )
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, _lane_center_x(1), 600) == WRONG_KEY_FLASH_COLOR


@pytest.mark.ui
def test_dying_phantom_disappears_on_the_off_beat(headless_surface) -> None:
    """Between flash beats, the phantom isn't painted — its column shows the hit zone."""
    renderer = Renderer()
    phantom = Tile(lane=1, y=580.0, height=80.0, speed=300.0)
    # WRONG_KEY_FLASH_DURATION = 0.6, FLASH_COUNT = 3, so each beat = 0.6 / 6 = 0.1s
    # Off beats are slots 1, 3, 5 — i.e. elapsed in [0.1, 0.2) is off.
    state = GameState(
        state=State.DYING, dying_phantom=phantom, dying_elapsed=0.15
    )
    renderer.render(state, headless_surface)
    # The hit zone shows through where the phantom was.
    assert _rgb(headless_surface, _lane_center_x(1), 600) == HIT_ZONE_COLOR


# ---- phase banner ----------------------------------------------------------


@pytest.mark.ui
def test_phase_banner_renders_when_active(headless_surface) -> None:
    """A banner at peak visibility (end of fade-in) paints non-background pixels.

    The banner is centred at (WINDOW_W/2, BANNER_TOP_MARGIN) at native size, so
    for a count=1 banner it occupies an icon-square around x=204..276. Sample a
    region inside the icon but on the left side of the lane divider (x=240) so
    a non-bg hit can only come from the star itself, not the divider line.
    """
    from piano_tiles.config import BANNER_FADE_IN_SECONDS

    renderer = Renderer()
    state = GameState(
        state=State.PLAYING,
        banner_phase_number=2,
        banner_elapsed=BANNER_FADE_IN_SECONDS,  # alpha=255, scale=1.0
    )
    renderer.render(state, headless_surface)
    assert _any_non_bg_pixel(headless_surface, 215, 50, 20, 50)


@pytest.mark.ui
def test_phase_banner_renders_mid_fade_in_with_partial_alpha(headless_surface) -> None:
    """During the fade-in window the banner draws but with alpha < 255."""
    from piano_tiles.config import BANNER_FADE_IN_SECONDS

    renderer = Renderer()
    state = GameState(
        state=State.PLAYING,
        banner_phase_number=2,
        banner_elapsed=BANNER_FADE_IN_SECONDS / 2.0,  # mid fade-in
    )
    renderer.render(state, headless_surface)
    # Non-background somewhere in the banner region — the partial alpha didn't suppress it.
    assert _any_non_bg_pixel(headless_surface, WINDOW_W // 2 - 60, 50, 120, 120)


@pytest.mark.ui
def test_phase_banner_does_not_paint_outside_its_window(headless_surface) -> None:
    """Past the fade-out window, the banner is gone — the top area is all background."""
    renderer = Renderer()
    state = GameState(
        state=State.PLAYING,
        banner_phase_number=2,
        banner_elapsed=99.0,
    )
    renderer.render(state, headless_surface)
    # Sample inside lane 0 at the banner's vertical region (away from lane dividers).
    assert _rgb(headless_surface, 50, 100) == BG_COLOR


@pytest.mark.ui
def test_falling_tile_paints_over_banner_when_they_overlap(headless_surface) -> None:
    """Regression for the 'tiles overlap with the banner' bug.

    The phase-change banner sits BEHIND falling tiles in the z-order. When a
    tile crosses the banner rect, the tile's color paints over the icon — not
    the other way around. The previous order made the yellow icon look stamped
    onto the tile mid-flight, which read as a glitch.
    """
    from piano_tiles.config import (
        BANNER_FADE_IN_SECONDS,
        BANNER_ICON_HEIGHT,
        BANNER_TOP_MARGIN,
    )

    renderer = Renderer()
    # Banner (count=1) is centred at x=WINDOW_W//2, occupies a 72×72 square
    # starting at y=BANNER_TOP_MARGIN. Lane 2 (x=240..360) overlaps the right
    # half of the banner (x=204..276 for one icon).
    overlap_x = (WINDOW_W // 2) + 10  # x=250, inside both lane 2 and banner
    overlap_y = BANNER_TOP_MARGIN + BANNER_ICON_HEIGHT // 2
    tile = Tile(
        lane=2,
        y=float(BANNER_TOP_MARGIN),
        height=float(BANNER_ICON_HEIGHT),
        speed=300.0,
    )
    state = GameState(
        state=State.PLAYING,
        tiles=(tile,),
        banner_phase_number=2,
        banner_elapsed=BANNER_FADE_IN_SECONDS,  # alpha=255, scale=1.0
    )
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, overlap_x, overlap_y) == TILE_FALLING_COLOR


# ---- edge cases ------------------------------------------------------------


@pytest.mark.ui
def test_tile_partially_off_screen_at_top_renders_without_error(
    headless_surface,
) -> None:
    """Tile with negative y — pygame clips the rect; rendering must not raise."""
    renderer = Renderer()
    tile = Tile(lane=0, y=-50.0, height=100.0, speed=300.0)  # top -50, bottom 50
    state = GameState(state=State.PLAYING, tiles=(tile,))
    renderer.render(state, headless_surface)
    # The on-screen part (y = 0..49) is still the tile color.
    assert _rgb(headless_surface, _lane_center_x(0), 25) == TILE_FALLING_COLOR


@pytest.mark.ui
def test_render_with_many_tiles_completes_in_reasonable_time(
    headless_surface,
) -> None:
    """Smoke perf: 500 tiles render without raising and within a generous budget."""
    renderer = Renderer()
    tiles = tuple(
        Tile(lane=i % 4, y=float(i), height=20.0, speed=300.0) for i in range(500)
    )
    state = GameState(state=State.PLAYING, tiles=tiles)
    start = time.perf_counter()
    renderer.render(state, headless_surface)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"500-tile render took {elapsed:.2f}s"


@pytest.mark.ui
def test_render_is_a_pure_paint_and_does_not_mutate_state(headless_surface) -> None:
    """The renderer must not mutate the GameState or its tiles."""
    renderer = Renderer()
    tile = Tile(lane=2, y=100.0, height=80.0, speed=300.0)
    state = GameState(state=State.PLAYING, tiles=(tile,), score=7)
    renderer.render(state, headless_surface)
    assert tile.lane == 2
    assert tile.y == 100.0
    assert tile.state == "falling"
    assert state.score == 7


@pytest.mark.ui
def test_render_can_be_called_repeatedly_on_same_surface(headless_surface) -> None:
    """Each render() is self-contained: the background fill clears prior frames."""
    renderer = Renderer()
    # Frame 1: MENU.
    renderer.render(GameState(state=State.MENU), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == MENU_OVERLAY_COLOR
    # Frame 2: PLAYING — overlay must be gone.
    renderer.render(GameState(state=State.PLAYING), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == BG_COLOR


# ---- per-state snapshots --------------------------------------------------


@pytest.mark.ui
def test_menu_state_snapshot(headless_surface) -> None:
    """MENU shows BG fill, hit-zone band, lane dividers, menu overlay band + text, and a score region."""
    renderer = Renderer()
    renderer.render(GameState(state=State.MENU), headless_surface)

    # Background fill in an empty area (above overlay band, away from score).
    assert _rgb(headless_surface, _lane_center_x(2), 250) == BG_COLOR
    # Hit zone is drawn even on the menu screen.
    hit_zone_mid_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) // 2
    assert _rgb(headless_surface, _lane_center_x(1), hit_zone_mid_y) == HIT_ZONE_COLOR
    # Overlay band edge (left of centered text) shows the flat menu color.
    assert _rgb(headless_surface, 10, _band_center_y()) == MENU_OVERLAY_COLOR
    # Overlay text region (center of band) is non-background — text was painted.
    assert _rgb(headless_surface, WINDOW_W // 2, _band_center_y()) != BG_COLOR
    # Score area renders the "0" — non-background somewhere in the corner.
    assert _any_non_bg_pixel(headless_surface, SCORE_POS_X, SCORE_POS_Y, 60, 40)


@pytest.mark.ui
def test_playing_state_snapshot(headless_surface) -> None:
    """PLAYING shows BG, hit zone, a tile in its lane, a non-zero score, and NO overlay band."""
    renderer = Renderer()
    tile = Tile(lane=2, y=120.0, height=120.0, speed=300.0)
    state = GameState(state=State.PLAYING, tiles=(tile,), score=5)
    renderer.render(state, headless_surface)

    # Background in an empty lane area.
    assert _rgb(headless_surface, _lane_center_x(0), 250) == BG_COLOR
    # Tile painted in its lane at its y range.
    assert _rgb(headless_surface, _lane_center_x(2), 180) == TILE_FALLING_COLOR
    # Other lanes are background at the same y.
    for other_lane in (0, 1, 3):
        assert _rgb(headless_surface, _lane_center_x(other_lane), 180) == BG_COLOR
    # Hit zone visible across the width.
    hit_zone_mid_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) // 2
    for lane in range(4):
        assert _rgb(headless_surface, _lane_center_x(lane), hit_zone_mid_y) == HIT_ZONE_COLOR
    # Score region has rendered text.
    assert _any_non_bg_pixel(headless_surface, SCORE_POS_X, SCORE_POS_Y, 60, 40)
    # No overlay band — the center band area must be plain BG.
    color = _rgb(headless_surface, 10, _band_center_y())
    assert color == BG_COLOR
    assert color not in (MENU_OVERLAY_COLOR, PAUSED_OVERLAY_COLOR, GAME_OVER_OVERLAY_COLOR)


@pytest.mark.ui
def test_game_over_state_snapshot(headless_surface) -> None:
    """GAME_OVER shows BG, hit zone, the game-over band, and the score from frame one."""
    renderer = Renderer()
    state = GameState(state=State.GAME_OVER, score=17)
    renderer.render(state, headless_surface)

    # Background in an empty area above the overlay band.
    assert _rgb(headless_surface, _lane_center_x(2), 250) == BG_COLOR
    # Hit zone remains painted under the overlay (sample where the band isn't).
    hit_zone_mid_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) // 2
    assert _rgb(headless_surface, _lane_center_x(0), hit_zone_mid_y) == HIT_ZONE_COLOR
    # Game-over band uses the flat game-over color, distinct from menu.
    band_pixel = _rgb(headless_surface, 10, _band_center_y())
    assert band_pixel == GAME_OVER_OVERLAY_COLOR
    assert band_pixel != MENU_OVERLAY_COLOR
    # Overlay text region is non-background.
    assert _rgb(headless_surface, WINDOW_W // 2, _band_center_y()) != BG_COLOR
    # Final score is rendered.
    assert _any_non_bg_pixel(headless_surface, SCORE_POS_X, SCORE_POS_Y, 60, 40)


# ---- per-song palette theming ---------------------------------------------
#
# The play-field and overlay colors are read from the palette on the GameState,
# so each song repaints the whole screen in its own theme. These render with an
# explicit non-default palette and assert the painted pixels follow it.


@pytest.mark.ui
def test_playing_field_colors_follow_palette(headless_surface) -> None:
    """Background, the hit-zone line, and the falling tile all paint in the
    supplied palette's colors, not the classic defaults."""
    renderer = Renderer()
    tile = Tile(lane=2, y=120.0, height=120.0, speed=300.0)
    state = GameState(state=State.PLAYING, tiles=(tile,), palette=PEACH_SORBET)
    renderer.render(state, headless_surface)
    # Background, away from the tile and hit zone.
    assert _rgb(headless_surface, _lane_center_x(0), 250) == PEACH_SORBET.background
    # Hit-zone line at the bottom.
    hit_zone_mid_y = (HIT_ZONE_TOP + HIT_ZONE_BOTTOM) // 2
    assert (
        _rgb(headless_surface, _lane_center_x(0), hit_zone_mid_y)
        == PEACH_SORBET.hit_zone
    )
    # Falling tile band.
    assert _rgb(headless_surface, _lane_center_x(2), 180) == PEACH_SORBET.tile_falling


@pytest.mark.ui
def test_held_tile_uses_palette_held_color(headless_surface) -> None:
    """A fully-overlaid tile paints in the palette's held color."""
    renderer = Renderer()
    tile = Tile(lane=0, y=100.0, height=80.0, speed=300.0)
    tile.held_amount = tile.original_height
    tile.mark_hit()
    state = GameState(state=State.PLAYING, tiles=(tile,), palette=MINT_BLUSH)
    renderer.render(state, headless_surface)
    assert _rgb(headless_surface, _lane_center_x(0), 140) == MINT_BLUSH.tile_held


@pytest.mark.ui
@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET])
def test_menu_band_follows_palette(headless_surface, palette) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.MENU, palette=palette), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == palette.menu_band


@pytest.mark.ui
@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET])
def test_paused_band_follows_palette(headless_surface, palette) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.PAUSED, palette=palette), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == palette.paused_band


@pytest.mark.ui
@pytest.mark.parametrize("palette", [MINT_BLUSH, PEACH_SORBET])
def test_game_over_band_follows_palette(headless_surface, palette) -> None:
    renderer = Renderer()
    renderer.render(GameState(state=State.GAME_OVER, palette=palette), headless_surface)
    assert _rgb(headless_surface, 10, _band_center_y()) == palette.game_over_band
