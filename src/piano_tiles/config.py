"""Game-wide constants. Pure Python; no pygame imports."""

from dataclasses import dataclass
from pathlib import Path

# ---- lanes ----------------------------------------------------------------
LANE_COUNT: int = 4
LANE_KEYS: tuple[str, str, str, str] = ("d", "f", "j", "k")

# ---- controls --------------------------------------------------------------
PAUSE_KEY: str = "p"
RESTART_KEY: str = "space"
QUIT_KEY: str = "escape"
MENU_KEY: str = "m"  # from GAME_OVER, return to the main menu (song selection)

# ---- window & geometry ----------------------------------------------------
WINDOW_W: int = 480
WINDOW_H: int = 720
LANE_WIDTH: int = WINDOW_W // LANE_COUNT

HIT_ZONE_TOP: int = 570
HIT_ZONE_BOTTOM: int = 700

TILE_HEIGHT: int = 180

# ---- difficulty phases ----------------------------------------------------
# Each phase has (fall_speed_px_per_sec, duration_seconds). Speed jumps
# discretely at phase boundaries; the schedule continues forever at the last
# phase's settings once we run out of entries. The speed ramp stops at phase 5
# (the first phase that shows a crown); phases 6 and 7 keep the top speed.
PHASES: tuple[tuple[float, float], ...] = (
    (240.0, 20.0),
    (290.0, 20.0),
    (340.0, 20.0),
    (390.0, 20.0),
    (440.0, 20.0),
    (440.0, 20.0),
    (440.0, 20.0),
)

# Visual gap (px) between two consecutive same-lane tiles. The spawner picks
# spawn intervals so this gap stays the same regardless of fall speed.
TILE_VISUAL_GAP_PX: int = 1

# ---- phase banner (shown briefly when a new phase starts) -----------------
# Total banner display = FADE_IN + HOLD + FADE_OUT seconds. Gameplay continues
# during the banner; it's a HUD element, not a pause. The hold phase keeps the
# icon fully visible at native size so the player can read it without rushing.
BANNER_FADE_IN_SECONDS: float = 0.5
BANNER_HOLD_SECONDS: float = 2.0
BANNER_FADE_OUT_SECONDS: float = 0.5
BANNER_TOP_MARGIN: int = 20
BANNER_ZOOM_FROM: float = 0.4  # starting scale of the fade-in (grows to 1.0)
BANNER_ZOOM_TO: float = 0.4    # ending scale of the fade-out (shrinks from 1.0)
BANNER_ICON_HEIGHT: int = 72   # 2× the score text. Each icon renders at this size regardless of count.

# Phase → (icon_key, count). The renderer looks up each icon_key in its asset
# registry. Phase 1 has no entry — that's the starting phase, so no banner
# plays for it. The first banner fires when the player advances from 1 to 2.
PHASE_BANNER_ICONS: dict[int, tuple[str, int]] = {
    2: ("star", 1),
    3: ("star", 2),
    4: ("star", 3),
    5: ("crown", 1),
    6: ("crown", 2),
    7: ("crown", 3),
}

# ---- wrong-key feedback ---------------------------------------------------
# When the player presses the wrong lane, a phantom red tile briefly flashes
# at the pressed lane before the game-over screen fades in.
WRONG_KEY_FLASH_DURATION: float = 0.6
WRONG_KEY_FLASH_COUNT: int = 3
WRONG_KEY_FLASH_COLOR: tuple[int, int, int] = (240, 50, 50)

# Game-over snaps on at full opacity — no fade.
# An alpha fade-in (any duration) produced a visible dark stripe across the
# screen during the dim phase; killing the fade kills the artifact.

# ---- background music ------------------------------------------------------
# Absolute path to the BGM file, resolved at import time so the asset is found
# regardless of cwd. Ships at `assets/SDITD.ogg` at the repo root, two levels
# up from this module (src/piano_tiles/config.py -> repo root).
BGM_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "SDITD.ogg"
)

