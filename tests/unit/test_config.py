import pytest

from piano_tiles import config


@pytest.mark.unit
def test_lane_count_matches_lane_keys() -> None:
    """LANE_COUNT must equal len(LANE_KEYS) — every lane has exactly one key."""
    assert config.LANE_COUNT == len(config.LANE_KEYS)


@pytest.mark.unit
def test_lane_keys_are_non_empty_strings() -> None:
    """Each lane key must be a non-empty string (used as a key-name lookup)."""
    for key in config.LANE_KEYS:
        assert isinstance(key, str)
        assert key != ""


@pytest.mark.unit
def test_lane_keys_are_unique() -> None:
    """Two lanes cannot share the same key — that would make input ambiguous."""
    assert len(set(config.LANE_KEYS)) == config.LANE_COUNT


@pytest.mark.unit
def test_control_keys_are_non_empty_strings() -> None:
    """Pause / restart / quit keys must each be a non-empty string."""
    for name in ("PAUSE_KEY", "RESTART_KEY", "QUIT_KEY"):
        value = getattr(config, name)
        assert isinstance(value, str), f"{name} is not a string"
        assert value != "", f"{name} is empty"


@pytest.mark.unit
def test_control_keys_do_not_collide_with_lane_keys() -> None:
    """Control keys must not double as lane keys — that would make input ambiguous."""
    control = {config.PAUSE_KEY, config.RESTART_KEY, config.QUIT_KEY}
    assert control.isdisjoint(config.LANE_KEYS)


@pytest.mark.unit
def test_control_keys_are_distinct() -> None:
    """Pause, restart, and quit must each be a different key."""
    assert len({config.PAUSE_KEY, config.RESTART_KEY, config.QUIT_KEY}) == 3


@pytest.mark.unit
def test_window_dimensions_are_positive() -> None:
    assert config.WINDOW_W > 0
    assert config.WINDOW_H > 0


@pytest.mark.unit
def test_hit_zone_lies_inside_window() -> None:
    """Hit zone must be: 0 < TOP < BOTTOM < WINDOW_H."""
    assert 0 < config.HIT_ZONE_TOP
    assert config.HIT_ZONE_TOP < config.HIT_ZONE_BOTTOM
    assert config.HIT_ZONE_BOTTOM < config.WINDOW_H


@pytest.mark.unit
def test_tile_height_and_visual_gap_are_strictly_positive() -> None:
    assert config.TILE_HEIGHT > 0
    assert config.TILE_VISUAL_GAP_PX > 0


@pytest.mark.unit
def test_phases_are_well_formed() -> None:
    """Each phase must be a (speed, duration) pair of positive floats."""
    assert config.PHASES, "PHASES must contain at least one entry"
    for speed, duration in config.PHASES:
        assert speed > 0
        assert duration > 0


@pytest.mark.unit
def test_phase_speeds_are_non_decreasing() -> None:
    """Speeds must never go down. The ramp may plateau (e.g. after phase 5)."""
    speeds = [speed for speed, _ in config.PHASES]
    assert speeds == sorted(speeds)


@pytest.mark.unit
def test_phase_speed_ramp_stops_after_phase_five() -> None:
    """Phases 5/6/7 share the top speed — the difficulty curve plateaus there."""
    speeds = [speed for speed, _ in config.PHASES]
    assert len(speeds) >= 5
    top_speed = speeds[4]
    for s in speeds[4:]:
        assert s == top_speed


@pytest.mark.unit
def test_lane_width_divides_window_evenly() -> None:
    """Lane widths must tile the window without leftover pixels — avoids visual gaps."""
    assert config.LANE_WIDTH * config.LANE_COUNT == config.WINDOW_W


def _color_constants() -> list[tuple[str, object]]:
    return [
        (name, getattr(config, name))
        for name in dir(config)
        if name.endswith("_COLOR") and not name.startswith("_")
    ]


@pytest.mark.unit
def test_color_constants_exist() -> None:
    """At least the documented color constants must exist."""
    required = {
        "BG_COLOR",
        "LANE_DIVIDER_COLOR",
        "HIT_ZONE_COLOR",
        "TILE_FALLING_COLOR",
        "TILE_HELD_COLOR",
        "SCORE_TEXT_COLOR",
    }
    names = {name for name, _ in _color_constants()}
    missing = required - names
    assert not missing, f"missing color constants: {missing}"


