"""UI tests for `PygameMusicPlayer` — the production music seam.

These run under `SDL_VIDEODRIVER=dummy` + `SDL_AUDIODRIVER=dummy` (set in
`tests/conftest.py`) so no real audio device is required. We assert the
contract — no-raise on every method, volume round-trips, missing path raises,
volume clamping holds, and the mixer is not double-initialized — but we do
*not* assert that the dummy audio driver flips `is_playing` to True, since
that's unreliable under SDL's dummy backend.
"""

import pathlib

import pygame
import pytest

from piano_tiles.pygame_seams import PygameMusicPlayer

pytestmark = pytest.mark.ui

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BGM_PATH = REPO_ROOT / "assets" / "SDITD.ogg"


@pytest.fixture
def pygame_inited():
    """Ensure pygame is initialized before each test; tear down after."""
    pygame.init()
    yield
    pygame.mixer.music.stop()  # leave no music bleeding across tests


# ---- construction ---------------------------------------------------------


def test_construct_after_pygame_init_does_not_raise(pygame_inited: None) -> None:
    PygameMusicPlayer()


def test_constructor_initializes_mixer_when_not_yet_initialized(
    pygame_inited: None,
) -> None:
    """First-init branch: if the mixer was somehow uninitialized, ctor inits it."""
    pygame.mixer.quit()
    assert pygame.mixer.get_init() is None
    PygameMusicPlayer()
    assert pygame.mixer.get_init() is not None


def test_constructor_is_idempotent_across_multiple_instances(
    pygame_inited: None,
) -> None:
    """Already-init branch: second ctor must not re-init the mixer."""
    PygameMusicPlayer()
    snapshot = pygame.mixer.get_init()
    assert snapshot is not None
    PygameMusicPlayer()
    assert pygame.mixer.get_init() == snapshot


def test_constructor_does_not_call_mixer_init_when_already_initialized(
    pygame_inited: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reinforce the guard: pygame.mixer.init must not be called the second time."""
    PygameMusicPlayer()
    calls = {"n": 0}

    real_init = pygame.mixer.init

    def counting_init(*args: object, **kwargs: object) -> None:
        calls["n"] += 1
        real_init(*args, **kwargs)

    monkeypatch.setattr(pygame.mixer, "init", counting_init)
    PygameMusicPlayer()
    assert calls["n"] == 0


# ---- play -----------------------------------------------------------------


def test_play_with_valid_asset_does_not_raise(pygame_inited: None) -> None:
    assert BGM_PATH.exists(), f"missing fixture asset: {BGM_PATH}"
    player = PygameMusicPlayer()
    player.play(str(BGM_PATH))


def test_play_with_loop_false_does_not_raise(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.play(str(BGM_PATH), loop=False)


def test_play_with_nonexistent_path_raises_pygame_error(
    pygame_inited: None,
    tmp_path: pathlib.Path,
) -> None:
    """Edge: missing-file errors must surface — silent absence would mask bugs."""
    player = PygameMusicPlayer()
    bogus = tmp_path / "no-such-track.ogg"
    with pytest.raises(pygame.error):
        player.play(str(bogus))


# ---- pause / resume / stop ------------------------------------------------


def test_pause_then_resume_round_trip_does_not_raise(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.play(str(BGM_PATH))
    player.pause()
    player.resume()


def test_stop_does_not_raise_and_clears_is_playing(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.play(str(BGM_PATH))
    player.stop()
    assert player.is_playing is False


def test_stop_on_idle_player_does_not_raise(pygame_inited: None) -> None:
    """Edge: stop with nothing loaded must be a quiet no-op, not an exception."""
    player = PygameMusicPlayer()
    player.stop()
    assert player.is_playing is False


# ---- set_volume / volume --------------------------------------------------


def test_set_volume_round_trips_through_get_volume(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.set_volume(0.3)
    assert player.volume == pytest.approx(0.3, abs=0.02)


def test_set_volume_clamps_below_zero_to_zero(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.set_volume(-0.1)
    assert player.volume == pytest.approx(0.0, abs=0.02)


def test_set_volume_clamps_above_one_to_one(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.set_volume(1.5)
    assert player.volume == pytest.approx(1.0, abs=0.02)


def test_set_volume_at_zero_boundary(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.set_volume(0.0)
    assert player.volume == pytest.approx(0.0, abs=0.02)


def test_set_volume_at_one_boundary(pygame_inited: None) -> None:
    player = PygameMusicPlayer()
    player.set_volume(1.0)
    assert player.volume == pytest.approx(1.0, abs=0.02)
