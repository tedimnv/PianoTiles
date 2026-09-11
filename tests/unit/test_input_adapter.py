import pygame
import pytest

from piano_tiles.components.input_adapter import (
    InputAdapter,
    InputEvent,
    InputEventKind,
    key_code,
)
from piano_tiles.config import LANE_KEYS, MENU_KEY, PAUSE_KEY, QUIT_KEY, RESTART_KEY


class FakeEvent:
    """Duck-typed stand-in for `pygame.event.Event`."""

    def __init__(
        self,
        type_: int,
        key: int | None = None,
        pos: tuple[int, int] | None = None,
    ) -> None:
        self.type = type_
        self.key = key
        self.pos = pos


def _keydown(key: int) -> FakeEvent:
    return FakeEvent(pygame.KEYDOWN, key)


def _keyup(key: int) -> FakeEvent:
    return FakeEvent(pygame.KEYUP, key)


def _window_close() -> FakeEvent:
    return FakeEvent(pygame.QUIT)


def _mouse_down(pos: tuple[int, int]) -> FakeEvent:
    return FakeEvent(pygame.MOUSEBUTTONDOWN, pos=pos)


# ---- LANE_PRESS mapping ----------------------------------------------------


@pytest.mark.unit
def test_each_lane_key_produces_corresponding_lane_press() -> None:
    adapter = InputAdapter()
    for i, name in enumerate(LANE_KEYS):
        result = adapter.translate([_keydown(key_code(name))])
        assert result == [InputEvent(InputEventKind.LANE_PRESS, lane=i)]


# ---- single-event keys -----------------------------------------------------


@pytest.mark.unit
def test_pause_key_produces_pause() -> None:
    adapter = InputAdapter()
    result = adapter.translate([_keydown(key_code(PAUSE_KEY))])
    assert result == [InputEvent(InputEventKind.PAUSE)]


@pytest.mark.unit
def test_restart_key_produces_restart() -> None:
    adapter = InputAdapter()
    result = adapter.translate([_keydown(key_code(RESTART_KEY))])
    assert result == [InputEvent(InputEventKind.RESTART)]


@pytest.mark.unit
def test_quit_key_produces_quit() -> None:
    adapter = InputAdapter()
    result = adapter.translate([_keydown(key_code(QUIT_KEY))])
    assert result == [InputEvent(InputEventKind.QUIT)]


@pytest.mark.unit
def test_menu_key_produces_menu() -> None:
    adapter = InputAdapter()
    result = adapter.translate([_keydown(key_code(MENU_KEY))])
    assert result == [InputEvent(InputEventKind.MENU)]


# ---- mouse clicks ----------------------------------------------------------


@pytest.mark.unit
def test_mouse_button_down_produces_click_carrying_its_position() -> None:
    adapter = InputAdapter()
    result = adapter.translate([_mouse_down((123, 456))])
    assert result == [InputEvent(InputEventKind.CLICK, pos=(123, 456))]


@pytest.mark.unit
def test_mouse_button_up_is_ignored() -> None:
    """Only the button press matters for menu selection."""
    adapter = InputAdapter()
    assert adapter.translate([FakeEvent(pygame.MOUSEBUTTONUP, pos=(1, 2))]) == []


@pytest.mark.unit
def test_window_close_event_produces_quit() -> None:
    """A pygame.QUIT event (window close button) maps to QUIT."""
    adapter = InputAdapter()
    result = adapter.translate([_window_close()])
    assert result == [InputEvent(InputEventKind.QUIT)]


# ---- unmapped / ignored events --------------------------------------------


@pytest.mark.unit
def test_unmapped_keydown_produces_no_event() -> None:
    adapter = InputAdapter()
    # K_z is not in the default keymap.
    assert adapter.translate([_keydown(pygame.K_z)]) == []


@pytest.mark.unit
def test_keyup_for_lane_keys_produces_lane_release() -> None:
    """KEYUP for lane keys is meaningful — it ends a long-tile hold."""
    adapter = InputAdapter()
    for i, name in enumerate(LANE_KEYS):
        result = adapter.translate([_keyup(key_code(name))])
        assert result == [InputEvent(InputEventKind.LANE_RELEASE, lane=i)]


@pytest.mark.unit
def test_keyup_for_control_keys_is_ignored() -> None:
    """Pause / restart / quit are KEYDOWN-only; their releases produce nothing."""
    adapter = InputAdapter()
    assert adapter.translate([_keyup(key_code(PAUSE_KEY))]) == []
    assert adapter.translate([_keyup(key_code(RESTART_KEY))]) == []
    assert adapter.translate([_keyup(key_code(QUIT_KEY))]) == []


@pytest.mark.unit
def test_non_keyboard_event_type_is_ignored() -> None:
    """A non-KEYDOWN, non-QUIT event type produces nothing."""
    adapter = InputAdapter()
    mouse_motion = FakeEvent(pygame.MOUSEMOTION)
    assert adapter.translate([mouse_motion]) == []


@pytest.mark.unit
def test_empty_event_batch_returns_empty_list() -> None:
    adapter = InputAdapter()
    assert adapter.translate([]) == []


