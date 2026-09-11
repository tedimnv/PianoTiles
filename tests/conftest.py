import os
import random

# Force pygame to use the dummy SDL driver so any test that ends up importing
# pygame.display runs headlessly (no window). Set this at conftest import time,
# before any test module imports pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
# Same for audio — the music seam's UI tests need pygame.mixer to init even on
# machines/CI runners with no audio device. Real audio output is never asserted.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, dt: float) -> float:
        if dt < 0:
            raise ValueError("dt must be non-negative")
        self.now += dt
        return self.now


@pytest.fixture
def seeded_rng() -> random.Random:
    return random.Random(0)


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def headless_surface():
    import pygame

    pygame.display.init()
    surface = pygame.Surface((480, 720))
    yield surface
    pygame.display.quit()
