"""Entry point for the game loop."""

import pygame

from src.core.game_manager import GameManager
from src.entities.bullet import Bullet
from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import FPS, HEIGHT, SCREEN_TITLE, WIDTH
from src.utils.settings_store import settings


def main() -> None:
    pygame.init()

    # Load settings first (before display, so we can apply fullscreen)
    settings.load()

    # Apply display mode from saved settings
    flags = pygame.FULLSCREEN | pygame.SCALED if settings.fullscreen else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption(SCREEN_TITLE)
    clock = pygame.time.Clock()

    # Load all visual assets eagerly — must happen after display.set_mode()
    assets.load_all()

    # Pre-compute rocket sprite so the first shot doesn't freeze the game
    Bullet.eager_init()

    # Initialise audio — must happen after pygame.init()
    audio.init()

    # Apply saved volume preferences immediately
    audio.set_sfx_volume(settings.sfx_volume)
    audio.set_music_volume(settings.music_volume)

    manager = GameManager(screen)
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                result = manager.handle_event(event)
                if result == "quit":
                    running = False

        manager.update(dt)
        manager.render()
        pygame.display.flip()

    audio.teardown()
    pygame.quit()


if __name__ == "__main__":
    main()