# ---- ordering & batching ---------------------------------------------------


@pytest.mark.unit
def test_multiple_events_returned_in_order() -> None:
    adapter = InputAdapter()
    raw = [
        _keydown(key_code(LANE_KEYS[0])),
        _keydown(key_code(PAUSE_KEY)),
        _keydown(key_code(LANE_KEYS[3])),
        _keydown(key_code(QUIT_KEY)),
    ]
    result = adapter.translate(raw)
    assert result == [
        InputEvent(InputEventKind.LANE_PRESS, lane=0),
        InputEvent(InputEventKind.PAUSE),
        InputEvent(InputEventKind.LANE_PRESS, lane=3),
        InputEvent(InputEventKind.QUIT),
    ]


@pytest.mark.unit
def test_mixed_batch_keeps_only_translatable_events_in_order() -> None:
    adapter = InputAdapter()
    raw = [
        _keydown(key_code(LANE_KEYS[0])),  # mapped → LANE_PRESS(0)
        _keyup(key_code(PAUSE_KEY)),  # ignored (KEYUP)
        _keydown(pygame.K_z),  # unmapped
        FakeEvent(pygame.MOUSEMOTION),  # ignored (wrong type)
        _window_close(),  # mapped → QUIT
    ]
    result = adapter.translate(raw)
    assert result == [
        InputEvent(InputEventKind.LANE_PRESS, lane=0),
        InputEvent(InputEventKind.QUIT),
    ]


@pytest.mark.unit
def test_same_lane_pressed_twice_produces_two_events() -> None:
    """Repeated KEYDOWNs of the same key produce one event each."""
    adapter = InputAdapter()
    raw = [
        _keydown(key_code(LANE_KEYS[1])),
        _keydown(key_code(LANE_KEYS[1])),
    ]
    result = adapter.translate(raw)
    assert result == [
        InputEvent(InputEventKind.LANE_PRESS, lane=1),
        InputEvent(InputEventKind.LANE_PRESS, lane=1),
    ]


# ---- custom keymap (extensibility) ----------------------------------------


@pytest.mark.unit
def test_custom_keymap_is_respected() -> None:
    adapter = InputAdapter(
        lane_keys=("a", "s"),
        pause_key="space",
        restart_key="return",
        quit_key="q",
    )
    assert adapter.translate([_keydown(pygame.K_a)]) == [
        InputEvent(InputEventKind.LANE_PRESS, lane=0),
    ]
    assert adapter.translate([_keydown(pygame.K_s)]) == [
        InputEvent(InputEventKind.LANE_PRESS, lane=1),
    ]
    assert adapter.translate([_keydown(pygame.K_SPACE)]) == [
        InputEvent(InputEventKind.PAUSE),
    ]
    assert adapter.translate([_keydown(pygame.K_RETURN)]) == [
        InputEvent(InputEventKind.RESTART),
    ]
    assert adapter.translate([_keydown(pygame.K_q)]) == [
        InputEvent(InputEventKind.QUIT),
    ]


@pytest.mark.unit
def test_default_lane_keys_no_longer_map_when_overridden() -> None:
    """If the user supplies a custom lane_keys tuple, the defaults stop mapping."""
    adapter = InputAdapter(lane_keys=("a", "s", "k", "l"))
    # 'd' and 'f' are no longer lane keys for this adapter.
    assert adapter.translate([_keydown(pygame.K_d)]) == []
    assert adapter.translate([_keydown(pygame.K_f)]) == []


# ---- key_code helper -------------------------------------------------------


@pytest.mark.unit
def test_key_code_resolves_letter_names() -> None:
    assert key_code("d") == pygame.K_d
    assert key_code("k") == pygame.K_k


@pytest.mark.unit
def test_key_code_resolves_named_keys_case_insensitively() -> None:
    assert key_code("escape") == pygame.K_ESCAPE
    assert key_code("ESCAPE") == pygame.K_ESCAPE
    assert key_code("Space") == pygame.K_SPACE


@pytest.mark.unit
def test_key_code_raises_on_unknown_name() -> None:
    with pytest.raises(ValueError, match=r"must resolve to a pygame key, got"):
        key_code("not_a_real_key_name")


@pytest.mark.unit
def test_translate_accepts_any_iterable_not_just_list() -> None:
    """raw_events is typed as Iterable; a tuple or generator works equally well."""
    adapter = InputAdapter()
    code = key_code(LANE_KEYS[0])
    as_tuple = adapter.translate((_keydown(code),))
    as_gen = adapter.translate(_keydown(code) for _ in range(1))
    expected = [InputEvent(InputEventKind.LANE_PRESS, lane=0)]
    assert as_tuple == expected
    assert as_gen == expected


# ---- InputEvent shape ------------------------------------------------------


@pytest.mark.unit
def test_input_event_is_frozen() -> None:
    e = InputEvent(InputEventKind.PAUSE)
    with pytest.raises(Exception):
        e.lane = 0  # type: ignore[misc]


@pytest.mark.unit
def test_input_event_default_lane_is_none() -> None:
    assert InputEvent(InputEventKind.QUIT).lane is None
