"""Game flow manager for turns, aiming, charging, and combat resolution."""

import math
import random

import pygame

from src.core.terrain import Terrain
from src.entities.bullet import BULLET_TYPES, Bullet, BulletType
from src.entities.tank import Tank
from src.ui.hud import HUD
from src.ui.main_menu import MainMenu
from src.utils.constants import (
    EXPLOSION_DAMAGE_RADIUS,
    GREEN,
    HEIGHT,
    RED,
    SHOT_CHARGE_RATE,
    SHOT_POWER_MAX,
    SHOT_POWER_MIN,
    SKY_BLUE,
    WIND_MAX,
    WIND_MIN,
    WIDTH,
)


class GameManager:
    """High-level game state coordinator."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.state = "menu"
        self.menu = MainMenu()
        self.hud = HUD()
        self.terrain = Terrain()

        self.wind = random.uniform(WIND_MIN, WIND_MAX)
        self.turn_index = 0
        self.winner_text = ""
        self.winner_color = (20, 20, 20)

        self.tanks = [
            Tank(220.0, 120.0, GREEN),
            Tank(WIDTH - 220.0, 120.0, RED),
        ]
        # Player 1 starts aiming to the right/up, Player 2 to the left/up.
        self.tanks[0].aim_angle_deg = 45.0
        self.tanks[1].aim_angle_deg = 135.0
        for tank in self.tanks:
            tank.snap_to_ground(self.terrain)

        self.active_bullet: Bullet | None = None
        self.current_bullet_type: BulletType = random.choice(BULLET_TYPES)

        self.is_dragging = False
        self.drag_start: tuple[float, float] | None = None
        self.drag_current: tuple[float, float] | None = None

        self.aim_ready = False
        self.aim_vector = (1.0, -0.2)
        self.is_charging = False
        self.charge_power = SHOT_POWER_MIN
        self.charge_direction = 1.0

    def _reset_turn_inputs(self) -> None:
        self.is_dragging = False
        self.drag_start = None
        self.drag_current = None
        self.aim_ready = False
        self.is_charging = False
        self.charge_power = SHOT_POWER_MIN
        self.charge_direction = 1.0

    def _next_turn(self) -> None:
        self.turn_index = (self.turn_index + 1) % len(self.tanks)
        self.wind = random.uniform(WIND_MIN, WIND_MAX)
        self.current_bullet_type = random.choice(BULLET_TYPES)
        self._reset_turn_inputs()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "menu":
            action = self.menu.handle_event(event)
            if action == "start":
                self.state = "playing"
            return

        if self.state == "game_over" and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.__init__(self.screen)
            self.state = "playing"
            return

        if self.state != "playing":
            return

        current = self.tanks[self.turn_index]
        if not current.is_alive:
            self._next_turn()
            return

        if self.active_bullet is not None:
            return

        if event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self.drag_current = event.pos

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.is_charging:
            turret_pos = current.get_turret_base_pos()
            if math.dist(turret_pos, event.pos) <= 88:
                self.is_dragging = True
                self.drag_start = turret_pos
                self.drag_current = event.pos

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_dragging:
            self.is_dragging = False
            if self.drag_start is not None and self.drag_current is not None:
                self._commit_aim_from_drag(current, self.drag_start, self.drag_current)
            self.drag_start = None
            self.drag_current = None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not self.is_charging:
            # Hold Space to let power oscillate between min and max.
            self.is_charging = True
            self.charge_power = SHOT_POWER_MIN
            self.charge_direction = 1.0

        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE and self.is_charging:
            self.is_charging = False
            self._fire_charged_shot(current)

    def _commit_aim_from_drag(
        self,
        tank: Tank,
        drag_start: tuple[float, float],
        drag_end: tuple[float, float],
    ) -> None:
        """Convert drag vector into a locked shot direction."""
        pull_x = drag_start[0] - drag_end[0]
        pull_y = drag_start[1] - drag_end[1]
        length = math.hypot(pull_x, pull_y)
        if length < 16.0:
            self.aim_ready = False
            return

        dir_x = pull_x / length
        dir_y = pull_y / length
        self.aim_vector = (dir_x, dir_y)
        self.aim_ready = True

        turret_x, turret_y = tank.get_turret_base_pos()
        tank.set_aim_towards((int(turret_x + dir_x * 100), int(turret_y + dir_y * 100)))

    def _fire_charged_shot(self, tank: Tank) -> None:
        if self.aim_ready:
            dir_x, dir_y = self.aim_vector
        else:
            # Default Gunny-style behavior: fire in current cannon/mouse direction.
            turret_x, turret_y = tank.get_turret_base_pos()
            tip_x, tip_y = tank.get_barrel_tip()
            vec_x = tip_x - turret_x
            vec_y = tip_y - turret_y
            length = math.hypot(vec_x, vec_y)
            if length <= 1e-5:
                return
            dir_x = vec_x / length
            dir_y = vec_y / length

        muzzle_x, muzzle_y = tank.get_barrel_tip()
        self.active_bullet = Bullet(
            x=muzzle_x,
            y=muzzle_y,
            vx=dir_x * self.charge_power,
            vy=dir_y * self.charge_power,
            damage=self.current_bullet_type.damage,
            radius=self.current_bullet_type.radius,
            explosion_radius=self.current_bullet_type.explosion_radius,
            color=self.current_bullet_type.color,
        )
        self.aim_ready = False

    def update(self, dt: float) -> None:
        if self.state != "playing":
            return

        current = self.tanks[self.turn_index]

        for tank in self.tanks:
            tank.apply_gravity(dt, self.terrain)

        if self.active_bullet is None and current.is_alive and not self.is_charging:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                current.move_horizontal(-1.0, dt, self.terrain)
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                current.move_horizontal(1.0, dt, self.terrain)

            # Gunny-like cannon control: Up/Down (or W/S) changes barrel angle.
            aim_speed = 95.0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                delta = aim_speed * dt
                if self.turn_index == 0:
                    current.aim_angle_deg = min(170.0, current.aim_angle_deg + delta)
                else:
                    current.aim_angle_deg = max(10.0, current.aim_angle_deg - delta)

            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                delta = aim_speed * dt
                if self.turn_index == 0:
                    current.aim_angle_deg = max(10.0, current.aim_angle_deg - delta)
                else:
                    current.aim_angle_deg = min(170.0, current.aim_angle_deg + delta)

        if self.is_charging:
            self.charge_power += self.charge_direction * SHOT_CHARGE_RATE * dt
            if self.charge_power >= SHOT_POWER_MAX:
                self.charge_power = SHOT_POWER_MAX
                self.charge_direction = -1.0
            elif self.charge_power <= SHOT_POWER_MIN:
                self.charge_power = SHOT_POWER_MIN
                self.charge_direction = 1.0

        if self.active_bullet is None:
            self._check_game_over()
            return

        self.active_bullet.update(dt, self.wind)

        if self.active_bullet.y > HEIGHT or self.active_bullet.x < 0 or self.active_bullet.x > WIDTH:
            self.active_bullet = None
            self._next_turn()
            return

        if self.terrain.is_solid_at(self.active_bullet.x, self.active_bullet.y):
            self._explode(self.active_bullet)
            return

        target_idx = (self.turn_index + 1) % len(self.tanks)
        target = self.tanks[target_idx]
        if target.is_alive and self._bullet_hits_tank(self.active_bullet, target):
            self._explode(self.active_bullet)
            return

    def _bullet_hits_tank(self, bullet: Bullet, tank: Tank) -> bool:
        mask, rect = tank.get_mask_and_rect()
        local_x = int(bullet.x - rect.left)
        local_y = int(bullet.y - rect.top)

        if local_x < 0 or local_y < 0 or local_x >= rect.width or local_y >= rect.height:
            return False

        return bool(mask.get_at((local_x, local_y)))

    def _explode(self, bullet: Bullet) -> None:
        self.terrain.carve_crater(bullet.x, bullet.y, bullet.explosion_radius)
        self._apply_explosion_damage(bullet.x, bullet.y, bullet)
        self.active_bullet = None
        self._next_turn()
        self._check_game_over()

    def _apply_explosion_damage(self, x: float, y: float, bullet: Bullet) -> None:
        for tank in self.tanks:
            if not tank.is_alive:
                continue

            blast_radius = max(EXPLOSION_DAMAGE_RADIUS, bullet.explosion_radius * 1.6)
            distance = math.dist((x, y), (tank.x, tank.y))
            if distance <= blast_radius:
                ratio = 1.0 - (distance / blast_radius)
                damage = int(max(1, bullet.damage * (0.35 + 0.65 * ratio)))
                tank.take_damage(damage)

    def _check_game_over(self) -> None:
        alive = [idx for idx, tank in enumerate(self.tanks) if tank.is_alive]
        if len(alive) == 1:
            winner = alive[0] + 1
            self.state = "game_over"
            self.winner_text = f"Player {winner} wins"
            self.winner_color = self.tanks[alive[0]].color
        elif len(alive) == 0:
            self.state = "game_over"
            self.winner_text = "Draw"
            self.winner_color = (40, 40, 40)

    def _draw_world_decorations(self) -> None:
        """Draw lightweight scenery details so gameplay looks closer to the reference UI."""
        # Clouds
        for cx, cy, w, h in [(280, 150, 150, 78), (1010, 170, 180, 86), (520, 200, 210, 92)]:
            pygame.draw.ellipse(self.screen, (226, 247, 255), (cx - w // 2, cy - h // 2, w, h))
            pygame.draw.ellipse(self.screen, (237, 252, 255), (cx - w // 3, cy - h // 2 - 16, w // 2, h // 2))

        # Sun
        sun_center = (WIDTH - 210, 184)
        pygame.draw.circle(self.screen, (253, 224, 88), sun_center, 38)
        pygame.draw.circle(self.screen, (247, 197, 72), sun_center, 38, width=3)

        for k in range(12):
            angle = k * 30
            vec = pygame.math.Vector2(1, 0).rotate(angle)
            p1 = (sun_center[0] + int(vec.x * 48), sun_center[1] + int(vec.y * 48))
            p2 = (sun_center[0] + int(vec.x * 58), sun_center[1] + int(vec.y * 58))
            pygame.draw.line(self.screen, (255, 221, 99), p1, p2, 4)

        # Small trees and bunker mounds
        for tx, ty in [(150, 310), (1090, 324), (980, 300)]:
            pygame.draw.rect(self.screen, (99, 82, 58), (tx - 5, ty - 14, 10, 16), border_radius=4)
            pygame.draw.circle(self.screen, (109, 190, 83), (tx, ty - 28), 22)
            pygame.draw.circle(self.screen, (97, 176, 72), (tx - 14, ty - 26), 16)
            pygame.draw.circle(self.screen, (97, 176, 72), (tx + 14, ty - 26), 16)

    def render(self) -> None:
        self.screen.fill(SKY_BLUE)

        if self.state == "menu":
            self.menu.draw(self.screen)
            return

        self._draw_world_decorations()

        self.terrain.draw(self.screen)

        for tank in self.tanks:
            tank.draw(self.screen)

        if self.active_bullet is not None:
            self.active_bullet.draw(self.screen)

        if self.is_dragging and self.drag_start is not None and self.drag_current is not None:
            pygame.draw.line(
                self.screen,
                (28, 28, 28),
                (int(self.drag_start[0]), int(self.drag_start[1])),
                (int(self.drag_current[0]), int(self.drag_current[1])),
                2,
            )
            pygame.draw.circle(
                self.screen,
                (252, 246, 235),
                (int(self.drag_start[0]), int(self.drag_start[1])),
                7,
                width=2,
            )

        self.hud.draw(
            self.screen,
            self.tanks,
            self.turn_index,
            self.wind,
            self.current_bullet_type,
            self.charge_power,
            self.is_charging,
            self.aim_ready,
        )

        if self.state == "game_over":
            font = pygame.font.Font(None, 64)
            text = font.render(self.winner_text + " - Press R to restart", True, self.winner_color)
            rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text, rect)