@pytest.mark.unit
def test_color_constants_are_valid_rgb_tuples() -> None:
    """Every *_COLOR constant must be a 3-tuple of ints in 0..255."""
    for name, value in _color_constants():
        assert isinstance(value, tuple), f"{name} is not a tuple"
        assert len(value) == 3, f"{name} has length {len(value)}, expected 3"
        for channel in value:
            assert isinstance(channel, int), f"{name} channel {channel!r} is not int"
            assert 0 <= channel <= 255, f"{name} channel {channel} out of 0..255"


# ---- per-song palettes ----------------------------------------------------


def _all_palettes() -> dict[str, object]:
    return {
        "DEFAULT_PALETTE": config.DEFAULT_PALETTE,
        "MINT_BLUSH": config.MINT_BLUSH,
        "PEACH_SORBET": config.PEACH_SORBET,
        "ARCTIC": config.ARCTIC,
    }


@pytest.mark.unit
def test_every_palette_colour_is_a_valid_rgb_tuple() -> None:
    """Each Palette field must be a 3-tuple of ints in 0..255."""
    fields = (
        "background",
        "hit_zone",
        "tile_falling",
        "tile_held",
        "menu_band",
        "paused_band",
        "game_over_band",
    )
    for name, palette in _all_palettes().items():
        for field in fields:
            value = getattr(palette, field)
            assert isinstance(value, tuple) and len(value) == 3, f"{name}.{field}"
            assert all(isinstance(c, int) and 0 <= c <= 255 for c in value), (
                f"{name}.{field} = {value}"
            )


@pytest.mark.unit
def test_default_palette_matches_the_classic_constants() -> None:
    """DEFAULT_PALETTE is the classic theme — its fields mirror the globals so
    GameState's default keeps the original look."""
    p = config.DEFAULT_PALETTE
    assert p.background == config.BG_COLOR
    assert p.hit_zone == config.HIT_ZONE_COLOR
    assert p.tile_falling == config.TILE_FALLING_COLOR
    assert p.tile_held == config.TILE_HELD_COLOR
    assert p.menu_band == config.MENU_OVERLAY_COLOR
    assert p.paused_band == config.PAUSED_OVERLAY_COLOR
    assert p.game_over_band == config.GAME_OVER_OVERLAY_COLOR


@pytest.mark.unit
@pytest.mark.parametrize(
    "name, palette",
    [
        ("MINT_BLUSH", config.MINT_BLUSH),
        ("PEACH_SORBET", config.PEACH_SORBET),
        ("ARCTIC", config.ARCTIC),
    ],
)
def test_song_band_colors_are_dark_enough_for_white_text(name, palette) -> None:
    """The per-song bands carry white text, so each must be dark enough to
    contrast (perceived luminance well under mid-grey). The classic
    DEFAULT_PALETTE is exempt — its bright yellow PAUSED band predates this."""
    for field in ("menu_band", "paused_band", "game_over_band"):
        r, g, b = getattr(palette, field)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        assert luminance < 140, f"{name}.{field} too light for white text"


@pytest.mark.unit
def test_songs_are_themed_as_requested() -> None:
    """Slow Dancing → Mint & Blush; Loose → Peach Sorbet; Yesterday → Arctic."""
    by_title = {song.title: song for song in config.SONGS}
    assert by_title["Slow Dancing In The Dark"].palette is config.MINT_BLUSH
    assert by_title["Loose"].palette is config.PEACH_SORBET
    assert by_title["Yesterday"].palette is config.ARCTIC


@pytest.mark.unit
def test_every_song_has_a_palette() -> None:
    for song in config.SONGS:
        assert isinstance(song.palette, config.Palette)


@pytest.mark.unit
def test_every_song_track_is_an_existing_asset_file() -> None:
    """Each song's track must be an absolute path under assets/ that exists —
    a missing/misnamed track is a real failure mode, surface it loudly."""
    for song in config.SONGS:
        assert song.path.is_absolute(), f"{song.title}: path not absolute"
        assert song.path.parent.name == "assets", f"{song.title}: not under assets/"
        assert song.path.is_file(), f"{song.title}: missing track at {song.path}"


@pytest.mark.unit
def test_overlay_colors_are_mutually_distinct() -> None:
    """Per-state overlay bands must be visually distinguishable from each other
    and from the background."""
    overlays = {
        config.MENU_OVERLAY_COLOR,
        config.PAUSED_OVERLAY_COLOR,
        config.GAME_OVER_OVERLAY_COLOR,
    }
    assert len(overlays) == 3
    assert config.BG_COLOR not in overlays


