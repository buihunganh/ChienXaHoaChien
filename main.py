"""Entry point for the game loop."""

import pygame

from src.core.game_manager import GameManager
from src.utils.constants import FPS, HEIGHT, SCREEN_TITLE, WIDTH


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(SCREEN_TITLE)
    clock = pygame.time.Clock()

    manager = GameManager(screen)
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.render()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
