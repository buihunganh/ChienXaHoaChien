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


_RESUME_TOP = (72, 200, 90)
_RESUME_BOT = (42, 148, 58)
_RESUME_BDR = (28, 110, 40)
_OVERLAY_COLOR = (0, 0, 15, 170)


class PauseMenu:
    """Draws on top of the frozen game frame; returns 'resume' when closed."""

    def __init__(self) -> None:
        self._settings = SettingsScreen()
        self.font      = assets.get_font(FONT_SIZE_TITLE)
        self.btn_font  = assets.get_font(FONT_SIZE_NORMAL)

        btn_w = 220
        # Resume button sits above the settings panel
        self._resume_rect = pygame.Rect(WIDTH // 2 - btn_w // 2, 30, btn_w, 52)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Return 'resume' to unpause, None to stay paused."""
        # Escape key also resumes
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            audio.play_sfx("click")
            return "resume"

        # Resume button click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._resume_rect.collidepoint(event.pos):
                audio.play_sfx("click")
                return "resume"

        # Delegate to settings screen (Save & Close also resumes)
        result = self._settings.handle_event(event)
        if result == "close":
            return "resume"

        return None

    def draw(self, screen: pygame.Surface) -> None:
        # Dark overlay (game scene is already drawn beneath)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(_OVERLAY_COLOR)
        screen.blit(overlay, (0, 0))

        # Resume button
        r = self._resume_rect
        half = r.height // 2
        pygame.draw.rect(screen, _RESUME_TOP,
                         pygame.Rect(r.left, r.top, r.width, half),
                         border_top_left_radius=26, border_top_right_radius=26)
        pygame.draw.rect(screen, _RESUME_BOT,
                         pygame.Rect(r.left, r.top + half, r.width, r.height - half),
                         border_bottom_left_radius=26, border_bottom_right_radius=26)
        pygame.draw.rect(screen, _RESUME_BDR, r, width=3, border_radius=26)
        lbl = self.btn_font.render(t("settings_save").split("&")[0].strip() + " ▶  Resume", True, (10, 30, 10))
        screen.blit(lbl, lbl.get_rect(center=r.center))

        # Settings panel (reused from Phase 3)
        self._settings.draw(screen)