# "Loose" track, resolved the same way as BGM_PATH above.
LOOSE_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "Loose.ogg"
)

# "Yesterday" track, resolved the same way as BGM_PATH above.
YESTERDAY_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "Yesterday.ogg"
)

# Volume during GAME_OVER. Music keeps playing but ducked so the game-over
# screen feels distinct from active play. 0.0 = silent, 1.0 = full.
BGM_GAME_OVER_VOLUME: float = 0.6


# ---- colors ----------------------------------------------------------------
# The classic cyan/magenta theme. These globals double as DEFAULT_PALETTE's
# values. LANE_DIVIDER_COLOR, SCORE_TEXT_COLOR and BANNER_COLOR are not themed
# per song, so they stay plain module constants.
BG_COLOR: tuple[int, int, int] = (10, 10, 20)
LANE_DIVIDER_COLOR: tuple[int, int, int] = (80, 80, 100)
HIT_ZONE_COLOR: tuple[int, int, int] = (200, 60, 200)
TILE_FALLING_COLOR: tuple[int, int, int] = (80, 200, 220)
TILE_HELD_COLOR: tuple[int, int, int] = (180, 240, 255)  # brighter cyan — held overlay (long tile in progress, short tile hit)
SCORE_TEXT_COLOR: tuple[int, int, int] = (240, 240, 240)
BANNER_COLOR: tuple[int, int, int] = (255, 220, 60)

# ---- overlay band colors (one per non-PLAYING state, mutually distinct) -----
# Defaults for the classic theme; each Palette supplies its own band colors.
# Overlay text is always white, so every band must stay dark enough to read.
MENU_OVERLAY_COLOR: tuple[int, int, int] = (60, 80, 200)
PAUSED_OVERLAY_COLOR: tuple[int, int, int] = (200, 200, 60)
GAME_OVER_OVERLAY_COLOR: tuple[int, int, int] = (200, 50, 50)
OVERLAY_TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)


# ---- per-song palettes ------------------------------------------------------
@dataclass(frozen=True)
class Palette:
    """The themeable colors for one song: the play-field (background, the
    hit-zone line at the bottom, and the two tile bands) plus the three overlay
    band colors. The overlay text is always white, so every band colour here is
    dark enough to read against."""

    background: tuple[int, int, int]
    hit_zone: tuple[int, int, int]
    tile_falling: tuple[int, int, int]
    tile_held: tuple[int, int, int]
    menu_band: tuple[int, int, int]
    paused_band: tuple[int, int, int]
    game_over_band: tuple[int, int, int]


# Classic cyan/magenta — used when no song is selected (e.g. the boot screen,
# which paints its own background anyway).
DEFAULT_PALETTE = Palette(
    background=BG_COLOR,
    hit_zone=HIT_ZONE_COLOR,
    tile_falling=TILE_FALLING_COLOR,
    tile_held=TILE_HELD_COLOR,
    menu_band=MENU_OVERLAY_COLOR,
    paused_band=PAUSED_OVERLAY_COLOR,
    game_over_band=GAME_OVER_OVERLAY_COLOR,
)

# "Mint & Blush" — mint tiles + blush hit line on a near-black slate. The
# falling and held (clicked) tile colors are swapped from the source palette.
MINT_BLUSH = Palette(
    background=(15, 20, 23),       # #0F1417
    hit_zone=(255, 153, 177),      # #FF99B1
    tile_falling=(127, 227, 190),  # #7FE3BE
    tile_held=(205, 245, 228),     # #CDF5E4
    menu_band=(31, 58, 52),        # #1F3A34
    paused_band=(46, 36, 51),      # #2E2433
    game_over_band=(58, 34, 48),   # #3A2230
)

# "Peach Sorbet" — warm cream/coral tiles on near-black brown.
PEACH_SORBET = Palette(
    background=(21, 17, 15),
    hit_zone=(255, 155, 133),     # #FF9B85
    tile_falling=(255, 201, 163),  # #FFC9A3
    tile_held=(255, 233, 199),     # #FFE9C7
    menu_band=(58, 42, 31),
    paused_band=(46, 42, 34),
    game_over_band=(64, 32, 40),
)