@pytest.mark.unit
def test_phase_banner_icons_covers_every_phase_after_the_first() -> None:
    """Phase 1 is the starting phase (no banner). Every phase we advance INTO
    needs a banner mapping."""
    for idx in range(1, len(config.PHASES)):
        phase_number = idx + 1
        assert phase_number in config.PHASE_BANNER_ICONS, (
            f"PHASE_BANNER_ICONS is missing phase {phase_number}"
        )


@pytest.mark.unit
def test_phase_one_has_no_banner_mapping() -> None:
    """We start in phase 1 — no transition fires, so no banner is shown."""
    assert 1 not in config.PHASE_BANNER_ICONS


@pytest.mark.unit
def test_phase_banner_icons_use_known_keys() -> None:
    """Every banner icon key must correspond to a real asset file we can show."""
    for icon, count in config.PHASE_BANNER_ICONS.values():
        assert icon in {"star", "crown"}, f"unknown banner icon: {icon!r}"
        assert count >= 1


@pytest.mark.unit
def test_banner_timing_is_strictly_positive() -> None:
    assert config.BANNER_FADE_IN_SECONDS > 0
    assert config.BANNER_HOLD_SECONDS > 0
    assert config.BANNER_FADE_OUT_SECONDS > 0


@pytest.mark.unit
def test_banner_total_lifetime_is_three_seconds() -> None:
    """The banner should be on screen for three seconds — fade-in + hold + fade-out."""
    total = (
        config.BANNER_FADE_IN_SECONDS
        + config.BANNER_HOLD_SECONDS
        + config.BANNER_FADE_OUT_SECONDS
    )
    assert total == pytest.approx(3.0)


@pytest.mark.unit
def test_wrong_key_flash_constants_are_well_formed() -> None:
    assert config.WRONG_KEY_FLASH_DURATION > 0
    assert config.WRONG_KEY_FLASH_COUNT >= 1
    assert len(config.WRONG_KEY_FLASH_COLOR) == 3


@pytest.mark.unit
def test_game_over_fade_was_removed_entirely() -> None:
    """Pin the no-fade contract. A fade timer (under any name) re-introduces the
    'black line for the first second' bug."""
    assert not hasattr(config, "GAME_OVER_FADE_IN_SECONDS")
    assert not hasattr(config, "GAME_OVER_ZOOM_FROM")


@pytest.mark.unit
def test_overlay_band_lies_inside_window() -> None:
    assert 0 < config.OVERLAY_BAND_TOP < config.OVERLAY_BAND_BOTTOM < config.WINDOW_H


@pytest.mark.unit
def test_score_position_lies_inside_window() -> None:
    assert 0 <= config.SCORE_POS_X < config.WINDOW_W
    assert 0 <= config.SCORE_POS_Y < config.WINDOW_H


@pytest.mark.unit
def test_font_sizes_are_positive() -> None:
    assert config.SCORE_FONT_SIZE > 0
    assert config.OVERLAY_FONT_SIZE > 0


# ---- background music -----------------------------------------------------


@pytest.mark.unit
def test_bgm_path_is_absolute() -> None:
    """Resolved at import time so the asset is found regardless of cwd."""
    assert config.BGM_PATH.is_absolute()


@pytest.mark.unit
def test_bgm_path_points_to_an_existing_file() -> None:
    """Missing music asset is a real failure mode — surface it loudly in CI
    rather than letting the game silently launch with no sound."""
    assert config.BGM_PATH.exists(), f"BGM asset not found at {config.BGM_PATH}"
    assert config.BGM_PATH.is_file()


@pytest.mark.unit
def test_bgm_path_lives_under_the_repo_assets_directory() -> None:
    """Pin the location — if the asset is moved, this test forces a config update."""
    assert config.BGM_PATH.parent.name == "assets"


@pytest.mark.unit
def test_bgm_path_does_not_depend_on_cwd(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolving from a different cwd must yield the same absolute path."""
    import importlib

    original = config.BGM_PATH
    monkeypatch.chdir(tmp_path)
    reloaded = importlib.reload(config)
    assert reloaded.BGM_PATH == original


@pytest.mark.unit
def test_bgm_game_over_volume_is_within_unit_range() -> None:
    assert 0.0 <= config.BGM_GAME_OVER_VOLUME <= 1.0


@pytest.mark.unit
def test_bgm_game_over_volume_is_strictly_below_one() -> None:
    """The point of the constant is to *duck* the volume — full volume would
    be indistinguishable from active play."""
    assert config.BGM_GAME_OVER_VOLUME < 1.0
