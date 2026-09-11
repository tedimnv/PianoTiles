"""Unit tests for `MusicDirector` — the event→audio policy, tested in
isolation against a ScriptedMusicPlayer. Game's end-to-end wiring is covered
separately in `test_game_music.py`; here we pin the policy itself."""

import pytest

from piano_tiles.components.state_machine import Event
from piano_tiles.config import BGM_GAME_OVER_VOLUME, BGM_PATH
from piano_tiles.music import MusicDirector
from tests.scripted import ScriptedMusicPlayer

pytestmark = pytest.mark.unit


def _make() -> tuple[MusicDirector, ScriptedMusicPlayer]:
    player = ScriptedMusicPlayer()
    return MusicDirector(player), player


# ---- start / restart: full volume then play from the top ------------------


@pytest.mark.parametrize("event", [Event.START, Event.RESTART])
def test_start_and_restart_set_full_volume_then_play(event: Event) -> None:
    director, player = _make()
    director.react_to(event)
    assert player.calls == [("set_volume", 1.0), ("play", str(BGM_PATH), True)]
    assert player.is_playing is True


# ---- pause / resume --------------------------------------------------------


def test_pause_pauses_the_player() -> None:
    director, player = _make()
    director.react_to(Event.PAUSE)
    assert player.calls == [("pause",)]


def test_resume_resumes_the_player() -> None:
    director, player = _make()
    director.react_to(Event.RESUME)
    assert player.calls == [("resume",)]


# ---- die ducks but keeps playing ------------------------------------------


def test_die_ducks_volume_without_stopping() -> None:
    director, player = _make()
    director.react_to(Event.DIE)
    assert player.calls == [("set_volume", BGM_GAME_OVER_VOLUME)]


# ---- quit ------------------------------------------------------------------


def test_quit_stops_the_player() -> None:
    director, player = _make()
    director.react_to(Event.QUIT)
    assert player.calls == [("stop",)]


# ---- return to main menu ---------------------------------------------------


def test_to_main_menu_stops_the_player() -> None:
    """Back at song selection — the current track stops."""
    director, player = _make()
    director.react_to(Event.TO_MAIN_MENU)
    assert player.calls == [("stop",)]


# ---- track selection -------------------------------------------------------


def test_use_track_changes_what_the_next_play_loads() -> None:
    director, player = _make()
    director.use_track("chosen.ogg")
    director.react_to(Event.START)
    assert player.calls == [("set_volume", 1.0), ("play", "chosen.ogg", True)]


# ---- events that intentionally leave the music untouched ------------------


def test_wrong_key_emits_no_music_calls() -> None:
    """WRONG_KEY enters the red flash; the music keeps playing untouched and
    only ducks when DIE later lands the player in GAME_OVER."""
    director, player = _make()
    director.react_to(Event.WRONG_KEY)
    assert player.calls == []


# ---- injectable path / volume ---------------------------------------------


def test_custom_path_and_game_over_volume_are_used() -> None:
    """The policy reads its track and duck level from construction, so callers
    can retune without touching the player."""
    player = ScriptedMusicPlayer()
    director = MusicDirector(player, bgm_path="other.ogg", game_over_volume=0.1)
    director.react_to(Event.START)
    director.react_to(Event.DIE)
    assert player.calls == [
        ("set_volume", 1.0),
        ("play", "other.ogg", True),
        ("set_volume", 0.1),
    ]
