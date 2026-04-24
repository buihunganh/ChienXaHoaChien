"""SettingsScreen — functional settings panel with sliders, toggle, language selector.

Controls:
    - SFX volume slider (with volume icon)
    - Music volume slider (with volume icon)
    - Fullscreen toggle (pill switch)
    - Language selector (VI | EN pill buttons)
    - Save & Close button

All changes take effect immediately; Save & Close writes to disk and returns "close".
"""

from __future__ import annotations

import pygame

from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE, HEIGHT, WIDTH
from src.utils.settings_store import settings
from src.utils.strings import t


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
_PANEL_BG     = (18, 28, 52, 230)
_PANEL_BORDER = (60, 110, 190)
_TRACK_BG     = (30, 55, 110)
_TRACK_FILL   = (72, 160, 240)
_HANDLE       = (255, 255, 255)
_TOGGLE_OFF   = (90, 90, 110)
_TOGGLE_ON    = (72, 195, 100)
_BTN_ACTIVE   = (47, 130, 220)
_BTN_INACTIVE = (38, 52, 88)
_TEXT_MAIN    = (230, 240, 255)
_TEXT_DIM     = (140, 160, 200)
_SAVE_BTN_TOP = (100, 210, 90)
_SAVE_BTN_BOT = (55, 158, 50)
_SAVE_BORDER  = (38, 115, 38)


class Slider:
    """Horizontal drag slider for a float value 0.0–1.0."""

    TRACK_H = 14
    HANDLE_R = 11

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect    = rect   # full bounding box
        self._drag   = False

    def draw(self, screen: pygame.Surface, value: float, label: str,
             font: pygame.font.Font, small_font: pygame.font.Font,
             icon: pygame.Surface | None = None) -> None:
        ix = self.rect.left
        iy = self.rect.top + 10

        # Icon
        if icon is not None:
            icon_scaled = pygame.transform.smoothscale(icon, (28, 28))
            screen.blit(icon_scaled, (ix, iy))
            ix += 36

        # Label
        lbl = font.render(label, True, _TEXT_MAIN)
        screen.blit(lbl, (ix, iy))

        # Percentage text (right-aligned)
        pct_text = small_font.render(f"{int(value * 100)}%", True, _TEXT_DIM)
        screen.blit(pct_text, (self.rect.right - pct_text.get_width(), iy))

        # Track
        ty = self.rect.top + 52
        track = pygame.Rect(self.rect.left, ty - self.TRACK_H // 2,
                            self.rect.width, self.TRACK_H)
        pygame.draw.rect(screen, _TRACK_BG, track, border_radius=7)

        # Fill
        fill_w = int(track.width * max(0.0, min(1.0, value)))
        if fill_w > 0:
            fill = pygame.Rect(track.left, track.top, fill_w, track.height)
            pygame.draw.rect(screen, _TRACK_FILL, fill, border_radius=7)

        pygame.draw.rect(screen, _PANEL_BORDER, track, width=2, border_radius=7)

        # Handle
        hx = track.left + fill_w
        pygame.draw.circle(screen, _HANDLE, (hx, ty), self.HANDLE_R)
        pygame.draw.circle(screen, _TRACK_FILL, (hx, ty), self.HANDLE_R, width=3)

    def handle_event(self, event: pygame.event.Event) -> float | None:
        """Return new value 0.0–1.0 if changed, else None."""
        ty = self.rect.top + 52
        track = pygame.Rect(self.rect.left, ty - 20, self.rect.width, 40)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if track.collidepoint(event.pos):
                self._drag = True
                return self._value_from_x(event.pos[0])

        if event.type == pygame.MOUSEMOTION and self._drag:
            return self._value_from_x(event.pos[0])

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False

        return None

    def _value_from_x(self, x: int) -> float:
        left  = self.rect.left
        right = self.rect.right
        return max(0.0, min(1.0, (x - left) / max(1, right - left)))


