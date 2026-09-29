"""Paints a `GameState` snapshot to a pygame Surface.

The only component beyond `InputAdapter` and the top-level `Game` that touches
pygame. The renderer is stateless w.r.t. game logic — it reads the snapshot
and draws; it never mutates the state. Overlay and banner color/text/alpha
decisions live in `overlay.py` and `banner.py`; this module turns them into
pixels.
"""

import math
from pathlib import Path

import pygame

from piano_tiles.components.banner import BannerInfo, banner_for
from piano_tiles.components.main_menu import (
    instruction_lines,
    song_label,
    song_option_box,
)
from piano_tiles.components.overlay import OverlayInfo, overlay_for
from piano_tiles.config import (
    BANNER_ICON_HEIGHT,
    BANNER_TOP_MARGIN,
    LANE_COUNT,
    LANE_DIVIDER_COLOR,
    LANE_WIDTH,
    MAIN_MENU_BG_IMAGE,
    MAIN_MENU_CHOOSE_HEADER,
    MAIN_MENU_CHOOSE_HEADER_Y,
    MAIN_MENU_INSTRUCTIONS_TOP,
    MAIN_MENU_LINE_SPACING,
    MAIN_MENU_TEXT_COLOR,
    MAIN_MENU_TEXT_FONT_SIZE,
    MAIN_MENU_TITLE,
    MAIN_MENU_TITLE_FONT_SIZE,
    MAIN_MENU_TITLE_Y,
    OVERLAY_BAND_BOTTOM,
    OVERLAY_BAND_TOP,
    OVERLAY_FONT_SIZE,
    OVERLAY_SUBTITLE_FONT_SIZE,
    OVERLAY_TEXT_COLOR,
    SCORE_FONT_SIZE,
    SCORE_POS_X,
    SCORE_POS_Y,
    SCORE_TEXT_COLOR,
    SONG_EMPTY_SLOT_COLOR,
    SONG_OPTION_COLOR,
    SONG_OPTION_FONT_SIZE,
    SONG_OPTION_TEXT_COLOR,
    SONG_SLOT_COUNT,
    SONGS,
    WINDOW_H,
    WINDOW_W,
    WRONG_KEY_FLASH_COLOR,
    WRONG_KEY_FLASH_COUNT,
    WRONG_KEY_FLASH_DURATION,
)
from piano_tiles.config import Palette
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State
from piano_tiles.models.tile import Tile

# assets/ lives at the repo root: src/piano_tiles/components/renderer.py -> repo root.
_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "assets"
_ICON_FILES: dict[str, str] = {
    "star": "star.png",
    "crown": "crown.png",
}


