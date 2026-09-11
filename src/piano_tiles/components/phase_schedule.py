"""Discrete phase schedule for the difficulty curve.

The game runs in numbered phases. Each phase has a constant fall speed and a
duration. After the last phase ends, the schedule sticks to the last phase's
settings forever.

Pure Python; no pygame imports.
"""

from dataclasses import dataclass

from piano_tiles.config import PHASES


@dataclass(frozen=True)
class Phase:
    speed: float
    duration: float

    def __post_init__(self) -> None:
        if self.speed <= 0:
            raise ValueError(f"speed must be > 0, got {self.speed}")
        if self.duration <= 0:
            raise ValueError(f"duration must be > 0, got {self.duration}")


@dataclass(frozen=True)
class PhaseSchedule:
    phases: tuple[Phase, ...]

    def __post_init__(self) -> None:
        if not self.phases:
            raise ValueError("phases must contain at least one Phase")

    @classmethod
    def from_config(cls) -> "PhaseSchedule":
        """Build the default schedule from the tuples defined in config.PHASES."""
        phases = tuple(Phase(speed=s, duration=d) for s, d in PHASES)
        return cls(phases=phases)

    @property
    def count(self) -> int:
        return len(self.phases)

    def phase(self, index: int) -> Phase:
        """Phase at the given index. The schedule clamps past the last phase."""
        if index < 0:
            raise ValueError(f"phase index must be >= 0, got {index}")
        return self.phases[min(index, self.count - 1)]

    def has_phase_after(self, index: int) -> bool:
        """True if there is at least one more phase after the given index."""
        return index + 1 < self.count
