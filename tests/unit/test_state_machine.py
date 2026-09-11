import pytest

from piano_tiles.components.state_machine import (
    Event,
    InvalidTransition,
    State,
    StateMachine,
)


def _menu() -> StateMachine:
    """A machine advanced to the post-selection 'press SPACE' MENU."""
    sm = StateMachine()
    sm.process(Event.SELECT_SONG)
    return sm


def _playing() -> StateMachine:
    sm = _menu()
    sm.process(Event.START)
    return sm


@pytest.mark.unit
def test_initial_state_is_main_menu() -> None:
    sm = StateMachine()
    assert sm.state == State.MAIN_MENU


@pytest.mark.unit
def test_main_menu_select_song_transitions_to_menu() -> None:
    sm = StateMachine()
    assert sm.process(Event.SELECT_SONG) == State.MENU
    assert sm.state == State.MENU


@pytest.mark.unit
def test_menu_start_transitions_to_playing() -> None:
    sm = _menu()
    assert sm.process(Event.START) == State.PLAYING
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_playing_pause_transitions_to_paused() -> None:
    sm = _playing()
    assert sm.process(Event.PAUSE) == State.PAUSED
    assert sm.state == State.PAUSED


@pytest.mark.unit
def test_paused_resume_transitions_to_playing() -> None:
    sm = _playing()
    sm.process(Event.PAUSE)
    assert sm.process(Event.RESUME) == State.PLAYING
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_playing_die_transitions_to_game_over() -> None:
    """A missed tile fires DIE directly; the run goes straight to GAME_OVER."""
    sm = _playing()
    assert sm.process(Event.DIE) == State.GAME_OVER
    assert sm.state == State.GAME_OVER


@pytest.mark.unit
def test_playing_wrong_key_transitions_to_dying() -> None:
    """Wrong-lane press triggers the transient DYING state (red flash)."""
    sm = _playing()
    assert sm.process(Event.WRONG_KEY) == State.DYING
    assert sm.state == State.DYING


@pytest.mark.unit
def test_dying_die_transitions_to_game_over() -> None:
    """Once the red flash finishes, DIE moves DYING → GAME_OVER."""
    sm = _playing()
    sm.process(Event.WRONG_KEY)
    assert sm.process(Event.DIE) == State.GAME_OVER
    assert sm.state == State.GAME_OVER


@pytest.mark.unit
def test_game_over_restart_transitions_to_playing() -> None:
    sm = _playing()
    sm.process(Event.DIE)
    assert sm.process(Event.RESTART) == State.PLAYING
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_game_over_to_main_menu_transitions_back_to_main_menu() -> None:
    """Pressing M from GAME_OVER returns to the song-selection screen."""
    sm = _playing()
    sm.process(Event.DIE)
    assert sm.process(Event.TO_MAIN_MENU) == State.MAIN_MENU
    assert sm.state == State.MAIN_MENU


@pytest.mark.unit
@pytest.mark.parametrize(
    "setup_events",
    [
        [],  # MAIN_MENU
        [Event.SELECT_SONG],  # MENU
        [Event.SELECT_SONG, Event.START],  # PLAYING
        [Event.SELECT_SONG, Event.START, Event.PAUSE],  # PAUSED
        [Event.SELECT_SONG, Event.START, Event.WRONG_KEY],  # DYING
        [Event.SELECT_SONG, Event.START, Event.DIE],  # GAME_OVER
    ],
)
def test_quit_transitions_to_terminal_quit_from_any_state(setup_events) -> None:
    sm = StateMachine()
    for ev in setup_events:
        sm.process(ev)
    assert sm.process(Event.QUIT) == State.QUIT
    assert sm.state == State.QUIT


@pytest.mark.unit
def test_quit_state_is_terminal_no_event_is_accepted() -> None:
    sm = StateMachine()
    sm.process(Event.QUIT)
    for ev in Event:
        with pytest.raises(InvalidTransition):
            sm.process(ev)
        assert sm.state == State.QUIT


@pytest.mark.unit
def test_invalid_transition_raises_and_does_not_change_state() -> None:
    sm = _menu()  # in MENU
    with pytest.raises(InvalidTransition):
        sm.process(Event.PAUSE)
    assert sm.state == State.MENU


@pytest.mark.unit
def test_resume_while_playing_is_rejected() -> None:
    """Idempotency edge case: RESUME from PLAYING is not allowed."""
    sm = _playing()
    with pytest.raises(InvalidTransition):
        sm.process(Event.RESUME)
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_pause_while_paused_is_rejected() -> None:
    sm = _playing()
    sm.process(Event.PAUSE)
    with pytest.raises(InvalidTransition):
        sm.process(Event.PAUSE)
    assert sm.state == State.PAUSED


@pytest.mark.unit
def test_start_from_main_menu_is_rejected() -> None:
    """A song must be selected first — START is invalid from MAIN_MENU."""
    sm = StateMachine()
    with pytest.raises(InvalidTransition):
        sm.process(Event.START)
    assert sm.state == State.MAIN_MENU


@pytest.mark.unit
def test_die_from_menu_is_rejected() -> None:
    sm = _menu()
    with pytest.raises(InvalidTransition):
        sm.process(Event.DIE)
    assert sm.state == State.MENU


@pytest.mark.unit
def test_wrong_key_from_menu_is_rejected() -> None:
    sm = _menu()
    with pytest.raises(InvalidTransition):
        sm.process(Event.WRONG_KEY)
    assert sm.state == State.MENU


@pytest.mark.unit
def test_select_song_from_playing_is_rejected() -> None:
    """You can't re-pick a song mid-run."""
    sm = _playing()
    with pytest.raises(InvalidTransition):
        sm.process(Event.SELECT_SONG)
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_to_main_menu_from_playing_is_rejected() -> None:
    """M only works from GAME_OVER, not mid-run."""
    sm = _playing()
    with pytest.raises(InvalidTransition):
        sm.process(Event.TO_MAIN_MENU)
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_restart_from_playing_is_rejected() -> None:
    sm = _playing()
    with pytest.raises(InvalidTransition):
        sm.process(Event.RESTART)
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_start_from_playing_is_rejected() -> None:
    sm = _playing()
    with pytest.raises(InvalidTransition):
        sm.process(Event.START)
    assert sm.state == State.PLAYING


@pytest.mark.unit
def test_restart_from_dying_is_rejected() -> None:
    """During the red flash the player can't shortcut to a fresh run."""
    sm = _playing()
    sm.process(Event.WRONG_KEY)
    with pytest.raises(InvalidTransition):
        sm.process(Event.RESTART)
    assert sm.state == State.DYING


@pytest.mark.unit
def test_unknown_event_type_raises_type_error() -> None:
    sm = StateMachine()
    with pytest.raises(TypeError):
        sm.process("start")  # type: ignore[arg-type]


@pytest.mark.unit
def test_unknown_event_type_does_not_change_state() -> None:
    sm = StateMachine()
    try:
        sm.process(42)  # type: ignore[arg-type]
    except TypeError:
        pass
    assert sm.state == State.MAIN_MENU
