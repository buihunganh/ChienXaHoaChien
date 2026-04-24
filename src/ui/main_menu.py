"""Stylized multi-screen main menu that simulates the provided mockups."""

from dataclasses import dataclass

import pygame

from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE, HEIGHT, WIDTH
from src.utils.strings import t


@dataclass
class MenuButton:
    """Simple rounded button model used by all menu screens."""

    label: str
    rect: pygame.Rect
    fill_top: tuple[int, int, int]
    fill_bottom: tuple[int, int, int]
    border: tuple[int, int, int]
    action: str
    subtitle: str = ""
    is_locked: bool = False
    thumbnail_key: str | None = None


class MainMenu:
    """Menu flow: home -> mode -> difficulty -> level select."""

    def __init__(self) -> None:
        self.state = "home"
        self.title_font = assets.get_font(FONT_SIZE_TITLE)
        self.big_font   = assets.get_font(FONT_SIZE_TITLE)
        self.btn_font   = assets.get_font(FONT_SIZE_TITLE)
        self.text_font  = assets.get_font(FONT_SIZE_NORMAL)
        self.small_font = assets.get_font(FONT_SIZE_SMALL)

        self.selected_mode = "PVP"
        self.selected_difficulty = "Medium"

        from src.core.map_config import get_map_config, MAP_CATALOGUE
        self.get_map_config = get_map_config
        
        self._home_buttons = self._build_home_buttons()
        self._mode_buttons = self._build_mode_buttons()
        self._difficulty_buttons = self._build_difficulty_buttons()
        self._level_buttons = self._build_level_buttons()

        # Lazy-import to avoid circular deps at module level
        from src.ui.settings_screen import SettingsScreen
        self._settings_screen = SettingsScreen()

        self.back_button = MenuButton(
            label=t("back"),
            rect=pygame.Rect(26, 24, 160, 56),
            fill_top=(248, 248, 244),
            fill_bottom=(224, 224, 217),
            border=(74, 74, 74),
            action="back",
        )

    def _build_home_buttons(self) -> list[MenuButton]:
        center_x = WIDTH // 2
        width = 460
        height = 108
        gap = 30
        start_y = 168

        return [
            MenuButton(
                label=t("menu_start"),
                rect=pygame.Rect(center_x - width // 2, start_y, width, height),
                fill_top=(167, 228, 83),
                fill_bottom=(86, 182, 58),
                border=(42, 126, 46),
                action="go_mode",
            ),
            MenuButton(
                label=t("menu_settings"),
                rect=pygame.Rect(center_x - width // 2, start_y + (height + gap), width, height),
                fill_top=(108, 213, 252),
                fill_bottom=(45, 148, 229),
                border=(36, 102, 178),
                action="go_settings",
            ),
            MenuButton(
                label=t("menu_guide"),
                rect=pygame.Rect(center_x - width // 2, start_y + 2 * (height + gap), width, height),
                fill_top=(255, 234, 111),
                fill_bottom=(244, 180, 55),
                border=(173, 122, 35),
                action="go_guide",
            ),
        ]

    def _build_mode_buttons(self) -> list[MenuButton]:
        center_x = WIDTH // 2
        width = 640
        height = 132
        return [
            MenuButton(
                label="PVP",
                rect=pygame.Rect(center_x - width // 2, 168, width, height),
                fill_top=(255, 133, 79),
                fill_bottom=(214, 72, 26),
                border=(155, 46, 19),
                action="mode_pvp",
                subtitle=t("mode_pvp_sub"),
            ),
            MenuButton(
                label="PVE",
                rect=pygame.Rect(center_x - width // 2, 348, width, height),
                fill_top=(255, 239, 108),
                fill_bottom=(241, 196, 56),
                border=(171, 128, 30),
                action="mode_pve",
                subtitle=t("mode_pve_sub"),
            ),
        ]

    def _build_difficulty_buttons(self) -> list[MenuButton]:
        center_x = WIDTH // 2
        width = 460
        height = 104
        gap = 28
        start_y = 156
        return [
            MenuButton(
                label=t("diff_easy"),
                rect=pygame.Rect(center_x - width // 2, start_y, width, height),
                fill_top=(170, 228, 89),
                fill_bottom=(84, 180, 56),
                border=(42, 126, 46),
                action="difficulty_easy",
            ),
            MenuButton(
                label=t("diff_medium"),
                rect=pygame.Rect(center_x - width // 2, start_y + (height + gap), width, height),
                fill_top=(108, 212, 252),
                fill_bottom=(46, 150, 230),
                border=(36, 102, 178),
                action="difficulty_medium",
            ),
            MenuButton(
                label=t("diff_hard"),
                rect=pygame.Rect(center_x - width // 2, start_y + 2 * (height + gap), width, height),
                fill_top=(255, 234, 112),
                fill_bottom=(244, 183, 58),
                border=(173, 122, 35),
                action="difficulty_hard",
            ),
        ]

    def _build_level_buttons(self) -> list[MenuButton]:
        from src.utils.settings_store import settings
        cards: list[MenuButton] = []
        card_w = 320
        card_h = 186
        gap_x = 36
        gap_y = 36
        start_x = 112
        start_y = 150

        for idx in range(6):
            col = idx % 3
            row = idx // 3
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)
            
            level_id = idx + 1
            config = self.get_map_config(level_id)
            
            # Determine if this level is locked
            is_locked = False
            # Hard lock maps 4, 5, 6 for now as they are not designed yet
            if level_id > 3:
                is_locked = True
            elif self.selected_mode == "PVE" and level_id > settings.max_unlocked_level:
                is_locked = True
                
            label = config.name
            action = f"level_{level_id}" if not is_locked else "locked"

            cards.append(
                MenuButton(
                    label=label,
                    rect=pygame.Rect(x, y, card_w, card_h),
                    fill_top=(140, 223, 251),
                    fill_bottom=(67, 170, 236),
                    border=(49, 116, 181),
                    action=action,
                    subtitle=t("level_locked") if is_locked else t("level_ready"),
                    is_locked=is_locked,
                    thumbnail_key=config.thumbnail_image,
                )
            )

        return cards

    def _draw_background(self, screen: pygame.Surface) -> None:
        """Blit main menu background image; fallback to procedural gradient."""
        bg = assets.get_image("bg/main_menu")
        if bg is not None:
            # Scale to screen if needed
            if bg.get_size() != (WIDTH, HEIGHT):
                bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
            screen.blit(bg, (0, 0))
            return

        # --- Fallback: original procedural gradient ---
        for y in range(HEIGHT):
            t = y / max(1, HEIGHT - 1)
            if t < 0.62:
                k = t / 0.62
                color = (
                    int(105 + (178 - 105) * k),
                    int(199 + (236 - 199) * k),
                    int(255 - 10 * k),
                )
            else:
                k = (t - 0.62) / 0.38
                color = (
                    int(115 + (142 - 115) * k),
                    int(210 + (233 - 210) * k),
                    int(112 - 26 * k),
                )
            pygame.draw.line(screen, color, (0, y), (WIDTH, y))

        pygame.draw.ellipse(screen, (163, 226, 121), (-80, 505, 600, 270))
        pygame.draw.ellipse(screen, (142, 214, 100), (350, 500, 700, 270))
        pygame.draw.ellipse(screen, (126, 201, 88), (870, 515, 520, 250))

        for x, y, r in [(130, 134, 120), (1110, 140, 128), (640, 172, 170)]:
            pygame.draw.circle(screen, (235, 252, 255), (x, y), r, width=0)
            pygame.draw.circle(screen, (220, 246, 255), (x + 25, y + 12), int(r * 0.72), width=0)

    def _draw_button(self, screen: pygame.Surface, btn: MenuButton, active: bool = False) -> None:
        shadow = btn.rect.move(0, 6)
        pygame.draw.rect(screen, (40, 80, 55, 80), shadow, border_radius=28)

        # Draw thumbnail if available
        if btn.thumbnail_key:
            thumb = assets.get_image(btn.thumbnail_key)
            if thumb:
                thumb = pygame.transform.smoothscale(thumb, (btn.rect.width, btn.rect.height))
                screen.blit(thumb, btn.rect)
                # Overlay for better text readability
                overlay = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 80))
                screen.blit(overlay, btn.rect)
        else:
            half_h = btn.rect.height // 2
            top = pygame.Rect(btn.rect.left, btn.rect.top, btn.rect.width, half_h)
            bottom = pygame.Rect(btn.rect.left, btn.rect.top + half_h, btn.rect.width, btn.rect.height - half_h)
            pygame.draw.rect(screen, btn.fill_top, top, border_top_left_radius=28, border_top_right_radius=28)
            pygame.draw.rect(screen, btn.fill_bottom, bottom, border_bottom_left_radius=28, border_bottom_right_radius=28)

        # Draw lock icon if locked
        if btn.is_locked:
            lock_icon = assets.get_image("icons/lock_map")
            if lock_icon:
                # Dim the button
                dim = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 150))
                screen.blit(dim, btn.rect)
                # Draw lock
                lock_scaled = pygame.transform.smoothscale(lock_icon, (64, 64))
                screen.blit(lock_scaled, lock_scaled.get_rect(center=btn.rect.center))
            else:
                # Fallback lock text
                lock_label = self.btn_font.render("LOCKED", True, (255, 100, 100))
                screen.blit(lock_label, lock_label.get_rect(center=btn.rect.center))

        border_color = (255, 255, 255) if active else btn.border
        border_width = 5 if active else 4
        pygame.draw.rect(screen, border_color, btn.rect, width=border_width, border_radius=28)

        if not btn.is_locked:
            gloss = pygame.Rect(btn.rect.left + 16, btn.rect.top + 10, btn.rect.width - 150, 20)
            pygame.draw.ellipse(screen, (255, 255, 255, 120), gloss)

        label_color = (255, 255, 255) if btn.thumbnail_key else (41, 50, 61)
        if btn.is_locked: label_color = (150, 150, 150)
        
        label = self.btn_font.render(btn.label, True, label_color)
        label_rect = label.get_rect(center=(btn.rect.centerx, btn.rect.centery - 6))
        screen.blit(label, label_rect)

        if btn.subtitle:
            sub = self.small_font.render(btn.subtitle, True, label_color)
            sub_rect = sub.get_rect(center=(btn.rect.centerx, btn.rect.centery + 28))
            screen.blit(sub, sub_rect)

    def _handle_click(self, pos: tuple[int, int]) -> str | None:
        if self.state != "home" and self.back_button.rect.collidepoint(pos):
            if self.state in ("mode", "settings", "guide"):
                self.state = "home"
            elif self.state == "difficulty":
                self.state = "mode"
            elif self.state == "levels":
                # If we bypassed difficulty (PVP), go back to mode
                if self.selected_mode == "PVP":
                    self.state = "mode"
                else:
                    self.state = "difficulty"
            return None

        if self.state == "home":
            for btn in self._home_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.action == "go_mode":
                        self.state = "mode"
                    elif btn.action == "go_settings":
                        self.state = "settings"
                    elif btn.action == "go_guide":
                        self.state = "guide"
                    return None

        if self.state == "mode":
            for btn in self._mode_buttons:
                if btn.rect.collidepoint(pos):
                    self.selected_mode = "PVP" if btn.action == "mode_pvp" else "PVE"
                    if self.selected_mode == "PVP":
                        self.state = "levels"
                        self._level_buttons = self._build_level_buttons()
                    else:
                        self.state = "difficulty"
                    return None

        if self.state == "difficulty":
            for btn in self._difficulty_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.action == "difficulty_easy":
                        self.selected_difficulty = "Easy"
                    elif btn.action == "difficulty_medium":
                        self.selected_difficulty = "Medium"
                    else:
                        self.selected_difficulty = "Hard"
                    self.state = "levels"
                    return None

        if self.state == "levels":
            for btn in self._level_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.action == "locked":
                        return None
                    # action is "level_X"
                    level_id = int(btn.action.split("_")[1])
                    return ("start", level_id)

        return None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # Settings screen consumes events while active
        if self.state == "settings":
            result = self._settings_screen.handle_event(event)
            if result == "close":
                self.state = "home"
                audio.play_sfx("click")
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.state == "home":
                self.state = "mode"
                return None
            if event.key == pygame.K_ESCAPE and self.state != "home":
                self.state = "home"
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)

        return None

    def _draw_top_title(self, screen: pygame.Surface, text: str) -> None:
        title = self.big_font.render(text, True, (34, 92, 147))
        outline = self.big_font.render(text, True, (219, 244, 255))
        screen.blit(outline, (WIDTH // 2 - outline.get_width() // 2 - 3, 34))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

    def _draw_guide(self, screen: pygame.Surface) -> None:
        self._draw_top_title(screen, t("guide_title"))
        panel = pygame.Rect(WIDTH // 2 - 420, 148, 840, 420)
        pygame.draw.rect(screen, (251, 250, 240), panel, border_radius=28)
        pygame.draw.rect(screen, (176, 133, 53), panel, width=4, border_radius=28)

        rules = [
            t("guide_line1"),
            t("guide_line2"),
            t("guide_line3"),
            t("guide_line4"),
            t("guide_line5"),
        ]
        for idx, rule in enumerate(rules):
            text = self.text_font.render(rule, True, (40, 54, 67))
            screen.blit(text, (panel.left + 38, panel.top + 62 + idx * 64))

    def draw(self, screen: pygame.Surface) -> None:
        self._draw_background(screen)

        # Settings screen overlays on top of background
        if self.state == "settings":
            self._settings_screen.draw(screen)
            return

        if self.state == "home":
            for btn in self._home_buttons:
                self._draw_button(screen, btn)
            return

        self._draw_button(screen, self.back_button)

        if self.state == "mode":
            self._draw_top_title(screen, t("mode_title"))
            for btn in self._mode_buttons:
                active = (btn.action == "mode_pvp" and self.selected_mode == "PVP") or (
                    btn.action == "mode_pve" and self.selected_mode == "PVE"
                )
                self._draw_button(screen, btn, active=active)
            return

        if self.state == "difficulty":
            self._draw_top_title(screen, t("diff_title"))
            for btn in self._difficulty_buttons:
                active = (
                    (btn.action == "difficulty_easy" and self.selected_difficulty == "Easy")
                    or (btn.action == "difficulty_medium" and self.selected_difficulty == "Medium")
                    or (btn.action == "difficulty_hard" and self.selected_difficulty == "Hard")
                )
                self._draw_button(screen, btn, active=active)
            return

        if self.state == "levels":
            self._draw_top_title(screen, t("level_title"))
            mode_text = self.small_font.render(
                f"{t('mode_title')}: {self.selected_mode} | {t('diff_title')}: {self.selected_difficulty}",
                True,
                (38, 70, 98),
            )
            screen.blit(mode_text, (WIDTH // 2 - mode_text.get_width() // 2, 114))
            for btn in self._level_buttons:
                self._draw_button(screen, btn, active=(btn.action != "locked"))
            return

        if self.state == "settings":
            self._draw_settings(screen)
            return

        if self.state == "guide":
            self._draw_guide(screen)
