"""Stylized HUD inspired by Gunny-like battle interface.

Phase 1 upgrade:
- Custom font loaded via AssetManager (gunbai.ttf)
- Static label surfaces pre-rendered in __init__() — not every frame
- HUD panel frames loaded from ui/ sprites; fallback to pygame.draw primitives
"""

import pygame

from src.entities.bullet import BulletType
from src.entities.tank import Tank
from src.utils.asset_manager import assets
from src.utils.constants import (
    BLACK,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    HEIGHT,
    SHOT_POWER_MAX,
    SHOT_POWER_MIN,
    WHITE,
    WIDTH,
    WIND_MAX,
)


class HUD:
    def __init__(self) -> None:
        self.font       = assets.get_font(FONT_SIZE_NORMAL)
        self.small_font = assets.get_font(FONT_SIZE_SMALL)
        self.tiny_font  = assets.get_font(FONT_SIZE_TINY)

        # Load panel images (may be None — fallback to primitives)
        self._panel_left  = assets.get_image("ui/panel_left")
        self._panel_right = assets.get_image("ui/panel_right")
        self._shield_vs   = assets.get_image("ui/shield_vs")
        self._power_bg    = assets.get_image("ui/power_bar_bg")

        # Pre-render STATIC text labels — never re-render these each frame
        self._lbl_wind  = self.font.render("Wind", True, (46, 76, 128))
        self._lbl_power = self.font.render("Power", True, (70, 47, 30))
        self._lbl_fuel  = self.font.render("Fuel", True, (82, 50, 32))
        self._lbl_p1    = self.font.render("Player 1", True, WHITE)
        self._lbl_p2    = self.font.render("Player 2", True, WHITE)

        # Settings / pause button rect — used by GameManager for click detection
        self.menu_btn_rect = pygame.Rect(31, 33, 62, 62)

    # ------------------------------------------------------------------
    # Bar helper
    # ------------------------------------------------------------------

    def _draw_rounded_bar(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
        fill_color: tuple[int, int, int],
        frame_color: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(screen, (43, 70, 120), rect, border_radius=12)

        inner = rect.inflate(-8, -8)
        pygame.draw.rect(screen, (28, 45, 82), inner, border_radius=8)
        value_w = int(inner.width * ratio)
        if value_w > 0:
            value_rect = pygame.Rect(inner.left, inner.top, value_w, inner.height)
            pygame.draw.rect(screen, fill_color, value_rect, border_radius=8)

        pygame.draw.rect(screen, frame_color, rect, width=3, border_radius=12)

    # ------------------------------------------------------------------
    # Top health bars
    # ------------------------------------------------------------------

    def _draw_top_health(self, screen: pygame.Surface, left_tank: Tank, right_tank: Tank) -> None:
        left_rect  = pygame.Rect(200, 10, 340, 80)
        right_rect = pygame.Rect(WIDTH - 540, 10, 340, 80)

        # Panel backgrounds (sprite or fallback)
        if self._panel_left is not None:
            screen.blit(self._panel_left, left_rect.topleft)
        else:
            pygame.draw.rect(screen, (18, 28, 52, 180), left_rect, border_radius=14)
            pygame.draw.rect(screen, (47, 123, 178), left_rect, width=3, border_radius=14)

        if self._panel_right is not None:
            screen.blit(self._panel_right, right_rect.topleft)
        else:
            pygame.draw.rect(screen, (18, 28, 52, 180), right_rect, border_radius=14)
            pygame.draw.rect(screen, (186, 67, 86), right_rect, width=3, border_radius=14)

        # Player name labels (pre-rendered statics)
        screen.blit(self._lbl_p1, (left_rect.left + 12, left_rect.top + 6))
        screen.blit(self._lbl_p2, (right_rect.left + 12, right_rect.top + 6))

        # HP bars (dynamic — drawn every frame because HP changes)
        bar_left  = pygame.Rect(left_rect.left + 8,   left_rect.top + 38, left_rect.width - 16, 32)
        bar_right = pygame.Rect(right_rect.left + 8,  right_rect.top + 38, right_rect.width - 16, 32)
        self._draw_rounded_bar(screen, bar_left,  left_tank.hp / 100.0,  (77, 226, 62),  (47, 123, 178))
        self._draw_rounded_bar(screen, bar_right, right_tank.hp / 100.0, (231, 66, 66), (186, 67, 86))

    # ------------------------------------------------------------------
    # VS shield
    # ------------------------------------------------------------------

    def _draw_vs_shield(self, screen: pygame.Surface) -> None:
        center = (WIDTH // 2, 70)
        # Draw a perfectly symmetric shield so left/right halves stay balanced.
        shield = pygame.Surface((140, 124), pygame.SRCALPHA)
        pts = [(70, 6), (128, 34), (118, 94), (70, 118), (22, 94), (12, 34)]
        left_half = [(70, 6), (70, 118), (22, 94), (12, 34)]
        right_half = [(70, 6), (128, 34), (118, 94), (70, 118)]

        pygame.draw.polygon(shield, (69, 147, 222), left_half)
        pygame.draw.polygon(shield, (215, 76, 90), right_half)
        pygame.draw.polygon(shield, (223, 237, 251), pts, width=4)
        pygame.draw.line(shield, (223, 237, 251), (70, 11), (70, 112), 2)

        text = self.font.render("VS", True, WHITE)
        shield.blit(text, text.get_rect(center=(70, 64)))

        rect = shield.get_rect(center=center)
        screen.blit(shield, rect)

    # ------------------------------------------------------------------
    # Wind indicator
    # ------------------------------------------------------------------

    def _draw_wind_center(self, screen: pygame.Surface, wind: float) -> None:
        # Static label (pre-rendered) — blit directly
        screen.blit(self._lbl_wind, (WIDTH // 2 - self._lbl_wind.get_width() // 2, 142))

        # Dynamic: arrow + value (changes every turn)
        wind_max = WIND_MAX if WIND_MAX > 0 else 1.0
        ratio = max(-1.0, min(1.0, wind / wind_max))
        arrow_len = int(95 * abs(ratio))
        direction = 1 if wind >= 0 else -1

        start = (WIDTH // 2, 186)
        end   = (WIDTH // 2 + direction * max(26, arrow_len), 186)
        color = (47, 121, 224)
        pygame.draw.line(screen, color, start, end, 6)
        wing_a = (end[0] - 14 * direction, end[1] - 10)
        wing_b = (end[0] - 14 * direction, end[1] + 10)
        pygame.draw.polygon(screen, color, [end, wing_a, wing_b])

        wind_value = self.font.render(f"{abs(wind) / 100:.1f}".replace(".", ","), True, (30, 62, 110))
        screen.blit(wind_value, (WIDTH // 2 - wind_value.get_width() // 2, 202))

    # ------------------------------------------------------------------
    # Side icon buttons
    # ------------------------------------------------------------------

    def _draw_side_controls(self, screen: pygame.Surface) -> None:
        """Draw the single ☰ settings/pause button (top-left)."""
        x, y = self.menu_btn_rect.centerx, self.menu_btn_rect.centery
        pygame.draw.circle(screen, (54, 141, 220), (x, y), 31)
        pygame.draw.circle(screen, (31, 90, 144), (x, y), 31, width=3)
        # Three-line hamburger icon
        for dy in (-10, 0, 10):
            pygame.draw.line(screen, WHITE, (x - 18, y + dy), (x + 18, y + dy), 4)

    # ------------------------------------------------------------------
    # Power column
    # ------------------------------------------------------------------

    def _draw_power_column(self, screen: pygame.Surface, charge_power: float, is_charging: bool) -> None:
        col_rect = pygame.Rect(32, 282, 44, 248)

        if self._power_bg is not None:
            bg_rect = self._power_bg.get_rect(center=col_rect.inflate(20, 22).center)
            screen.blit(self._power_bg, bg_rect)
        else:
            pygame.draw.rect(screen, (30, 75, 138), col_rect.inflate(10, 10), border_radius=16)
            pygame.draw.rect(screen, (24, 61, 116), col_rect, border_radius=12)

        ratio = max(0.0, min(1.0, (charge_power - SHOT_POWER_MIN) / (SHOT_POWER_MAX - SHOT_POWER_MIN)))
        fill_h = int(col_rect.height * ratio)
        fill_rect = pygame.Rect(col_rect.left + 5, col_rect.bottom - 5 - fill_h, col_rect.width - 10, fill_h)

        if fill_h > 0:
            slices = [
                (90, 233, 96),
                (208, 236, 79),
                (247, 201, 66),
                (242, 129, 57),
                (232, 71, 64),
            ]
            slice_h = max(1, fill_h // len(slices))
            y = fill_rect.bottom
            for color in slices:
                h = min(slice_h, y - fill_rect.top)
                if h <= 0:
                    break
                y -= h
                pygame.draw.rect(screen, color, (fill_rect.left, y, fill_rect.width, h), border_radius=6)

        pygame.draw.rect(screen, (125, 188, 235), col_rect, width=3, border_radius=12)

        # Static "Power" label (pre-rendered)
        screen.blit(self._lbl_power, (14, 542))

        # Dynamic state text
        state = "Charging" if is_charging else "Ready"
        state_txt = self.tiny_font.render(state, True, (35, 63, 100))
        screen.blit(state_txt, (18, 570))

    # ------------------------------------------------------------------
    # Fuel bar near active tank
    # ------------------------------------------------------------------

    def _draw_fuel_near_current_tank(self, screen: pygame.Surface, tank: Tank) -> None:
        x = int(tank.x) - 64
        y = int(tank.y) - 126

        # Static "Fuel" label
        screen.blit(self._lbl_fuel, (x + 24, y - 18))

        rect = pygame.Rect(x, y + 18, 138, 34)
        pygame.draw.rect(screen, (43, 111, 190), rect, border_radius=10)
        pygame.draw.rect(screen, (27, 69, 122), rect.inflate(-8, -8), border_radius=8)

        value_w = int((rect.width - 12) * max(0.0, min(1.0, tank.fuel / 100.0)))
        if value_w > 0:
            pygame.draw.rect(
                screen,
                (248, 192, 66),
                (rect.left + 6, rect.top + 6, value_w, rect.height - 12),
                border_radius=7,
            )
        pygame.draw.rect(screen, (119, 186, 232), rect, width=3, border_radius=10)

    # ------------------------------------------------------------------
    # Ammo chip
    # ------------------------------------------------------------------

    def _draw_ammo_chip(self, screen: pygame.Surface, bullet_type: BulletType) -> None:
        txt = self.small_font.render(
            f"Ammo: {bullet_type.name} | Dmg {bullet_type.damage}",
            True,
            (35, 54, 86),
        )
        # Dynamic width: text width + horizontal padding (40px each side)
        chip_w = txt.get_width() + 80
        chip_h = txt.get_height() + 16
        chip = pygame.Rect(WIDTH // 2 - chip_w // 2, HEIGHT - 52, chip_w, chip_h)
        pygame.draw.rect(screen, (247, 248, 239), chip, border_radius=12)
        pygame.draw.rect(screen, (83, 125, 171), chip, width=2, border_radius=12)

        screen.blit(txt, (chip.centerx - txt.get_width() // 2, chip.centery - txt.get_height() // 2))

    # ------------------------------------------------------------------
    # Main draw entry point
    # ------------------------------------------------------------------

    def draw(
        self,
        screen: pygame.Surface,
        tanks: list[Tank],
        current_turn: int,
        wind: float,
        current_bullet_type: BulletType,
        charge_power: float,
        is_charging: bool,
        aim_ready: bool,
    ) -> None:
        p1 = tanks[0]
        p2 = tanks[1]

        self._draw_top_health(screen, p1, p2)
        self._draw_vs_shield(screen)
        self._draw_wind_center(screen, wind)
        self._draw_side_controls(screen)
        self._draw_power_column(screen, charge_power, is_charging)
        self._draw_fuel_near_current_tank(screen, tanks[current_turn])
        self._draw_ammo_chip(screen, current_bullet_type)

        status = "Space: hold to charge" if not is_charging else "Release Space to fire"
        if not aim_ready:
            status = "Arrow Up/Down to aim"
        hint = self.tiny_font.render(status, True, (29, 58, 98))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 76))
