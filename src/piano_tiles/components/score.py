"""Score and combo tracking. Pure Python; no pygame imports."""

from dataclasses import dataclass


@dataclass
class ScoreKeeper:
    points_per_hit: int = 1
    combo_threshold: int = 10
    combo_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.points_per_hit <= 0:
            raise ValueError(
                f"points_per_hit must be > 0, got {self.points_per_hit}"
            )
        if self.combo_threshold <= 0:
            raise ValueError(
                f"combo_threshold must be > 0, got {self.combo_threshold}"
            )
        if self.combo_multiplier < 1:
            raise ValueError(
                f"combo_multiplier must be >= 1, got {self.combo_multiplier}"
            )
        self._score: int = 0
        self._combo: int = 0

    @property
    def score(self) -> int:
        return self._score

    @property
    def combo(self) -> int:
        return self._combo

    def on_hit(self) -> int:
        """Register a hit. Returns the points added by this hit."""
        if self._combo >= self.combo_threshold:
            points = self.points_per_hit * self.combo_multiplier
        else:
            points = self.points_per_hit
        self._score += points
        self._combo += 1
        return points

    def on_miss(self) -> None:
        """Register a miss. Combo resets; score is unchanged (monotonic)."""
        self._combo = 0

    def reset(self) -> None:
        """Start a new run: both score and combo back to zero."""
        self._score = 0
        self._combo = 0
