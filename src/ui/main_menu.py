"""Stylized multi-screen main menu that simulates the provided mockups."""

from dataclasses import dataclass

import pygame

from src.utils.constants import HEIGHT, WIDTH


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


class MainMenu:
    """Menu flow: home -> mode -> difficulty -> level select."""

    def __init__(self) -> None:
        self.state = "home"
        self.title_font = pygame.font.Font(None, 98)
        self.big_font = pygame.font.Font(None, 78)
        self.btn_font = pygame.font.Font(None, 64)
        self.text_font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 28)

        self.selected_mode = "PVP"
        self.selected_difficulty = "Trung binh"

        self._home_buttons = self._build_home_buttons()
        self._mode_buttons = self._build_mode_buttons()
        self._difficulty_buttons = self._build_difficulty_buttons()
        self._level_buttons = self._build_level_buttons()

        self.back_button = MenuButton(
            label="< Back",
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
                label="Bat dau",
                rect=pygame.Rect(center_x - width // 2, start_y, width, height),
                fill_top=(167, 228, 83),
                fill_bottom=(86, 182, 58),
                border=(42, 126, 46),
                action="go_mode",
            ),
            MenuButton(
                label="Cai dat",
                rect=pygame.Rect(center_x - width // 2, start_y + (height + gap), width, height),
                fill_top=(108, 213, 252),
                fill_bottom=(45, 148, 229),
                border=(36, 102, 178),
                action="go_settings",
            ),
            MenuButton(
                label="Huong dan",
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
                subtitle="Doi dau 2 nguoi choi",
            ),
            MenuButton(
                label="PVE",
                rect=pygame.Rect(center_x - width // 2, 348, width, height),
                fill_top=(255, 239, 108),
                fill_bottom=(241, 196, 56),
                border=(171, 128, 30),
                action="mode_pve",
                subtitle="Dau voi may (AI)",
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
                label="De",
                rect=pygame.Rect(center_x - width // 2, start_y, width, height),
                fill_top=(170, 228, 89),
                fill_bottom=(84, 180, 56),
                border=(42, 126, 46),
                action="difficulty_easy",
            ),
            MenuButton(
                label="Trung binh",
                rect=pygame.Rect(center_x - width // 2, start_y + (height + gap), width, height),
                fill_top=(108, 212, 252),
                fill_bottom=(46, 150, 230),
                border=(36, 102, 178),
                action="difficulty_medium",
            ),
            MenuButton(
                label="Kho",
                rect=pygame.Rect(center_x - width // 2, start_y + 2 * (height + gap), width, height),
                fill_top=(255, 234, 112),
                fill_bottom=(244, 183, 58),
                border=(173, 122, 35),
                action="difficulty_hard",
            ),
        ]

    def _build_level_buttons(self) -> list[MenuButton]:
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
            label = str(idx + 1)
            action = f"level_{idx + 1}"
            if idx == 1:
                label = "LOCK"
                action = "locked"

            cards.append(
                MenuButton(
                    label=label,
                    rect=pygame.Rect(x, y, card_w, card_h),
                    fill_top=(140, 223, 251),
                    fill_bottom=(67, 170, 236),
                    border=(49, 116, 181),
                    action=action,
                    subtitle="Chua mo khoa" if idx == 1 else "San sang",
                )
            )

        return cards

    def _draw_background(self, screen: pygame.Surface) -> None:
        """Paint soft sky/grass gradients for a friendly cartoon look."""
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

        # Decorative soft hills and circles to mimic the sample scene depth.
        pygame.draw.ellipse(screen, (163, 226, 121), (-80, 505, 600, 270))
        pygame.draw.ellipse(screen, (142, 214, 100), (350, 500, 700, 270))
        pygame.draw.ellipse(screen, (126, 201, 88), (870, 515, 520, 250))

        for x, y, r in [(130, 134, 120), (1110, 140, 128), (640, 172, 170)]:
            pygame.draw.circle(screen, (235, 252, 255), (x, y), r, width=0)
            pygame.draw.circle(screen, (220, 246, 255), (x + 25, y + 12), int(r * 0.72), width=0)

    def _draw_button(self, screen: pygame.Surface, btn: MenuButton, active: bool = False) -> None:
        shadow = btn.rect.move(0, 6)
        pygame.draw.rect(screen, (40, 80, 55, 80), shadow, border_radius=28)

        half_h = btn.rect.height // 2
        top = pygame.Rect(btn.rect.left, btn.rect.top, btn.rect.width, half_h)
        bottom = pygame.Rect(btn.rect.left, btn.rect.top + half_h, btn.rect.width, btn.rect.height - half_h)

        pygame.draw.rect(screen, btn.fill_top, top, border_top_left_radius=28, border_top_right_radius=28)
        pygame.draw.rect(screen, btn.fill_bottom, bottom, border_bottom_left_radius=28, border_bottom_right_radius=28)

        border_color = (255, 255, 255) if active else btn.border
        border_width = 5 if active else 4
        pygame.draw.rect(screen, border_color, btn.rect, width=border_width, border_radius=28)

        gloss = pygame.Rect(btn.rect.left + 16, btn.rect.top + 10, btn.rect.width - 150, 20)
        pygame.draw.ellipse(screen, (255, 255, 255, 120), gloss)

        label = self.btn_font.render(btn.label, True, (41, 50, 61))
        label_rect = label.get_rect(center=(btn.rect.centerx, btn.rect.centery - 6))
        screen.blit(label, label_rect)

        if btn.subtitle:
            sub = self.small_font.render(btn.subtitle, True, (38, 56, 76))
            sub_rect = sub.get_rect(center=(btn.rect.centerx, btn.rect.centery + 28))
            screen.blit(sub, sub_rect)

    def _handle_click(self, pos: tuple[int, int]) -> str | None:
        if self.state != "home" and self.back_button.rect.collidepoint(pos):
            if self.state in ("mode", "settings", "guide"):
                self.state = "home"
            elif self.state == "difficulty":
                self.state = "mode"
            elif self.state == "levels":
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
                    self.state = "difficulty"
                    return None

        if self.state == "difficulty":
            for btn in self._difficulty_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.action == "difficulty_easy":
                        self.selected_difficulty = "De"
                    elif btn.action == "difficulty_medium":
                        self.selected_difficulty = "Trung binh"
                    else:
                        self.selected_difficulty = "Kho"
                    self.state = "levels"
                    return None

        if self.state == "levels":
            for btn in self._level_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.action == "locked":
                        return None
                    return "start"

        return None

    def handle_event(self, event: pygame.event.Event) -> str | None:
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

    def _draw_settings(self, screen: pygame.Surface) -> None:
        self._draw_top_title(screen, "Cai dat")
        panel = pygame.Rect(WIDTH // 2 - 390, 170, 780, 380)
        pygame.draw.rect(screen, (252, 252, 246), panel, border_radius=28)
        pygame.draw.rect(screen, (92, 130, 155), panel, width=4, border_radius=28)

        lines = [
            "Muc nay dang o che do mo phong giao dien.",
            "Ban co the them am thanh, nhac nen, do hoa va dieu khien.",
            "Phim ESC hoac nut Back de quay lai.",
        ]
        for idx, line in enumerate(lines):
            text = self.text_font.render(line, True, (36, 56, 72))
            screen.blit(text, (panel.left + 52, panel.top + 86 + idx * 54))

    def _draw_guide(self, screen: pygame.Surface) -> None:
        self._draw_top_title(screen, "Huong dan")
        panel = pygame.Rect(WIDTH // 2 - 420, 148, 840, 420)
        pygame.draw.rect(screen, (251, 250, 240), panel, border_radius=28)
        pygame.draw.rect(screen, (176, 133, 53), panel, width=4, border_radius=28)

        rules = [
            "1. Mui ten trai/phai de di chuyen xe tang (ton nhien lieu).",
            "2. Mui ten len/xuong (hoac W/S) de dieu chinh goc nong sung.",
            "3. Nhan giu Space de canh luc, tha Space de ban.",
            "4. Gio va loai dan ngau nhien thay doi moi luot.",
            "5. Ha HP doi thu ve 0 de chien thang.",
        ]
        for idx, rule in enumerate(rules):
            text = self.text_font.render(rule, True, (40, 54, 67))
            screen.blit(text, (panel.left + 38, panel.top + 62 + idx * 64))

    def draw(self, screen: pygame.Surface) -> None:
        self._draw_background(screen)

        if self.state == "home":
            for btn in self._home_buttons:
                self._draw_button(screen, btn)
            return

        self._draw_button(screen, self.back_button)

        if self.state == "mode":
            self._draw_top_title(screen, "Che do")
            for btn in self._mode_buttons:
                active = (btn.action == "mode_pvp" and self.selected_mode == "PVP") or (
                    btn.action == "mode_pve" and self.selected_mode == "PVE"
                )
                self._draw_button(screen, btn, active=active)
            return

        if self.state == "difficulty":
            self._draw_top_title(screen, "Do kho")
            for btn in self._difficulty_buttons:
                active = (
                    (btn.action == "difficulty_easy" and self.selected_difficulty == "De")
                    or (btn.action == "difficulty_medium" and self.selected_difficulty == "Trung binh")
                    or (btn.action == "difficulty_hard" and self.selected_difficulty == "Kho")
                )
                self._draw_button(screen, btn, active=active)
            return

        if self.state == "levels":
            self._draw_top_title(screen, "Man choi")
            mode_text = self.small_font.render(
                f"Mode: {self.selected_mode} | Do kho: {self.selected_difficulty}",
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
