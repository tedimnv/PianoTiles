"""Unit tests for the MusicPlayer seam — covers ScriptedMusicPlayer (the fake
tests use to assert call sequences) and SilentMusicPlayer (the no-op default
that lets the bulk of the test suite ignore audio entirely)."""

import pytest

from piano_tiles.music import SilentMusicPlayer
from tests.scripted import ScriptedMusicPlayer

pytestmark = pytest.mark.unit


# ---- ScriptedMusicPlayer: initial state -----------------------------------


def test_scripted_initial_state_is_idle() -> None:
    player = ScriptedMusicPlayer()
    assert player.is_playing is False
    assert player.volume == 1.0
    assert player.calls == []


# ---- ScriptedMusicPlayer: play --------------------------------------------


def test_play_records_path_and_loop_and_marks_playing() -> None:
    player = ScriptedMusicPlayer()
    player.play("x")
    assert player.calls == [("play", "x", True)]
    assert player.is_playing is True


def test_play_with_loop_false_records_loop_false() -> None:
    player = ScriptedMusicPlayer()
    player.play("track.ogg", loop=False)
    assert player.calls == [("play", "track.ogg", False)]


def test_play_while_already_playing_overwrites_with_new_call() -> None:
    """Matches pygame.mixer.music.play contract — calling play again restarts."""
    player = ScriptedMusicPlayer()
    player.play("a")
    player.play("b")
    assert player.calls == [("play", "a", True), ("play", "b", True)]
    assert player.is_playing is True


def test_play_does_not_reset_volume() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(0.5)
    player.play("x")
    assert player.volume == 0.5


# ---- ScriptedMusicPlayer: pause / resume ----------------------------------


def test_pause_then_resume_toggles_is_playing() -> None:
    player = ScriptedMusicPlayer()
    player.play("x")
    player.pause()
    assert player.is_playing is False
    player.resume()
    assert player.is_playing is True
    assert player.calls == [
        ("play", "x", True),
        ("pause",),
        ("resume",),
    ]


def test_pause_twice_in_a_row_is_idempotent() -> None:
    """Edge: second pause still records the call but state stays paused."""
    player = ScriptedMusicPlayer()
    player.play("x")
    player.pause()
    player.pause()
    assert player.is_playing is False
    assert player.calls == [("play", "x", True), ("pause",), ("pause",)]


def test_resume_with_no_prior_play_is_a_noop_for_state() -> None:
    """Edge: resume before anything has played leaves is_playing False."""
    player = ScriptedMusicPlayer()
    player.resume()
    assert player.is_playing is False
    assert player.calls == [("resume",)]


def test_resume_while_already_playing_is_a_noop_for_state() -> None:
    player = ScriptedMusicPlayer()
    player.play("x")
    player.resume()
    assert player.is_playing is True


# ---- ScriptedMusicPlayer: stop --------------------------------------------


def test_stop_clears_is_playing_from_playing_state() -> None:
    player = ScriptedMusicPlayer()
    player.play("x")
    player.stop()
    assert player.is_playing is False
    assert player.calls == [("play", "x", True), ("stop",)]


def test_stop_clears_is_playing_from_paused_state() -> None:
    player = ScriptedMusicPlayer()
    player.play("x")
    player.pause()
    player.stop()
    assert player.is_playing is False


def test_stop_when_nothing_is_playing_is_a_noop_no_exception() -> None:
    """Edge: stop on a fresh player records but does not raise."""
    player = ScriptedMusicPlayer()
    player.stop()  # must not raise
    assert player.is_playing is False
    assert player.calls == [("stop",)]


# ---- ScriptedMusicPlayer: set_volume --------------------------------------


def test_set_volume_records_and_updates_volume() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(0.5)
    assert player.calls == [("set_volume", 0.5)]
    assert player.volume == 0.5


def test_set_volume_clamps_below_zero_to_zero() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(-0.1)
    assert player.volume == 0.0


def test_set_volume_clamps_above_one_to_one() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(1.5)
    assert player.volume == 1.0


def test_set_volume_at_zero_boundary_holds() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(0.0)
    assert player.volume == 0.0


def test_set_volume_at_one_boundary_holds() -> None:
    player = ScriptedMusicPlayer()
    player.set_volume(1.0)
    assert player.volume == 1.0


def test_set_volume_records_original_unclamped_input() -> None:
    """The call log captures what the caller passed, not the clamped result —
    useful for asserting `Game` passes through the configured constant."""
    player = ScriptedMusicPlayer()
    player.set_volume(1.5)
    assert player.calls == [("set_volume", 1.5)]


# ---- SilentMusicPlayer ----------------------------------------------------


def test_silent_player_accepts_every_call_without_raising() -> None:
    player = SilentMusicPlayer()
    player.play("anywhere.ogg")
    player.play("anywhere.ogg", loop=False)
    player.pause()
    player.resume()
    player.stop()
    player.set_volume(0.5)
    player.set_volume(-1.0)
    player.set_volume(2.0)


def test_silent_player_never_reports_playing() -> None:
    player = SilentMusicPlayer()
    player.play("x")
    assert player.is_playing is False
    player.resume()
    assert player.is_playing is False


def test_silent_player_volume_is_zero() -> None:
    """Silent is silent — volume is meaningless. Stays at 0.0 regardless."""
    player = SilentMusicPlayer()
    player.set_volume(1.0)
    assert player.volume == 0.0
