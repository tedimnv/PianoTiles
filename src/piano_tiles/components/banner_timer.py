"""Runtime state of the phase-change banner.

The banner pops up briefly each time the player crosses a phase boundary. The
timer owns the "is one playing right now, and how far into it are we?" state;
the rendering policy (`banner_for(state)` in `banner.py`) consumes whatever
values it exposes. The orchestrator wires the two together: it starts the
timer on a phase boundary, ticks it once per frame, and packages the timer's
fields into the snapshot the renderer sees.

Pure Python; no pygame imports.
"""

from piano_tiles.components.banner import BANNER_TOTAL_SECONDS


class BannerTimer:
    def __init__(self) -> None:
        self._phase_number: int | None = None
        self._elapsed: float | None = None

    # ---- queries ----------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._phase_number is not None

    @property
    def phase_number(self) -> int | None:
        return self._phase_number

    @property
    def elapsed(self) -> float | None:
        return self._elapsed

    # ---- transitions ------------------------------------------------------

    def start(self, phase_number: int, initial_elapsed: float = 0.0) -> None:
        """Start a fresh banner. `initial_elapsed` time-stamps the banner from
        a point in the past — used when a phase boundary is crossed mid-tick
        so the banner doesn't show an extra frame of dead time at scale 0."""
        self._phase_number = phase_number
        self._elapsed = initial_elapsed

    def tick(self, dt: float) -> None:
        """Advance the timer. Once the total banner window has elapsed, the
        timer self-clears; subsequent ticks are no-ops until `start` runs."""
        if self._elapsed is None:
            return
        self._elapsed += dt
        if self._elapsed >= BANNER_TOTAL_SECONDS:
            self.clear()

    def clear(self) -> None:
        self._phase_number = None
        self._elapsed = None
