import math
import random
from pathlib import Path
import pygame
from src.core.map_config import MapConfig
from src.utils.asset_manager import assets
from src.utils.constants import HEIGHT, WIDTH

class Terrain:
    def __init__(self, map_config: MapConfig | None = None) -> None:
        self.map_config = map_config
        self.surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.decoration_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._load_or_build_terrain()
        self.mask = pygame.mask.from_surface(self.surface)

    def _load_or_build_terrain(self) -> None:
        """Generate terrain and decorations based on map configuration."""
        self.surface.fill((0, 0, 0, 0))
        self.decoration_surface.fill((0, 0, 0, 0))

        if self.map_config and self.map_config.terrain_image:
            image_path = Path(self.map_config.terrain_image)
            if image_path.exists():
                loaded = pygame.image.load(str(image_path)).convert_alpha()
                self.surface.blit(pygame.transform.smoothscale(loaded, (WIDTH, HEIGHT)), (0, 0))
                return

        map_id = self.map_config.id if self.map_config else 1

        if map_id == 1:
            self._build_plains_terrain(self.surface, self.decoration_surface)
        elif map_id == 2:
            self._build_sea_terrain(self.surface)
        elif map_id == 3:
            self._build_space_terrain(self.surface)
        else:
            self._build_plains_terrain(self.surface, self.decoration_surface)

    def _build_plains_terrain(self, surface: pygame.Surface, decoration: pygame.Surface) -> None:
        """Plains: Straight flat ground with decorative grass."""
        ground_y = int(HEIGHT * 0.75)
        
        # Soil base (flat rect) - earthy deep brown
        pygame.draw.rect(surface, (88, 62, 45), (0, ground_y, WIDTH, HEIGHT - ground_y))
        
        # Decorative grass patches (scaled down and non-collidable)
        grass1 = assets.get_image("icons/grass1")
        grass2 = assets.get_image("icons/grass2")
        
        if grass1 and grass2:
            x = -10
            while x < WIDTH:
                img = random.choice([grass1, grass2])
                # Scale down even more as requested (very small decorations)
                scale = random.uniform(0.12, 0.18)
                w, h = img.get_size()
                sw, sh = int(w * scale), int(h * scale)
                scaled = pygame.transform.smoothscale(img, (sw, sh))
                
                # Blit to decoration surface (no collision)
                # Randomize x a bit more for organic look
                offset_x = random.randint(-5, 20)
                offset_y = random.randint(-3, 3)
                decoration.blit(scaled, (x + offset_x, ground_y - sh + 2 + offset_y))
                x += sw + 10 # More gap
        else:
            pygame.draw.rect(decoration, (80, 160, 60), (0, ground_y - 6, WIDTH, 6))

    def _build_sea_terrain(self, surface: pygame.Surface) -> None:
        """Sea: Pirate ship foundation."""
        hull_color = (85, 55, 30)
        deck_color = (120, 85, 50)
        
        center_x = WIDTH // 2
        ground_y = int(HEIGHT * 0.65)
        
        # Hull shape
        hull_points = [
            (150, ground_y),           # Top left
            (WIDTH - 150, ground_y),   # Top right
            (WIDTH - 250, HEIGHT - 20),# Bottom right
            (250, HEIGHT - 20),        # Bottom left
        ]
        pygame.draw.polygon(surface, hull_color, hull_points)
        
        # Deck planks
        pygame.draw.rect(surface, deck_color, (150, ground_y, WIDTH - 300, 40))
        
        # Add some "plank" detail lines
        for x in range(160, WIDTH - 160, 40):
            pygame.draw.line(surface, (60, 40, 20), (x, ground_y), (x, ground_y + 40), 2)
            
        # Optional: Mast bases (non-collidable decoration or collidable obstacles?)
        # For simplicity, just make them part of the terrain
        pygame.draw.rect(surface, hull_color, (center_x - 10, ground_y - 120, 20, 120))
        pygame.draw.rect(surface, hull_color, (center_x - 300, ground_y - 80, 20, 80))
        pygame.draw.rect(surface, hull_color, (center_x + 280, ground_y - 80, 20, 80))

    def _build_space_terrain(self, surface: pygame.Surface) -> None:
        """Space: Uneven, jagged terrain matching background color."""
        # A dark, space-rock color (bluish-gray/purple)
        rock_color = (45, 45, 65)
        
        points = []
        points.append((0, HEIGHT))
        
        base_y = int(HEIGHT * 0.75)
        
        for x in range(0, WIDTH + 10, 10):
            # Sum of multiple sines for "jagged" look
            jagged = (
                math.sin(x * 0.02) * 50 +
                math.sin(x * 0.05) * 20 +
                math.sin(x * 0.1) * 10 +
                random.uniform(-5, 5) # Micro-jaggedness
            )
            points.append((x, int(base_y + jagged)))
            
        points.append((WIDTH, HEIGHT))
        pygame.draw.polygon(surface, rock_color, points)
        
        # Highlight top edge
        pygame.draw.lines(surface, (80, 80, 110), False, points[1:-1], 3)

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
        target.blit(self.decoration_surface, (0, 0))
