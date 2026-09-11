import pytest

from piano_tiles.components.score import ScoreKeeper


# ---- initial state ---------------------------------------------------------


@pytest.mark.unit
def test_initial_score_and_combo_are_zero() -> None:
    sk = ScoreKeeper()
    assert sk.score == 0
    assert sk.combo == 0


# ---- construction validation ----------------------------------------------


@pytest.mark.unit
def test_construction_rejects_non_positive_points_per_hit() -> None:
    with pytest.raises(ValueError):
        ScoreKeeper(points_per_hit=0)
    with pytest.raises(ValueError):
        ScoreKeeper(points_per_hit=-1)


@pytest.mark.unit
def test_construction_rejects_non_positive_combo_threshold() -> None:
    with pytest.raises(ValueError):
        ScoreKeeper(combo_threshold=0)
    with pytest.raises(ValueError):
        ScoreKeeper(combo_threshold=-2)


@pytest.mark.unit
def test_construction_rejects_combo_multiplier_below_one() -> None:
    with pytest.raises(ValueError):
        ScoreKeeper(combo_multiplier=0)


# ---- on_hit / on_miss / reset ---------------------------------------------


@pytest.mark.unit
def test_on_hit_increments_score_by_points_per_hit_and_increments_combo() -> None:
    sk = ScoreKeeper(points_per_hit=5)
    sk.on_hit()
    assert sk.score == 5
    assert sk.combo == 1


@pytest.mark.unit
def test_on_hit_returns_the_points_added() -> None:
    sk = ScoreKeeper(points_per_hit=3)
    assert sk.on_hit() == 3


@pytest.mark.unit
def test_multiple_on_hits_accumulate_score_and_combo() -> None:
    sk = ScoreKeeper(points_per_hit=2, combo_threshold=100)
    for _ in range(4):
        sk.on_hit()
    assert sk.score == 8
    assert sk.combo == 4


@pytest.mark.unit
def test_on_miss_resets_combo_but_not_score() -> None:
    sk = ScoreKeeper(points_per_hit=2, combo_threshold=100)
    sk.on_hit()
    sk.on_hit()  # score=4, combo=2
    sk.on_miss()
    assert sk.score == 4
    assert sk.combo == 0


@pytest.mark.unit
def test_on_miss_with_zero_combo_is_safe_noop_on_combo() -> None:
    sk = ScoreKeeper()
    sk.on_miss()
    assert sk.score == 0
    assert sk.combo == 0


@pytest.mark.unit
def test_reset_returns_score_and_combo_to_zero() -> None:
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=100)
    for _ in range(7):
        sk.on_hit()
    assert sk.score == 7
    sk.reset()
    assert sk.score == 0
    assert sk.combo == 0


# ---- monotonicity ---------------------------------------------------------


@pytest.mark.unit
def test_score_is_monotonic_non_decreasing_during_run() -> None:
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=3, combo_multiplier=2)
    history = [sk.score]
    actions = [
        "hit", "hit", "hit", "miss", "hit", "hit", "hit", "hit", "hit", "miss",
    ]
    for action in actions:
        if action == "hit":
            sk.on_hit()
        else:
            sk.on_miss()
        history.append(sk.score)
    for a, b in zip(history, history[1:]):
        assert b >= a


# ---- combo multiplier threshold -------------------------------------------


@pytest.mark.unit
def test_just_below_combo_threshold_uses_base_value() -> None:
    """Hit when combo == threshold - 1 (i.e., the threshold-th hit) → base points."""
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=5, combo_multiplier=3)
    for _ in range(4):
        sk.on_hit()
    assert sk.combo == 4
    score_before = sk.score
    points = sk.on_hit()  # combo was 4 (< 5), still base
    assert points == 1
    assert sk.score == score_before + 1
    assert sk.combo == 5


@pytest.mark.unit
def test_at_combo_threshold_next_hit_is_multiplied() -> None:
    """Hit when combo == threshold (the threshold+1-th hit) → multiplied points."""
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=5, combo_multiplier=3)
    for _ in range(5):
        sk.on_hit()
    assert sk.combo == 5
    score_before = sk.score
    points = sk.on_hit()  # combo was 5 (>= 5), multiplied
    assert points == 3
    assert sk.score == score_before + 3
    assert sk.combo == 6


@pytest.mark.unit
def test_above_combo_threshold_continues_to_be_multiplied() -> None:
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=5, combo_multiplier=3)
    for _ in range(7):  # 5 base, then 2 multiplied
        sk.on_hit()
    # 5 base = 5 points, 2 multiplied = 6 points → total 11
    assert sk.score == 11
    assert sk.combo == 7


@pytest.mark.unit
def test_miss_clears_multiplier_so_next_hit_is_base_again() -> None:
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=3, combo_multiplier=2)
    for _ in range(5):  # 3 base + 2 multiplied = 3 + 4 = 7
        sk.on_hit()
    assert sk.score == 7
    assert sk.combo == 5
    sk.on_miss()
    assert sk.combo == 0
    points = sk.on_hit()
    assert points == 1  # base again
    assert sk.combo == 1


@pytest.mark.unit
def test_multiplier_of_one_means_no_bonus() -> None:
    """combo_multiplier == 1 is a valid no-op multiplier."""
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=2, combo_multiplier=1)
    for _ in range(5):
        sk.on_hit()
    assert sk.score == 5  # nothing was bonused


@pytest.mark.unit
def test_reset_restores_base_value_path() -> None:
    """After a multiplied streak, reset puts us back into the base-value regime."""
    sk = ScoreKeeper(points_per_hit=1, combo_threshold=2, combo_multiplier=5)
    for _ in range(5):
        sk.on_hit()
    sk.reset()
    points = sk.on_hit()
    assert points == 1
    assert sk.score == 1
    assert sk.combo == 1
