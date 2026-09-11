"""High-level game state machine. Pure Python; no pygame imports."""

from enum import Enum

from piano_tiles.models.state import State


class Event(Enum):
    SELECT_SONG = "select_song"  # MAIN_MENU → MENU (a song was chosen)
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    WRONG_KEY = "wrong_key"  # PLAYING → DYING (wrong-lane press)
    DIE = "die"              # PLAYING → GAME_OVER (missed tile)  /  DYING → GAME_OVER (flash done)
    RESTART = "restart"
    TO_MAIN_MENU = "to_main_menu"  # GAME_OVER → MAIN_MENU (player pressed M)
    QUIT = "quit"


class InvalidTransition(Exception):
    """Raised when an event is not allowed from the current state."""


TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.MAIN_MENU, Event.SELECT_SONG): State.MENU,
    (State.MENU, Event.START): State.PLAYING,
    (State.PLAYING, Event.PAUSE): State.PAUSED,
    (State.PAUSED, Event.RESUME): State.PLAYING,
    (State.PLAYING, Event.WRONG_KEY): State.DYING,
    (State.PLAYING, Event.DIE): State.GAME_OVER,
    (State.DYING, Event.DIE): State.GAME_OVER,
    (State.GAME_OVER, Event.RESTART): State.PLAYING,
    (State.GAME_OVER, Event.TO_MAIN_MENU): State.MAIN_MENU,
    (State.MAIN_MENU, Event.QUIT): State.QUIT,
    (State.MENU, Event.QUIT): State.QUIT,
    (State.PLAYING, Event.QUIT): State.QUIT,
    (State.PAUSED, Event.QUIT): State.QUIT,
    (State.DYING, Event.QUIT): State.QUIT,
    (State.GAME_OVER, Event.QUIT): State.QUIT,
}


class StateMachine:
    def __init__(self) -> None:
        self._state: State = State.MAIN_MENU

    @property
    def state(self) -> State:
        return self._state

    def process(self, event: Event) -> State:
        if not isinstance(event, Event):
            raise TypeError(
                f"event must be a State Machine Event, got {type(event).__name__}"
            )
        try:
            next_state = TRANSITIONS[(self._state, event)]
        except KeyError:
            raise InvalidTransition(
                f"no transition from {self._state.name} on event {event.name}"
            ) from None
        self._state = next_state
        return self._state
