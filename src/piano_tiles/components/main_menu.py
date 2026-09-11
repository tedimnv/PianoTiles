"""Main-menu policy: what the boot screen says and where its song boxes sit.

Pure logic; no pygame. Two consumers share this module so they never drift
apart: the `Renderer` paints the instruction lines and song boxes, and the
`Game` orchestrator hit-tests clicks against the same boxes. Box geometry is
expressed as plain ``(x, y, w, h)`` tuples so this stays pygame-free.
"""

from piano_tiles.config import (
    LANE_KEYS,
    PAUSE_KEY,
    SONG_OPTION_GAP,
    SONG_OPTION_HEIGHT,
    SONG_OPTION_MARGIN_X,
    SONG_OPTION_TOP,
    SONGS,
    WINDOW_W,
    Song,
)

Box = tuple[int, int, int, int]  # (x, y, width, height)


def instruction_lines() -> tuple[str, ...]:
    """The control hints, derived from the keymap so they never go stale."""
    lane_keys = " ".join(key.upper() for key in LANE_KEYS)
    return (
        f"Play with {lane_keys}",
        f"Press {PAUSE_KEY.upper()} to pause",
    )


def song_label(song: Song) -> str:
    """The one-line label painted inside a song's option box."""
    return f"{song.title} - {song.artist}"


def song_option_box(index: int) -> Box:
    """The (x, y, w, h) rectangle for the song at `index`, stacked top-down."""
    width = WINDOW_W - 2 * SONG_OPTION_MARGIN_X
    top = SONG_OPTION_TOP + index * (SONG_OPTION_HEIGHT + SONG_OPTION_GAP)
    return (SONG_OPTION_MARGIN_X, top, width, SONG_OPTION_HEIGHT)


def song_index_at(pos: tuple[int, int]) -> int | None:
    """The index of the song box containing `pos`, or None if the click missed
    every box."""
    px, py = pos
    for index in range(len(SONGS)):
        x, y, w, h = song_option_box(index)
        if x <= px < x + w and y <= py < y + h:
            return index
    return None