class Renderer:
    def __init__(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        self._score_font = pygame.font.Font(None, SCORE_FONT_SIZE)
        self._overlay_font = pygame.font.Font(None, OVERLAY_FONT_SIZE)
        self._overlay_subtitle_font = pygame.font.Font(None, OVERLAY_SUBTITLE_FONT_SIZE)
        self._title_font = pygame.font.Font(None, MAIN_MENU_TITLE_FONT_SIZE)
        self._menu_text_font = pygame.font.Font(None, MAIN_MENU_TEXT_FONT_SIZE)
        self._song_font = pygame.font.Font(None, SONG_OPTION_FONT_SIZE)
        self._icons = self._load_icons()
        self._menu_bg = self._load_menu_bg()

    @staticmethod
    def _load_menu_bg() -> pygame.Surface:
        """Load the main-menu photo and scale it to fill the window. Left
        unconverted so it blits headlessly (no display mode needed in tests)."""
        image = pygame.image.load(str(_ASSETS_DIR / MAIN_MENU_BG_IMAGE))
        return pygame.transform.smoothscale(image, (WINDOW_W, WINDOW_H))

    @staticmethod
    def _load_icons() -> dict[str, pygame.Surface]:
        """Load each icon as RGBA. `convert_alpha` needs a video mode set; when
        running headless without `set_mode` (e.g. unit tests) we fall back to
        the raw loaded surface, which still blits correctly — just slower."""
        icons: dict[str, pygame.Surface] = {}
        for key, filename in _ICON_FILES.items():
            path = _ASSETS_DIR / filename
            surface = pygame.image.load(str(path))
            try:
                icons[key] = surface.convert_alpha()
            except pygame.error:
                icons[key] = surface
        return icons

    def render(self, state: GameState, surface: pygame.Surface) -> None:
        if state.state is State.MAIN_MENU:
            # The boot screen is its own layout (controls + song list); none of
            # the play-field elements belong here.
            self._draw_main_menu(surface)
            return
        self._draw_background(surface, state)
        self._draw_lane_dividers(surface)
        self._draw_hit_zone(surface, state)
        # Banner sits BEHIND tiles. When a falling tile crosses the banner
        # rect, the tile paints over the icon — visually the banner is a HUD
        # layer that gameplay tiles can occlude. The alternative (banner on
        # top of tiles) produced an "icon stamped on the falling tile" look
        # which the player perceived as a glitch.
        self._draw_banner(surface, state)
        self._draw_tiles(surface, state)
        self._draw_phantom(surface, state)
        self._draw_score(surface, state)
        self._draw_overlay(surface, state)

    # ---- main menu --------------------------------------------------------

    def _draw_main_menu(self, surface: pygame.Surface) -> None:
        surface.blit(self._menu_bg, (0, 0))
        self._blit_centered(
            surface, self._title_font, MAIN_MENU_TITLE, MAIN_MENU_TITLE_Y,
            MAIN_MENU_TEXT_COLOR,
        )
        for i, line in enumerate(instruction_lines()):
            y = MAIN_MENU_INSTRUCTIONS_TOP + i * MAIN_MENU_LINE_SPACING
            self._blit_centered(surface, self._menu_text_font, line, y, MAIN_MENU_TEXT_COLOR)
        self._blit_centered(
            surface, self._menu_text_font, MAIN_MENU_CHOOSE_HEADER,
            MAIN_MENU_CHOOSE_HEADER_Y, MAIN_MENU_TEXT_COLOR,
        )
        self._draw_song_options(surface)

    def _draw_song_options(self, surface: pygame.Surface) -> None:
        """Draw SONG_SLOT_COUNT boxes. Slots backed by a real song are filled in
        the option color and labelled; the extra slots are empty placeholders."""
        for i in range(SONG_SLOT_COUNT):
            x, y, w, h = song_option_box(i)
            if i < len(SONGS):
                pygame.draw.rect(surface, SONG_OPTION_COLOR, pygame.Rect(x, y, w, h))
                self._blit_centered(
                    surface, self._song_font, song_label(SONGS[i]), y + h // 2,
                    SONG_OPTION_TEXT_COLOR,
                )
            else:
                pygame.draw.rect(surface, SONG_EMPTY_SLOT_COLOR, pygame.Rect(x, y, w, h))

    def _blit_centered(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        center_y: int,
        color: tuple[int, int, int],
    ) -> None:
        rendered = font.render(text, True, color)
        surface.blit(rendered, rendered.get_rect(center=(WINDOW_W // 2, center_y)))

    # ---- pieces -----------------------------------------------------------

    @staticmethod
    def _draw_background(surface: pygame.Surface, state: GameState) -> None:
        surface.fill(state.palette.background)

    @staticmethod
    def _draw_lane_dividers(surface: pygame.Surface) -> None:
        for i in range(1, LANE_COUNT):
            x = i * LANE_WIDTH
            pygame.draw.line(surface, LANE_DIVIDER_COLOR, (x, 0), (x, WINDOW_H))

    @staticmethod
    def _draw_hit_zone(surface: pygame.Surface, state: GameState) -> None:
        height = state.hit_zone_bottom - state.hit_zone_top
        rect = pygame.Rect(0, int(state.hit_zone_top), WINDOW_W, int(height))
        pygame.draw.rect(surface, state.palette.hit_zone, rect)

    @staticmethod
    def _draw_tiles(surface: pygame.Surface, state: GameState) -> None:
        for tile in state.tiles:
            Renderer._draw_tile(surface, tile, state.palette)

    @staticmethod
    def _draw_tile(surface: pygame.Surface, tile: Tile, palette: Palette) -> None:
        """Paint one tile as up to two bands — the falling color on top (the
        un-held part) and the held color on the bottom (the held overlay).
        Missed tiles aren't drawn. Short tiles that have just been hit have
        `held_amount == height`, so they paint entirely in the held color; held
        long tiles paint a mix that grows; an un-pressed tile has
        `held_amount == 0` and paints entirely in the falling color."""
        if tile.is_missed:
            return
        falling_height = tile.height - tile.held_amount
        if falling_height > 0:
            Renderer._fill_rect_at(
                surface,
                tile.lane,
                y=tile.top,
                height=falling_height,
                color=palette.tile_falling,
            )
        if tile.held_amount > 0:
            Renderer._fill_rect_at(
                surface,
                tile.lane,
                y=tile.bottom - tile.held_amount,
                height=tile.held_amount,
                color=palette.tile_held,
            )

    @staticmethod
    def _fill_rect_at(
        surface: pygame.Surface,
        lane: int,
        *,
        y: float,
        height: float,
        color: tuple[int, int, int],
    ) -> None:
        rect = pygame.Rect(
            lane * LANE_WIDTH,
            math.floor(y),
            LANE_WIDTH,
            math.floor(height),
        )
        pygame.draw.rect(surface, color, rect)

    @staticmethod
    def _draw_phantom(surface: pygame.Surface, state: GameState) -> None:
        """Draw the wrong-key phantom while it's flashing red. Visible only on the
        ON beat of WRONG_KEY_FLASH_COUNT flashes spread over the flash duration."""
        if state.dying_phantom is None or state.dying_elapsed is None:
            return
        if Renderer._flash_visible(state.dying_elapsed):
            Renderer._fill_lane_rect(
                surface, state.dying_phantom, WRONG_KEY_FLASH_COLOR
            )

    @staticmethod
    def _flash_visible(elapsed: float) -> bool:
        slot = WRONG_KEY_FLASH_DURATION / (WRONG_KEY_FLASH_COUNT * 2)
        return int(elapsed // slot) % 2 == 0

    @staticmethod
    def _fill_lane_rect(
        surface: pygame.Surface, tile: Tile, color: tuple[int, int, int]
    ) -> None:
        Renderer._fill_rect_at(
            surface, tile.lane, y=tile.y, height=tile.height, color=color
        )

    def _draw_score(self, surface: pygame.Surface, state: GameState) -> None:
        text = self._score_font.render(str(state.score), True, SCORE_TEXT_COLOR)
        surface.blit(text, (SCORE_POS_X, SCORE_POS_Y))

    def _draw_banner(self, surface: pygame.Surface, state: GameState) -> None:
        banner = banner_for(state)
        if banner is None or banner.alpha == 0:
            return
        self._paint_banner(surface, banner, self._icons[banner.icon])

    def _paint_banner(
        self,
        surface: pygame.Surface,
        banner: BannerInfo,
        icon: pygame.Surface,
    ) -> None:
        # Every icon renders at BANNER_ICON_HEIGHT regardless of count. The
        # animation's `scale` zooms the whole row uniformly during fade-in/out.
        rendered_size = max(1, int(round(BANNER_ICON_HEIGHT * banner.scale)))
        icon_scaled = pygame.transform.smoothscale(icon, (rendered_size, rendered_size))
        total_width = rendered_size * banner.count
        composite = pygame.Surface((total_width, rendered_size), pygame.SRCALPHA)
        for i in range(banner.count):
            composite.blit(icon_scaled, (i * rendered_size, 0))
        if banner.alpha < 255:
            composite.set_alpha(banner.alpha)
        rect = composite.get_rect()
        rect.midtop = (WINDOW_W // 2, BANNER_TOP_MARGIN)
        surface.blit(composite, rect)

    def _draw_overlay(self, surface: pygame.Surface, state: GameState) -> None:
        overlay = overlay_for(state)
        if overlay is None:
            return
        self._paint_overlay_band(surface, overlay)

    def _paint_overlay_band(
        self, surface: pygame.Surface, overlay: OverlayInfo
    ) -> None:
        band_w = WINDOW_W
        band_h = OVERLAY_BAND_BOTTOM - OVERLAY_BAND_TOP
        band_surf = pygame.Surface((band_w, band_h))
        band_surf.fill(overlay.color)
        text = self._overlay_font.render(overlay.message, True, OVERLAY_TEXT_COLOR)
        text_rect = text.get_rect(center=(band_w // 2, band_h // 2))
        band_surf.blit(text, text_rect)
        if overlay.subtitle is not None:
            subtitle = self._overlay_subtitle_font.render(
                overlay.subtitle, True, OVERLAY_TEXT_COLOR
            )
            band_surf.blit(
                subtitle,
                subtitle.get_rect(midtop=(band_w // 2, text_rect.bottom + 15)),
            )
        surface.blit(band_surf, (0, OVERLAY_BAND_TOP))


