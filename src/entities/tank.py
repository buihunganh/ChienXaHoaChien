"""Tank entity with movement physics, aiming, and pixel-accurate collision shape."""

from dataclasses import dataclass
import math

import pygame

from src.core.terrain import Terrain
from src.utils.constants import (
    FUEL_COST_PER_PIXEL,
    GRAVITY,
    MAX_FUEL,
    TANK_BARREL_LENGTH,
    TANK_BODY_HEIGHT,
    TANK_BODY_WIDTH,
    TANK_MAX_DROP,
    TANK_MAX_HP,
    TANK_MOVE_SPEED,
    TANK_STEP_UP,
    TANK_TRACK_WIDTH,
    TANK_TURRET_RADIUS,
)


@dataclass
class Tank:
    x: float
    y: float
    color: tuple[int, int, int]
    hp: int = TANK_MAX_HP
    fuel: float = MAX_FUEL

    def __post_init__(self) -> None:
        self.vy = 0.0
        self.slope_angle_deg = 0.0
        self.aim_angle_deg = -45.0

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def set_aim_towards(self, target_pos: tuple[int, int]) -> None:
        """Rotate cannon toward cursor position in world space."""
        turret_x, turret_y = self.get_turret_base_pos()
        dx = target_pos[0] - turret_x
        dy = target_pos[1] - turret_y
        if dx == 0 and dy == 0:
            return
        self.aim_angle_deg = math.degrees(math.atan2(-dy, dx))

    def move_horizontal(self, direction: float, dt: float, terrain: Terrain) -> None:
        """
        Move along X with snap-to-ground and step-up handling.

        The step check allows a small vertical climb so the tank slides over
        crater edges instead of getting stuck on a single pixel step.
        """
        if not self.is_alive or self.fuel <= 0:
            return

        dx = direction * TANK_MOVE_SPEED * dt
        if abs(dx) < 1e-5:
            return

        current_ground = terrain.get_surface_y(self.x)
        candidate_x = max(8.0, min(self.x + dx, 1272.0))
        candidate_ground = terrain.get_surface_y(candidate_x)

        if current_ground is None or candidate_ground is None:
            return

        climb = candidate_ground - current_ground
        if climb > TANK_STEP_UP:
            return
        if climb < -TANK_MAX_DROP:
            return

        self.x = candidate_x
        self.fuel = max(0.0, self.fuel - abs(dx) * FUEL_COST_PER_PIXEL)
        self.snap_to_ground(terrain)

    def snap_to_ground(self, terrain: Terrain) -> None:
        """Stick tank to terrain and compute body slope with atan2."""
        center_ground = terrain.get_surface_y(self.x)
        if center_ground is None:
            return

        self.y = float(center_ground)
        self.vy = 0.0

        half_track = TANK_TRACK_WIDTH * 0.45
        left_ground = terrain.get_surface_y(self.x - half_track)
        right_ground = terrain.get_surface_y(self.x + half_track)

        if left_ground is None or right_ground is None:
            self.slope_angle_deg = 0.0
            return

        self.slope_angle_deg = math.degrees(
            math.atan2((right_ground - left_ground), (half_track * 2.0))
        )

    def apply_gravity(self, dt: float, terrain: Terrain) -> None:
        """Free-fall when not supported by terrain directly under the tracks."""
        if not self.is_alive:
            return

        # Probe below the track center. If no solid pixel right under it, tank falls.
        if not terrain.is_solid_at(self.x, self.y + 2):
            self.vy += GRAVITY * dt
            self.y += self.vy * dt

            landed = terrain.get_surface_y(self.x, int(max(0, self.y - 10)))
            if landed is not None and self.y >= landed:
                self.y = float(landed)
                self.vy = 0.0
        else:
            self.snap_to_ground(terrain)

    def take_damage(self, damage: int) -> None:
        self.hp = max(0, self.hp - damage)

    def get_turret_base_pos(self) -> tuple[float, float]:
        return (self.x, self.y - TANK_BODY_HEIGHT - 4)

    def get_barrel_tip(self) -> tuple[float, float]:
        base_x, base_y = self.get_turret_base_pos()
        rad = math.radians(self.aim_angle_deg)
        return (
            base_x + math.cos(rad) * TANK_BARREL_LENGTH,
            base_y - math.sin(rad) * TANK_BARREL_LENGTH,
        )

    def _build_sprite(self) -> tuple[pygame.Surface, pygame.Rect]:
        """Build and rotate tank sprite so mask collision matches what player sees."""
        sprite_w = 120
        sprite_h = 80
        sprite = pygame.Surface((sprite_w, sprite_h), pygame.SRCALPHA)
        cx = sprite_w // 2
        cy = sprite_h // 2

        track_rect = pygame.Rect(0, 0, TANK_TRACK_WIDTH, 10)
        track_rect.center = (cx, cy + 12)
        body_rect = pygame.Rect(0, 0, TANK_BODY_WIDTH, TANK_BODY_HEIGHT)
        body_rect.center = (cx, cy)

        pygame.draw.rect(sprite, (35, 35, 35), track_rect, border_radius=5)
        pygame.draw.rect(sprite, self.color, body_rect, border_radius=6)
        pygame.draw.circle(sprite, self.color, (cx, cy - 8), TANK_TURRET_RADIUS)

        # Cannon is drawn in world-space orientation; body stays terrain-aligned.
        rotated = pygame.transform.rotozoom(sprite, -self.slope_angle_deg, 1.0)
        rect = rotated.get_rect(center=(int(self.x), int(self.y - 18)))
        return rotated, rect

    def get_mask_and_rect(self) -> tuple[pygame.Mask, pygame.Rect]:
        sprite, rect = self._build_sprite()
        return pygame.mask.from_surface(sprite), rect

    def draw(self, surface: pygame.Surface) -> None:
        sprite, rect = self._build_sprite()
        surface.blit(sprite, rect)

        turret_x, turret_y = self.get_turret_base_pos()
        tip_x, tip_y = self.get_barrel_tip()
        pygame.draw.line(
            surface,
            (25, 25, 25),
            (int(turret_x), int(turret_y)),
            (int(tip_x), int(tip_y)),
            5,
        )
