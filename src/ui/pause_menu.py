"""PauseMenu — in-game pause overlay.

Shows the full SettingsScreen (volume, fullscreen, language) plus a
"Resume" button at the top. The ☰ button in the HUD opens this overlay;
clicking Resume (or pressing Escape) closes it and resumes the game.
"""

from __future__ import annotations

import pygame

from src.ui.settings_screen import SettingsScreen
from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import FONT_SIZE_NORMAL, FONT_SIZE_TITLE, HEIGHT, WIDTH
from src.utils.strings import t

_OVERLAY_COLOR = (0, 0, 15, 170)

class PauseMenu:
    """Draws on top of the frozen game frame; returns 'resume' when closed."""

    def __init__(self) -> None:
        self._settings = SettingsScreen(in_game=True)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Return 'resume' to unpause, None to stay paused."""
        # Escape key also resumes
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            audio.play_sfx("click")
            return "resume"

        # Delegate to settings screen (handles buttons)
        result = self._settings.handle_event(event)
        if result in ("resume", "main_menu"):
            return result

        return None

    def draw(self, screen: pygame.Surface) -> None:
        # Dark overlay (game scene is already drawn beneath)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(_OVERLAY_COLOR)
        screen.blit(overlay, (0, 0))

        # Settings panel (handles its own bottom buttons now)
        self._settings.draw(screen)
