"""GameOverOverlay — animated victory / lose popup.

Animation sequence:
  1. Fade-in: dark semi-transparent overlay fades in over ~0.4 s
  2. Bounce-in: popup image drops from above centre, overshoots, settles (~0.5 s)
  3. Idle: popup sits centred, player reads result
  4. Press R to restart hint appears after 1.0 s

The overlay is driven by wall-clock time passed in via update(dt).
"""

from __future__ import annotations

import math

import pygame

from src.utils.asset_manager import assets
from src.utils.constants import FONT_SIZE_NORMAL, FONT_SIZE_SMALL, HEIGHT, WIDTH


# Popup target size (width; height scales proportionally)
_POPUP_W = 520

# Animation timings (seconds)
_FADE_DURATION   = 0.40   # how long the dark overlay takes to reach full opacity
_BOUNCE_START    = 0.15   # when the popup starts dropping in
_BOUNCE_DURATION = 0.55   # how long the bounce-in takes
_HINT_APPEAR     = 1.20   # when the restart hint fades in

# Max overlay darkness (0–255)
_OVERLAY_ALPHA = 175


def _ease_out_bounce(t: float) -> float:
    """Standard ease-out bounce easing — t in [0, 1]."""
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


class GameOverOverlay:
    """Stateful animated overlay — create once when game_over is triggered."""

    def __init__(self, winner_idx: int | None) -> None:
        """
        winner_idx: 0 for player 1 wins, 1 for player 2 wins, None for draw.
        The overlay chooses victory/lose image based on convention:
          player 1 (idx 0) = victory image
          player 2 (idx 1) / draw = lose image  (in PVP, both signs shown briefly)
        For PVE the caller can pass idx 0 = human won, idx None/1 = human lost.

        In practice, GameManager always calls this with winner_idx from tanks list.
        """
        self._elapsed = 0.0
        self._winner_idx = winner_idx  # None = draw

        # Choose which popup to show
        if winner_idx == 0:
            self._img_key = "icons/victory"
        elif winner_idx is None:
            self._img_key = "icons/lose"   # draw → lose popup (neutral)
        else:
            self._img_key = "icons/lose"

        # Load and scale the popup image
        raw = assets.get_image(self._img_key)
        if raw is not None:
            aspect = raw.get_height() / raw.get_width()
            h = int(_POPUP_W * aspect)
            self._popup = pygame.transform.smoothscale(raw, (_POPUP_W, h))
        else:
            self._popup = None

        # Flag: Lose JPG has a white background we hide behind a dark card
        self._needs_card = (self._img_key == "icons/lose")

        self.font       = assets.get_font(FONT_SIZE_NORMAL)
        self.small_font = assets.get_font(FONT_SIZE_SMALL)

        # Pre-compute target rect (centred, slightly above true centre)
        if self._popup:
            pw, ph = self._popup.get_size()
        else:
            pw, ph = _POPUP_W, 200
        self._target_rect = pygame.Rect(
            WIDTH // 2 - pw // 2,
            HEIGHT // 2 - ph // 2 - 30,
            pw, ph,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self._elapsed += dt

    def draw(self, screen: pygame.Surface) -> None:
        t = self._elapsed

        # 1. Dark overlay — fade in
        fade_alpha = int(_OVERLAY_ALPHA * min(1.0, t / _FADE_DURATION))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 10, fade_alpha))
        screen.blit(overlay, (0, 0))

        # 2. Popup bounce-in
        bounce_t = t - _BOUNCE_START
        if bounce_t > 0 and self._popup is not None:
            progress = min(1.0, bounce_t / _BOUNCE_DURATION)
            eased    = _ease_out_bounce(progress)

            # Popup starts from above the screen, drops to target
            start_y  = -self._target_rect.height - 20
            target_y = self._target_rect.top
            current_y = int(start_y + (target_y - start_y) * eased)

            dest_rect = pygame.Rect(self._target_rect.left, current_y,
                                    self._target_rect.width, self._target_rect.height)

            # Subtle scale pulse during bounce (1.0 → 1.08 → 1.0)
            scale = 1.0 + 0.08 * math.sin(progress * math.pi)
            if abs(scale - 1.0) > 0.005:
                sw = int(self._target_rect.width * scale)
                sh = int(self._target_rect.height * scale)
                img_to_blit = pygame.transform.smoothscale(self._popup, (sw, sh))
                blit_rect   = img_to_blit.get_rect(center=dest_rect.center)
            else:
                img_to_blit = self._popup
                blit_rect   = dest_rect

            # For JPG lose sign: draw a dark rounded card first to hide white background
            if self._needs_card:
                card_padding = 24
                card_rect = blit_rect.inflate(card_padding * 2, card_padding)
                card_surf = pygame.Surface(card_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(card_surf, (22, 30, 60, 230),
                                 card_surf.get_rect(), border_radius=24)
                pygame.draw.rect(card_surf, (60, 90, 160, 200),
                                 card_surf.get_rect(), width=3, border_radius=24)
                screen.blit(card_surf, card_rect.topleft)

            screen.blit(img_to_blit, blit_rect)

        # 3. Winner text beneath popup
        if t > _BOUNCE_START + _BOUNCE_DURATION * 0.6:
            alpha = int(255 * min(1.0, (t - (_BOUNCE_START + _BOUNCE_DURATION * 0.5)) / 0.25))
            alpha = max(0, min(255, alpha))
            if self._winner_idx == 0:
                msg = "Player 1 wins!"
                color = (255, 220, 50)
            elif self._winner_idx is None:
                msg = "Draw!"
                color = (200, 200, 220)
            else:
                msg = "Player 2 wins!"
                color = (255, 80, 80)
            txt = self.font.render(msg, True, color)
            txt.set_alpha(alpha)
            screen.blit(txt, txt.get_rect(
                centerx=WIDTH // 2,
                top=self._target_rect.bottom + 18,
            ))

        # 4. Restart hint
        if t > _HINT_APPEAR:
            hint_alpha = int(255 * min(1.0, (t - _HINT_APPEAR) / 0.30))
            hint = self.small_font.render("Press R to play again", True, (200, 220, 255))
            hint.set_alpha(hint_alpha)
            screen.blit(hint, hint.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 28))
