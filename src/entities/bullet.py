"""Bullet entity and bullet type definitions for per-turn random ammo."""

from collections import deque
from dataclasses import dataclass
import math
from typing import ClassVar

import numpy as np
import pygame

from src.utils.asset_manager import assets
from src.utils.constants import BULLET_DAMAGE, BULLET_RADIUS, GRAVITY


@dataclass(frozen=True)
class BulletType:
    """Config package for one ammo type."""

    name: str
    damage: int
    radius: int
    explosion_radius: int
    color: tuple[int, int, int]


BULLET_TYPES: tuple[BulletType, ...] = (
    BulletType("Normal", damage=40, radius=4, explosion_radius=42, color=(30, 30, 30)),
    BulletType("High-Explosive", damage=32, radius=5, explosion_radius=58, color=(55, 45, 30)),
    BulletType("Armor-Pierce", damage=58, radius=3, explosion_radius=34, color=(25, 25, 25)),
)


@dataclass
class Bullet:
    _rocket_clean_cache: ClassVar[pygame.Surface | None] = None

    x: float
    y: float
    vx: float
    vy: float
    alive: bool = True
    damage: int = BULLET_DAMAGE
    radius: int = BULLET_RADIUS
    explosion_radius: int = 44
    color: tuple[int, int, int] = (30, 30, 30)

    def update(self, dt: float, wind_acc: float, gravity: float = GRAVITY) -> None:
        if not self.alive:
            return

        self.vx += wind_acc * dt
        self.vy += gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    @classmethod
    def eager_init(cls) -> None:
        """Pre-compute the clean rocket sprite during loading so gameplay
        never freezes on the first shot."""
        cls._get_clean_rocket()

    @classmethod
    def _get_clean_rocket(cls) -> pygame.Surface | None:
        """Build one transparent rocket sprite from source image and cache it.

        Uses numpy array operations instead of per-pixel get_at/set_at
        for dramatically faster processing (~100x speedup on 800x1201 images).
        """
        if cls._rocket_clean_cache is not None:
            return cls._rocket_clean_cache

        raw = assets.get_image("in_game/rocket")
        if raw is None:
            return None

        sprite = raw.copy().convert_alpha()
        w, h = sprite.get_size()

        # Fast numpy-based background removal
        # Get pixel arrays: rgb is (w, h, 3), alpha is (w, h)
        rgb = pygame.surfarray.pixels3d(sprite)  # shape (w, h, 3)
        alpha = pygame.surfarray.pixels_alpha(sprite)  # shape (w, h)

        # Detect "background-like" pixels: bright, near-gray, opaque
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        max_delta = np.maximum(np.abs(r.astype(np.int16) - g.astype(np.int16)),
                               np.abs(g.astype(np.int16) - b.astype(np.int16)))
        max_delta = np.maximum(max_delta,
                               np.abs(r.astype(np.int16) - b.astype(np.int16)))

        bg_mask = (alpha > 0) & (max_delta <= 8) & (r >= 225) & (g >= 225) & (b >= 225)

        # BFS flood fill from edges using numpy boolean array
        # Only remove background pixels reachable from the border
        reachable = np.zeros((w, h), dtype=bool)
        queue: deque[tuple[int, int]] = deque()

        # Seed from edges
        for x in range(w):
            if bg_mask[x, 0]:
                queue.append((x, 0))
                reachable[x, 0] = True
            if bg_mask[x, h - 1]:
                queue.append((x, h - 1))
                reachable[x, h - 1] = True
        for y in range(h):
            if bg_mask[0, y]:
                queue.append((0, y))
                reachable[0, y] = True
            if bg_mask[w - 1, y]:
                queue.append((w - 1, y))
                reachable[w - 1, y] = True

        # BFS — still pixel-level but checking bg_mask (numpy bool) is fast
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and bg_mask[nx, ny] and not reachable[nx, ny]:
                    reachable[nx, ny] = True
                    queue.append((nx, ny))

        # Zero alpha on reachable background pixels
        alpha[reachable] = 0

        # Release pixel array locks before further surface operations
        del rgb, alpha, r, g, b

        bounds = sprite.get_bounding_rect()
        if bounds.width > 0 and bounds.height > 0:
            sprite = sprite.subsurface(bounds).copy()

        cls._rocket_clean_cache = sprite
        return cls._rocket_clean_cache

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return

        rocket = self._get_clean_rocket()
        if rocket is None:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
            return

        # Make rocket slightly larger and easier to read in motion.
        sprite_h = max(18, int(self.radius * 8))
        scale = sprite_h / max(1, rocket.get_height())
        sprite_w = max(10, int(rocket.get_width() * scale))
        scaled = pygame.transform.smoothscale(rocket, (sprite_w, sprite_h))

        # Base sprite points upward; rotate so nose points along projectile motion.
        angle_deg = math.degrees(math.atan2(-self.vx, -self.vy))
        rotated = pygame.transform.rotozoom(scaled, angle_deg, 1.0)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))

        # Subtle dark outline so the rocket stays visible on bright sky/backgrounds.
        outline = pygame.mask.from_surface(rotated).to_surface(
            setcolor=(20, 20, 20, 110),
            unsetcolor=(0, 0, 0, 0),
        )
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surface.blit(outline, (rect.x + ox, rect.y + oy))

        surface.blit(rotated, rect)
