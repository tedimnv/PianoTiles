"""Tests for the `main.py` entry point — thin glue, exits cleanly on QUIT."""

import pathlib

import pygame
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MAIN_PY = REPO_ROOT / "main.py"


@pytest.mark.ui
def test_main_exits_cleanly_when_quit_event_is_posted_immediately() -> None:
    """A pre-seeded QUIT in the event queue makes the loop exit on the first poll."""
    import main  # deferred so SDL_VIDEODRIVER=dummy (set in conftest) is in effect

    pygame.init()
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert main.main() == 0


@pytest.mark.unit
def test_main_module_is_a_thin_entry_point() -> None:
    """`main.py` is glue only. Bound non-blank line count to keep game logic out."""
    non_blank = [line for line in MAIN_PY.read_text().splitlines() if line.strip()]
    assert len(non_blank) <= 30, (
        f"main.py has {len(non_blank)} non-blank lines; "
        f"keep game logic out of the entry point"
    )


@pytest.mark.unit
def test_main_has_no_while_loop() -> None:
    """The frame loop belongs in Game.run() — main.py must not contain its own."""
    src = MAIN_PY.read_text()
    assert "while" not in src, "main.py must not contain a while-loop"


@pytest.mark.unit
def test_main_has_only_the_name_guard_if() -> None:
    """The only `if` in main.py should be the `if __name__ == "__main__"` guard."""
    if_lines = [
        line.strip()
        for line in MAIN_PY.read_text().splitlines()
        if line.lstrip().startswith("if ")
    ]
    assert all("__name__" in line for line in if_lines), (
        f"unexpected `if` statements in main.py: {if_lines}"
    )
