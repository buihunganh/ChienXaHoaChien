"""Terrain surface with destructible pixels and collision mask."""

from pathlib import Path

import pygame

from src.utils.constants import GROUND_BROWN, GROUND_DARK, HEIGHT, TERRAIN_IMAGE_PATH, WIDTH


class Terrain:
    def __init__(self) -> None:
        self.surface = self._load_or_build_terrain()
        self.mask = pygame.mask.from_surface(self.surface)

    def _load_or_build_terrain(self) -> pygame.Surface:
        """Load terrain image if available, otherwise generate a default ground image."""
        if Path(TERRAIN_IMAGE_PATH).exists():
            loaded = pygame.image.load(str(TERRAIN_IMAGE_PATH)).convert_alpha()
            return pygame.transform.smoothscale(loaded, (WIDTH, HEIGHT))

        # Fallback image-like surface, still works exactly the same for masking and carving.
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        ground_y = int(HEIGHT * 0.70)
        for y in range(ground_y, HEIGHT):
            blend = (y - ground_y) / max(1, (HEIGHT - ground_y))
            color = (
                int(GROUND_BROWN[0] * (1.0 - blend) + GROUND_DARK[0] * blend),
                int(GROUND_BROWN[1] * (1.0 - blend) + GROUND_DARK[1] * blend),
                int(GROUND_BROWN[2] * (1.0 - blend) + GROUND_DARK[2] * blend),
                255,
            )
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))

        return surface

    def update_mask(self) -> None:
        self.mask = pygame.mask.from_surface(self.surface)

    def carve_crater(self, x: float, y: float, radius: int) -> None:
        """
        Carve a transparent circular hole using BLEND_RGBA_MIN.

        The crater overlay starts with alpha=255 (no change on MIN blend),
        then a circle alpha=0 is drawn to force destination alpha to zero.
        """
        crater = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        crater.fill((255, 255, 255, 255))
        pygame.draw.circle(crater, (0, 0, 0, 0), (radius, radius), radius)

        self.surface.blit(
            crater,
            (int(x - radius), int(y - radius)),
            special_flags=pygame.BLEND_RGBA_MIN,
        )
        self.update_mask()

    def is_solid_at(self, x: float, y: float) -> bool:
        ix = int(x)
        iy = int(y)
        if ix < 0 or ix >= WIDTH or iy < 0 or iy >= HEIGHT:
            return False
        return bool(self.mask.get_at((ix, iy)))

    def get_surface_y(self, x: float, start_y: int = 0) -> int | None:
        """Return first solid pixel y on a vertical scan line."""
        ix = int(x)
        if ix < 0 or ix >= WIDTH:
            return None

        top = max(0, start_y)
        for iy in range(top, HEIGHT):
            if self.mask.get_at((ix, iy)):
                return iy
        return None

    def draw(self, target: pygame.Surface) -> None:
        target.blit(self.surface, (0, 0))
