"""Per-state overlay policy: band color and message.

Pure logic; no pygame. The renderer asks `overlay_for(state)` once per frame
and paints whatever it receives. The band color comes from the active song's
palette (carried on the GameState), so each song themes its own screens; the
message is fixed per state. Adding a new overlay variant means adding a branch
here — not in the renderer.

All overlays render at full opacity from the first frame. An earlier version
faded GAME_OVER in over ~1 s; against the dark background the dim phase looked
like a black stripe across the screen ("black line for the first second").
Snapping straight to full opacity removes the artifact entirely.
"""

from dataclasses import dataclass

from piano_tiles.config import MENU_KEY, RESTART_KEY
from piano_tiles.models.game_state import GameState
from piano_tiles.models.state import State


@dataclass(frozen=True)
class OverlayInfo:
    color: tuple[int, int, int]
    message: str
    subtitle: str | None = None


_MESSAGES: dict[State, str] = {
    State.MENU: f"Press {RESTART_KEY.upper()} to start",
    State.PAUSED: "PAUSED",
    State.GAME_OVER: "GAME OVER",
}

# Secondary hints shown beneath the main message, in the same text color but
# smaller. Only GAME_OVER carries one (the way back to the song picker).
_SUBTITLES: dict[State, str] = {
    State.GAME_OVER: f"Press {MENU_KEY.upper()} for main menu",
}


def overlay_for(state: GameState) -> OverlayInfo | None:
    """The overlay to paint this frame, or None when no overlay is shown. The
    band color is read from the active palette so each song themes its screens."""
    message = _MESSAGES.get(state.state)
    if message is None:
        return None
    return OverlayInfo(
        color=_band_color(state),
        message=message,
        subtitle=_SUBTITLES.get(state.state),
    )


def _band_color(state: GameState) -> tuple[int, int, int]:
    """The palette's band color for the (overlay-bearing) state."""
    palette = state.palette
    return {
        State.MENU: palette.menu_band,
        State.PAUSED: palette.paused_band,
        State.GAME_OVER: palette.game_over_band,
    }[state.state]
