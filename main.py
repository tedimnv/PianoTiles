"""Entry point — opens a real window and runs the Game loop."""

import sys

import pygame

from piano_tiles.components.renderer import Renderer
from piano_tiles.config import WINDOW_H, WINDOW_W
from piano_tiles.game import Game
from piano_tiles.pygame_seams import PygameClock, PygameEventSource, PygameMusicPlayer


def main() -> int:
    pygame.init()
    surface = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Piano Tiles")
    game = Game(
        clock=PygameClock(),
        events=PygameEventSource(),
        surface=surface,
        renderer=Renderer(),
        music=PygameMusicPlayer(),
    )
    try:
        game.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
