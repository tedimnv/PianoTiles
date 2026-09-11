"""Phase-banner policy: which icon, how many copies, and the per-frame fade /
zoom values for the transient HUD that pops up at each phase change.

Pure logic; no pygame. The renderer asks `banner_for(state)` once per frame
and paints whatever it receives — the icon key is looked up in the renderer's
loaded-asset registry, and the renderer tiles `count` copies side by side.

Animation profile (each segment uses its corresponding `BANNER_*_SECONDS`):
    fade-in:  alpha 0 → 255, scale ZOOM_FROM → 1.0
    hold:     alpha 255, scale 1.0 (so the player can read the icon)
    fade-out: alpha 255 → 0, scale 1.0 → ZOOM_TO
After `fade_in + hold + fade_out` seconds the banner is gone.
"""

from dataclasses import dataclass

from piano_tiles.config import (
    BANNER_FADE_IN_SECONDS,
    BANNER_FADE_OUT_SECONDS,
    BANNER_HOLD_SECONDS,
    BANNER_ZOOM_FROM,
    BANNER_ZOOM_TO,
    PHASE_BANNER_ICONS,
)
from piano_tiles.models.game_state import GameState

BANNER_TOTAL_SECONDS: float = (
    BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS + BANNER_FADE_OUT_SECONDS
)


@dataclass(frozen=True)
class BannerInfo:
    icon: str    # key into the renderer's icon registry (e.g. "star", "crown")
    count: int   # how many copies to tile side by side
    alpha: int   # 0 (fully transparent) … 255 (fully opaque)
    scale: float  # 1.0 = native size; <1.0 zooms in, >1.0 zooms out


def banner_for(state: GameState) -> BannerInfo | None:
    """The banner to paint this frame, or None when no banner is showing."""
    if state.banner_phase_number is None or state.banner_elapsed is None:
        return None
    if state.banner_elapsed < 0 or state.banner_elapsed >= BANNER_TOTAL_SECONDS:
        return None
    icon_count = PHASE_BANNER_ICONS.get(state.banner_phase_number)
    if icon_count is None:
        return None
    icon, count = icon_count
    alpha, scale = _animation_at(state.banner_elapsed)
    return BannerInfo(icon=icon, count=count, alpha=alpha, scale=scale)


def _animation_at(elapsed: float) -> tuple[int, float]:
    if elapsed < BANNER_FADE_IN_SECONDS:
        progress = elapsed / BANNER_FADE_IN_SECONDS
        alpha = max(0, min(255, int(255 * progress)))
        scale = BANNER_ZOOM_FROM + (1.0 - BANNER_ZOOM_FROM) * progress
        return alpha, scale
    held_end = BANNER_FADE_IN_SECONDS + BANNER_HOLD_SECONDS
    if elapsed < held_end:
        return 255, 1.0
    progress = (elapsed - held_end) / BANNER_FADE_OUT_SECONDS
    alpha = max(0, min(255, int(255 * (1.0 - progress))))
    scale = 1.0 + (BANNER_ZOOM_TO - 1.0) * progress
    return alpha, scale