# "Arctic" — icy blue tiles on a cold near-black. Reserved for the third song
# slot; attach it to a Song once that track is added.
ARCTIC = Palette(
    background=(12, 20, 24),       # #0C1418
    hit_zone=(124, 202, 223),      # #7CCADF
    tile_falling=(163, 228, 240),  # #A3E4F0
    tile_held=(207, 239, 245),     # #CFEFF5
    menu_band=(23, 48, 56),        # #173038
    paused_band=(30, 42, 51),      # #1E2A33
    game_over_band=(43, 39, 64),   # #2B2740
)


# ---- song catalog -----------------------------------------------------------
@dataclass(frozen=True)
class Song:
    """A selectable track. `path` is the audio the MusicPlayer loads; `palette`
    themes the play-field and overlays while this song is the chosen one."""

    title: str
    artist: str
    path: Path
    palette: Palette


# The songs offered on the main menu, in display order. Add more entries here
# and the menu lays them out automatically.
SONGS: tuple[Song, ...] = (
    Song(
        title="Slow Dancing In The Dark",
        artist="JOJI",
        path=BGM_PATH,
        palette=MINT_BLUSH,
    ),
    Song(
        title="Loose",
        artist="Daniel Caesar",
        path=LOOSE_PATH,
        palette=PEACH_SORBET,
    ),
    Song(
        title="Yesterday",
        artist="The Beatles",
        path=YESTERDAY_PATH,
        palette=ARCTIC,
    ),
)

# ---- text & overlay geometry ----------------------------------------------
SCORE_FONT_SIZE: int = 36
OVERLAY_FONT_SIZE: int = 48
SCORE_POS_X: int = 10
SCORE_POS_Y: int = 10
OVERLAY_BAND_TOP: int = WINDOW_H // 2 - 60
OVERLAY_BAND_BOTTOM: int = WINDOW_H // 2 + 60

# ---- main menu (boot screen: controls + song selection) -------------------
# A light bokeh photo backs the boot screen, so its text is near-black to read
# against the bright background. The image is scaled to the window at load.
MAIN_MENU_BG_IMAGE: str = "menu_bg.jpg"
MAIN_MENU_TITLE: str = "PIANO TILES"
MAIN_MENU_CHOOSE_HEADER: str = "Choose a song:"
MAIN_MENU_TEXT_COLOR: tuple[int, int, int] = (25, 25, 32)  # near-black on the light photo

MAIN_MENU_TITLE_FONT_SIZE: int = 56
MAIN_MENU_TEXT_FONT_SIZE: int = 30
SONG_OPTION_FONT_SIZE: int = 26

MAIN_MENU_TITLE_Y: int = 90            # baseline-centre of the title
MAIN_MENU_INSTRUCTIONS_TOP: int = 190  # centre-y of the first instruction line
MAIN_MENU_LINE_SPACING: int = 44       # vertical gap between instruction lines
MAIN_MENU_CHOOSE_HEADER_Y: int = 322   # centre-y of the "Choose a song:" header

# Clickable song option boxes — geometry shared by the renderer (draw) and the
# orchestrator (hit-test), so a click always lands where the box is painted.
# SONG_SLOT_COUNT boxes are drawn; slots past the end of SONGS are empty
# placeholders (rendered but not clickable yet).
SONG_SLOT_COUNT: int = 4
SONG_OPTION_MARGIN_X: int = 40
SONG_OPTION_TOP: int = 366             # top-y of the first option box
SONG_OPTION_HEIGHT: int = 70
SONG_OPTION_GAP: int = 16              # vertical gap between consecutive boxes
SONG_OPTION_COLOR: tuple[int, int, int] = (108, 82, 140)   # muted purple (filled song)
SONG_EMPTY_SLOT_COLOR: tuple[int, int, int] = (150, 150, 165)  # muted grey (empty slot)
SONG_OPTION_TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)