class SettingsScreen:
    """Interactive settings panel drawn on top of the menu background."""

    _PANEL_W = 700
    _PANEL_H = 520

    def __init__(self) -> None:
        self.font       = assets.get_font(FONT_SIZE_NORMAL)
        self.small_font = assets.get_font(FONT_SIZE_SMALL)
        self.title_font = assets.get_font(FONT_SIZE_TITLE)
        self._vol_icon  = assets.get_image("icons/volume")

        cx = WIDTH // 2
        cy = HEIGHT // 2
        px = cx - self._PANEL_W // 2
        py = cy - self._PANEL_H // 2

        slider_w = self._PANEL_W - 80

        self._sfx_slider   = Slider(pygame.Rect(px + 40, py + 100, slider_w, 70))
        self._music_slider = Slider(pygame.Rect(px + 40, py + 200, slider_w, 70))

        # Toggle rect (fullscreen)
        self._toggle_rect = pygame.Rect(px + self._PANEL_W - 100, py + 300, 70, 34)


        # Save & Close button
        btn_w = 220
        self._save_rect = pygame.Rect(cx - btn_w // 2, py + self._PANEL_H - 70, btn_w, 50)

        # Panel rect (for background)
        self._panel_rect = pygame.Rect(px, py, self._PANEL_W, self._PANEL_H)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Return 'close' when the player saves and exits, else None."""

        # SFX slider
        val = self._sfx_slider.handle_event(event)
        if val is not None:
            settings.sfx_volume = val
            audio.set_sfx_volume(val)

        # Music slider
        val = self._music_slider.handle_event(event)
        if val is not None:
            settings.music_volume = val
            audio.set_music_volume(val)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Fullscreen toggle
            if self._toggle_rect.collidepoint(event.pos):
                settings.fullscreen = not settings.fullscreen
                self._apply_fullscreen(settings.fullscreen)

            # Save & Close
            if self._save_rect.collidepoint(event.pos):
                settings.save()
                return "close"

        return None

    def draw(self, screen: pygame.Surface) -> None:
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 15, 150))
        screen.blit(overlay, (0, 0))

        # Panel background
        panel_surf = pygame.Surface((self._PANEL_W, self._PANEL_H), pygame.SRCALPHA)
        panel_surf.fill(_PANEL_BG)
        screen.blit(panel_surf, self._panel_rect.topleft)
        pygame.draw.rect(screen, _PANEL_BORDER, self._panel_rect, width=3, border_radius=18)

        px, py = self._panel_rect.topleft

        # Title
        title = self.title_font.render(t("settings_title"), True, _TEXT_MAIN)
        screen.blit(title, (self._panel_rect.centerx - title.get_width() // 2, py + 28))

        # Divider
        pygame.draw.line(screen, _PANEL_BORDER,
                         (px + 30, py + 80), (px + self._PANEL_W - 30, py + 80), 1)

        # Sliders
        self._sfx_slider.draw(screen, settings.sfx_volume,
                               t("settings_sfx"), self.font, self.small_font, self._vol_icon)
        self._music_slider.draw(screen, settings.music_volume,
                                t("settings_music"), self.font, self.small_font, self._vol_icon)

        # Fullscreen section
        fs_lbl = self.font.render(t("settings_fullscreen"), True, _TEXT_MAIN)
        screen.blit(fs_lbl, (px + 40, py + 308))
        self._draw_toggle(screen, settings.fullscreen)


        # Save & Close button
        self._draw_save_button(screen)

    # ------------------------------------------------------------------
    # Private drawing helpers
    # ------------------------------------------------------------------

    def _draw_toggle(self, screen: pygame.Surface, on: bool) -> None:
        color = _TOGGLE_ON if on else _TOGGLE_OFF
        pygame.draw.rect(screen, color, self._toggle_rect, border_radius=17)
        pygame.draw.rect(screen, _HANDLE, self._toggle_rect, width=2, border_radius=17)

        # Handle pill
        if on:
            hx = self._toggle_rect.right - 20
        else:
            hx = self._toggle_rect.left + 20
        hy = self._toggle_rect.centery
        pygame.draw.circle(screen, _HANDLE, (hx, hy), 13)

        # ON/OFF text inside toggle
        state_txt = self.small_font.render(t("settings_on") if on else t("settings_off"),
                                           True, _HANDLE)
        if on:
            tx = self._toggle_rect.left + 6
        else:
            tx = self._toggle_rect.right - state_txt.get_width() - 22
        screen.blit(state_txt, (tx, hy - state_txt.get_height() // 2))


    def _draw_save_button(self, screen: pygame.Surface) -> None:
        r = self._save_rect
        half = r.height // 2
        top_r = pygame.Rect(r.left, r.top, r.width, half)
        bot_r = pygame.Rect(r.left, r.top + half, r.width, r.height - half)
        pygame.draw.rect(screen, _SAVE_BTN_TOP, top_r,
                         border_top_left_radius=25, border_top_right_radius=25)
        pygame.draw.rect(screen, _SAVE_BTN_BOT, bot_r,
                         border_bottom_left_radius=25, border_bottom_right_radius=25)
        pygame.draw.rect(screen, _SAVE_BORDER, r, width=3, border_radius=25)
        lbl = self.font.render(t("settings_save"), True, (20, 40, 20))
        screen.blit(lbl, lbl.get_rect(center=r.center))

    @staticmethod
    def _apply_fullscreen(enabled: bool) -> None:
        try:
            if enabled:
                pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
            else:
                from src.utils.constants import WIDTH, HEIGHT
                pygame.display.set_mode((WIDTH, HEIGHT))
        except Exception as exc:
            print(f"[SettingsScreen] Fullscreen toggle failed: {exc}")
