"""Bullet entity and bullet type definitions for per-turn random ammo."""

from dataclasses import dataclass

import pygame

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
    BulletType("Normal", damage=32, radius=4, explosion_radius=42, color=(30, 30, 30)),
    BulletType("High-Explosive", damage=24, radius=5, explosion_radius=58, color=(55, 45, 30)),
    BulletType("Armor-Pierce", damage=52, radius=3, explosion_radius=34, color=(25, 25, 25)),
)


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    alive: bool = True
    damage: int = BULLET_DAMAGE
    radius: int = BULLET_RADIUS
    explosion_radius: int = 44
    color: tuple[int, int, int] = (30, 30, 30)

    def update(self, dt: float, wind_acc: float) -> None:
        if not self.alive:
            return

        self.vx += wind_acc * dt
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surface: pygame.Surface) -> None:
        if self.alive:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
