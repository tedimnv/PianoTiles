"""Runtime state of the wrong-key red flash.

When the player presses the wrong lane, a phantom tile flashes red where they
*should* have pressed before the game over screen appears. The flash owns the
phantom and the elapsed timer; the renderer reads them off the snapshot, and
the orchestrator drives the timer via `tick`, firing `DIE` when it returns
True.

Pure Python; no pygame imports.
"""

from piano_tiles.config import WRONG_KEY_FLASH_DURATION
from piano_tiles.models.tile import Tile


class DyingFlash:
    def __init__(self) -> None:
        self._phantom: Tile | None = None
        self._elapsed: float | None = None

    # ---- queries ----------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._phantom is not None

    @property
    def phantom(self) -> Tile | None:
        return self._phantom

    @property
    def elapsed(self) -> float | None:
        return self._elapsed

    # ---- transitions ------------------------------------------------------

    def begin(self, phantom: Tile) -> None:
        self._phantom = phantom
        self._elapsed = 0.0

    def tick(self, dt: float) -> bool:
        """Advance the flash timer. Returns True iff the flash has just ended
        this tick — the orchestrator should now fire DIE.

        Returns False (without raising) when called while inactive, so the
        orchestrator can blindly tick every frame in the DYING state."""
        if self._elapsed is None:
            return False
        self._elapsed += dt
        if self._elapsed >= WRONG_KEY_FLASH_DURATION:
            self.clear()
            return True
        return False

    def clear(self) -> None:
        self._phantom = None
        self._elapsed = None
