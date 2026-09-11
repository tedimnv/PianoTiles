"""Tracks the runtime position within a `PhaseSchedule`.

The schedule is static (which phases exist, how long each runs); the tracker
holds the *current* state: which phase we're in and how much of it has
elapsed. There are no inter-phase breaks — phase boundaries are crossed
instantaneously and `advance_play` reports whether a boundary was crossed
this tick so the orchestrator can swap the spawner and start a banner.

Pure Python; no pygame imports.
"""

from piano_tiles.components.phase_schedule import Phase, PhaseSchedule


class PhaseTracker:
    def __init__(self, schedule: PhaseSchedule) -> None:
        self._schedule = schedule
        self._phase_index: int = 0
        self._phase_elapsed: float = 0.0

    # ---- queries ----------------------------------------------------------

    @property
    def phase_number(self) -> int:
        """1-indexed phase number — what the player sees in the UI."""
        return self._phase_index + 1

    @property
    def current_phase(self) -> Phase:
        return self._schedule.phase(self._phase_index)

    # ---- transitions ------------------------------------------------------

    def advance_play(self, dt: float) -> float | None:
        """Tick the play clock; auto-advance to the next phase when the current
        phase's duration elapses.

        Returns None when the phase didn't change; otherwise returns the
        *leftover* — the time that's elapsed in the NEW phase this tick. The
        orchestrator uses the leftover both to time the new spawner (so it
        doesn't over-spawn after a long dt) and to time-stamp the banner. If
        dt covers multiple boundaries the tracker still advances at most one
        — the spawn cadence and banner only need to fire once per crossing.
        """
        self._phase_elapsed += dt
        if (
            self._schedule.has_phase_after(self._phase_index)
            and self._phase_elapsed >= self.current_phase.duration
        ):
            leftover = self._phase_elapsed - self.current_phase.duration
            self._phase_elapsed = leftover
            self._phase_index += 1
            return leftover
        return None

    def reset(self) -> None:
        self._phase_index = 0
        self._phase_elapsed = 0.0
