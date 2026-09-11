import os

import pytest


@pytest.mark.ui
def test_ui_placeholder_creates_headless_surface(headless_surface) -> None:
    """Initializing pygame with SDL_VIDEODRIVER=dummy must produce a real Surface."""
    import pygame

    assert os.environ.get("SDL_VIDEODRIVER") == "dummy"
    assert isinstance(headless_surface, pygame.Surface)
    assert headless_surface.get_size() == (480, 720)
