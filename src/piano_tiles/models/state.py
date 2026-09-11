"""High-level game state — the value type consumed by `StateMachine`, `GameState`, and `Renderer`."""

from enum import Enum


class State(Enum):
    MAIN_MENU = "main_menu"  # boot screen: controls + song selection
    MENU = "menu"            # post-selection "press SPACE to start" screen
    PLAYING = "playing"
    PAUSED = "paused"
    DYING = "dying"  # transient — wrong-key flash plays out before GAME_OVER
    GAME_OVER = "game_over"
    QUIT = "quit"
