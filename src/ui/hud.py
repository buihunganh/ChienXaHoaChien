"""Stylized HUD inspired by Gunny-like battle interface."""

import pygame

from src.entities.bullet import BulletType
from src.entities.tank import Tank
from src.utils.constants import BLACK, HEIGHT, SHOT_POWER_MAX, SHOT_POWER_MIN, WHITE, WIDTH


class HUD:
    def __init__(self) -> None:
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        self.tiny_font = pygame.font.Font(None, 24)

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

    def _draw_top_health(self, screen: pygame.Surface, left_tank: Tank, right_tank: Tank) -> None:
        left_label = self.font.render("Name", True, WHITE)
        right_label = self.font.render("Name", True, WHITE)

        screen.blit(left_label, (210, 18))
        screen.blit(right_label, (WIDTH - 318, 18))

        left_rect = pygame.Rect(200, 54, 340, 56)
        right_rect = pygame.Rect(WIDTH - 540, 54, 340, 56)

        self._draw_rounded_bar(screen, left_rect, left_tank.hp / 100.0, (77, 226, 62), (47, 123, 178))
        self._draw_rounded_bar(screen, right_rect, right_tank.hp / 100.0, (231, 66, 66), (186, 67, 86))

    def _draw_vs_shield(self, screen: pygame.Surface) -> None:
        center = (WIDTH // 2, 70)
        shield = pygame.Surface((130, 130), pygame.SRCALPHA)
        points = [(65, 10), (114, 25), (104, 94), (65, 120), (26, 94), (16, 25)]
        pygame.draw.polygon(shield, (52, 124, 210), points)
        pygame.draw.polygon(shield, (226, 62, 75), [(65, 10), (114, 25), (104, 94), (65, 120)])
        pygame.draw.polygon(shield, (225, 236, 247), points, width=5)

        text = self.font.render("VS", True, WHITE)
        shield.blit(text, text.get_rect(center=(66, 62)))
        screen.blit(shield, (center[0] - 65, center[1] - 56))

    def _draw_wind_center(self, screen: pygame.Surface, wind: float) -> None:
        text = self.font.render("Wind", True, (46, 76, 128))
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 142))

        ratio = max(-1.0, min(1.0, wind / 85.0))
        arrow_len = int(95 * abs(ratio))
        direction = 1 if wind >= 0 else -1

        start = (WIDTH // 2, 186)
        end = (WIDTH // 2 + direction * max(26, arrow_len), 186)
        color = (47, 121, 224)
        pygame.draw.line(screen, color, start, end, 6)
        wing_a = (end[0] - 14 * direction, end[1] - 10)
        wing_b = (end[0] - 14 * direction, end[1] + 10)
        pygame.draw.polygon(screen, color, [end, wing_a, wing_b])

        wind_value = self.font.render(f"{abs(wind) / 100:.1f}".replace(".", ","), True, (30, 62, 110))
        screen.blit(wind_value, (WIDTH // 2 - wind_value.get_width() // 2, 202))

    def _draw_side_controls(self, screen: pygame.Surface) -> None:
        x = 62
        for idx, color in enumerate([(54, 141, 220), (77, 176, 233), (56, 154, 223)]):
            y = 64 + idx * 92
            pygame.draw.circle(screen, color, (x, y), 31)
            pygame.draw.circle(screen, (31, 90, 144), (x, y), 31, width=3)

        # Minimal icon marks
        pygame.draw.line(screen, WHITE, (44, 64), (80, 64), 4)
        pygame.draw.line(screen, WHITE, (44, 54), (80, 54), 4)
        pygame.draw.line(screen, WHITE, (44, 74), (80, 74), 4)

        pygame.draw.circle(screen, WHITE, (62, 156), 12, width=3)
        pygame.draw.rect(screen, WHITE, (74, 165, 8, 8), border_radius=2)

        pygame.draw.polygon(screen, (255, 208, 78), [(52, 246), (78, 258), (52, 270)])
        pygame.draw.circle(screen, WHITE, (79, 246), 4)

    def _draw_power_column(self, screen: pygame.Surface, charge_power: float, is_charging: bool) -> None:
        col_rect = pygame.Rect(32, 282, 44, 248)
        pygame.draw.rect(screen, (30, 75, 138), col_rect.inflate(10, 10), border_radius=16)
        pygame.draw.rect(screen, (24, 61, 116), col_rect, border_radius=12)

        ratio = max(0.0, min(1.0, (charge_power - SHOT_POWER_MIN) / (SHOT_POWER_MAX - SHOT_POWER_MIN)))
        fill_h = int(col_rect.height * ratio)
        fill_rect = pygame.Rect(col_rect.left + 5, col_rect.bottom - 5 - fill_h, col_rect.width - 10, fill_h)

        if fill_h > 0:
            # Fake gradient using a few slices from green to red.
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
        label = self.font.render("Power", True, (70, 47, 30))
        screen.blit(label, (14, 542))

        state = "Charging" if is_charging else "Ready"
        state_txt = self.tiny_font.render(state, True, (35, 63, 100))
        screen.blit(state_txt, (18, 570))

    def _draw_fuel_near_current_tank(self, screen: pygame.Surface, tank: Tank) -> None:
        x = int(tank.x) - 64
        y = int(tank.y) - 126

        text = self.font.render("Fuel", True, (82, 50, 32))
        screen.blit(text, (x + 24, y - 18))

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

    def _draw_ammo_chip(self, screen: pygame.Surface, bullet_type: BulletType) -> None:
        chip = pygame.Rect(WIDTH // 2 - 170, HEIGHT - 52, 340, 38)
        pygame.draw.rect(screen, (247, 248, 239), chip, border_radius=12)
        pygame.draw.rect(screen, (83, 125, 171), chip, width=2, border_radius=12)

        txt = self.small_font.render(
            f"Ammo: {bullet_type.name} | Dmg {bullet_type.damage}",
            True,
            (35, 54, 86),
        )
        screen.blit(txt, (chip.centerx - txt.get_width() // 2, chip.top + 7))

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
