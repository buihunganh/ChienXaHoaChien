"""Game flow manager for turns, aiming, charging, and combat resolution."""

import math
import random

import pygame

from src.core.terrain import Terrain
from src.entities.bullet import BULLET_TYPES, Bullet, BulletType
from src.entities.tank import Tank
from src.ui.game_over_overlay import GameOverOverlay
from src.ui.hud import HUD
from src.ui.main_menu import MainMenu
from src.ui.pause_menu import PauseMenu
from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import (
    EXPLOSION_DAMAGE_RADIUS,
    FONT_SIZE_TITLE,
    GRAVITY,
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
        self.pause_menu = PauseMenu()
        self.paused = False
        self._game_over_overlay: GameOverOverlay | None = None
        audio.play_music("menu")  # start BGM immediately on launch / restart

        self.game_mode = "PVP"
        self.difficulty = "Medium"

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

        self.bot_pending_shot = False
        self.bot_shot_delay = 0.0
        self.tank_prev_x = [tank.x for tank in self.tanks]
        self.tank_est_vel_x = [0.0 for _ in self.tanks]

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
        self.bot_pending_shot = False
        self.bot_shot_delay = 0.0
        audio.stop_movement()  # ensure movement loop stops on turn change

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "menu":
            action = self.menu.handle_event(event)
            if action == "start":
                self.game_mode = self.menu.selected_mode
                self.difficulty = self.menu.selected_difficulty
                self.state = "playing"
                audio.play_music("battle")
            elif action is None and event.type == pygame.MOUSEBUTTONDOWN:
                # Button was clicked in menu (any click while in menu)
                audio.play_sfx("click")
            return

        # --- Pause overlay intercepts all events while paused ---
        if self.paused:
            result = self.pause_menu.handle_event(event)
            if result == "resume":
                self.paused = False
            elif result == "main_menu":
                self.paused = False
                self.__init__(self.screen)
            return

        if self.state == "game_over" and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            # Preserve the mode/difficulty the player chose — __init__ resets them to defaults
            saved_mode       = self.game_mode
            saved_difficulty = self.difficulty
            self.__init__(self.screen)
            self.game_mode   = saved_mode
            self.difficulty  = saved_difficulty
            self.state = "playing"
            audio.play_music("battle")
            return

        if self.state != "playing":
            return

        # ☰ button click → pause
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.hud.menu_btn_rect.collidepoint(event.pos)):
            self.paused = True
            audio.play_sfx("click")
            return

        # Escape during play → pause
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.state == "playing":
            self.paused = True
            return

        current = self.tanks[self.turn_index]
        if not current.is_alive:
            self._next_turn()
            return

        if self.active_bullet is not None:
            return

        if self._is_bot_turn():
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
        audio.play_sfx("shoot")  # fire SFX tied to bullet creation, not key press

    def _is_bot_turn(self) -> bool:
        return self.game_mode == "PVE" and self.turn_index == 1

    def _update_tank_motion_estimates(self, dt: float) -> None:
        """Track smoothed horizontal velocity for simple target-leading behavior."""
        if dt <= 1e-5:
            return

        alpha = 0.22
        for idx, tank in enumerate(self.tanks):
            raw_vx = (tank.x - self.tank_prev_x[idx]) / dt
            self.tank_est_vel_x[idx] = (1.0 - alpha) * self.tank_est_vel_x[idx] + alpha * raw_vx
            self.tank_prev_x[idx] = tank.x

    def _predict_target_x(self, shooter: Tank, target: Tank, target_idx: int, power: float) -> float:
        """Predict future target x using estimated velocity and approximate flight time."""
        distance = abs(target.x - shooter.x)
        lead_time = max(0.30, min(1.50, distance / max(120.0, power * 0.88)))
        predicted_x = target.x + self.tank_est_vel_x[target_idx] * lead_time
        return max(10.0, min(WIDTH - 10.0, predicted_x))

    def _orient_angle_toward(self, angle_left: float, shooter_x: float, target_x: float) -> float:
        """Convert a left-facing angle template to either side based on relative target position."""
        if shooter_x <= target_x:
            return 180.0 - angle_left
        return angle_left

    def _simulate_impact_point(self, shooter: Tank, angle_deg: float, power: float) -> tuple[float, float]:
        """Run a lightweight internal trajectory simulation to estimate impact location."""
        muzzle_x, muzzle_y = shooter.get_barrel_tip()
        rad = math.radians(angle_deg)
        x = muzzle_x
        y = muzzle_y
        vx = math.cos(rad) * power
        vy = -math.sin(rad) * power

        dt = 1.0 / 60.0
        for _ in range(360):
            vx += self.wind * dt
            vy += GRAVITY * dt
            x += vx * dt
            y += vy * dt

            if x < 0 or x > WIDTH or y > HEIGHT:
                break
            if self.terrain.is_solid_at(x, y):
                break

        return x, y

    def _eval_shot_error(
        self,
        shooter: Tank,
        target_x: float,
        target_y: float,
        angle_deg: float,
        power: float,
    ) -> tuple[float, float, float]:
        impact_x, impact_y = self._simulate_impact_point(shooter, angle_deg, power)
        error = abs(impact_x - target_x) + 0.35 * abs(impact_y - target_y)
        return error, impact_x, impact_y

    def _plan_easy_lookup_shot(self, shooter: Tank, target: Tank) -> tuple[float, float, float, float]:
        """Easy bot: distance lookup table + strong random noise."""
        distance = abs(target.x - shooter.x)
        ratio = max(0.0, min(1.0, distance / (WIDTH * 0.72)))

        table: tuple[tuple[float, float, float], ...] = (
            (0.16, 146.0, 270.0),
            (0.30, 139.0, 330.0),
            (0.44, 132.0, 400.0),
            (0.58, 126.0, 480.0),
            (0.74, 119.0, 565.0),
            (1.00, 112.0, 650.0),
        )

        base_angle_left = table[-1][1]
        base_power = table[-1][2]
        for threshold, angle_left, power in table:
            if ratio <= threshold:
                base_angle_left = angle_left
                base_power = power
                break

        angle = self._orient_angle_toward(base_angle_left, shooter.x, target.x)
        angle += random.uniform(-22.0, 22.0)
        power = base_power + random.uniform(-170.0, 170.0)

        if random.random() < 0.28:
            angle += random.uniform(-24.0, 24.0)
            power += random.uniform(-150.0, 150.0)

        angle = max(10.0, min(170.0, angle))
        power = max(SHOT_POWER_MIN, min(SHOT_POWER_MAX, power))
        return angle, power, 0.50, 1.05

    def _plan_medium_heuristic_shot(
        self,
        shooter: Tank,
        target: Tank,
        target_idx: int,
    ) -> tuple[float, float, float, float]:
        """Medium bot: weighted heuristic with predicted target lead and controlled noise."""
        predicted_target_x = self._predict_target_x(shooter, target, target_idx, SHOT_POWER_MAX)
        distance = abs(predicted_target_x - shooter.x)
        dist_ratio = max(0.0, min(1.0, distance / (WIDTH * 0.72)))

        power_span = SHOT_POWER_MAX - SHOT_POWER_MIN
        base_power = SHOT_POWER_MIN + power_span * (0.25 + 0.65 * dist_ratio)
        base_angle_left = 152.0 - 40.0 * dist_ratio
        base_angle = self._orient_angle_toward(base_angle_left, shooter.x, predicted_target_x)

        angle = base_angle + random.uniform(-15.0, 15.0)
        power = base_power + random.uniform(-120.0, 120.0)

        if random.random() < 0.12:
            angle += random.uniform(-18.0, 18.0)
            power += random.uniform(-130.0, 130.0)

        angle = max(10.0, min(170.0, angle))
        power = max(SHOT_POWER_MIN, min(SHOT_POWER_MAX, power))
        return angle, power, 0.40, 0.90

    def _plan_hard_refined_shot(
        self,
        shooter: Tank,
        target: Tank,
        target_idx: int,
    ) -> tuple[float, float, float, float]:
        """Hard bot: iterative refinement over simulated trajectory error."""
        target_x = self._predict_target_x(shooter, target, target_idx, 0.64 * SHOT_POWER_MAX)
        target_y = target.y - 18.0

        # Start from medium-quality guess, then optimize.
        best_angle, best_power, _, _ = self._plan_medium_heuristic_shot(shooter, target, target_idx)
        best_error, impact_x, _ = self._eval_shot_error(shooter, target_x, target_y, best_angle, best_power)

        angle_step = 13.0
        power_step = 95.0
        for _ in range(8):
            candidates = (
                (best_angle, best_power),
                (best_angle + angle_step, best_power),
                (best_angle - angle_step, best_power),
                (best_angle, best_power + power_step),
                (best_angle, best_power - power_step),
                (best_angle + angle_step, best_power + power_step),
                (best_angle - angle_step, best_power + power_step),
                (best_angle + angle_step, best_power - power_step),
                (best_angle - angle_step, best_power - power_step),
            )

            improved = False
            for cand_angle, cand_power in candidates:
                cand_angle = max(10.0, min(170.0, cand_angle))
                cand_power = max(SHOT_POWER_MIN, min(SHOT_POWER_MAX, cand_power))
                cand_error, cand_impact_x, _ = self._eval_shot_error(
                    shooter,
                    target_x,
                    target_y,
                    cand_angle,
                    cand_power,
                )
                if cand_error < best_error:
                    best_error = cand_error
                    best_angle = cand_angle
                    best_power = cand_power
                    impact_x = cand_impact_x
                    improved = True

            # Nudge power with a binary-search-like correction for horizontal overshoot.
            if not improved:
                if shooter.x <= target_x:
                    horizontal_error = impact_x - target_x
                else:
                    horizontal_error = target_x - impact_x
                best_power -= max(-60.0, min(60.0, horizontal_error * 0.18))
                best_power = max(SHOT_POWER_MIN, min(SHOT_POWER_MAX, best_power))

            angle_step *= 0.58
            power_step *= 0.62

        best_angle += random.uniform(-4.0, 4.0)
        best_power += random.uniform(-34.0, 34.0)
        best_angle = max(10.0, min(170.0, best_angle))
        best_power = max(SHOT_POWER_MIN, min(SHOT_POWER_MAX, best_power))
        return best_angle, best_power, 0.28, 0.62

    def _plan_bot_shot(self, shooter: Tank, target: Tank, target_idx: int) -> None:
        if self.difficulty == "Easy":
            angle, power, delay_min, delay_max = self._plan_easy_lookup_shot(shooter, target)
        elif self.difficulty == "Hard":
            angle, power, delay_min, delay_max = self._plan_hard_refined_shot(shooter, target, target_idx)
        else:
            angle, power, delay_min, delay_max = self._plan_medium_heuristic_shot(shooter, target, target_idx)

        shooter.aim_angle_deg = angle
        self.charge_power = power
        self.bot_pending_shot = True
        self.bot_shot_delay = random.uniform(delay_min, delay_max)

    def _update_bot_turn(self, dt: float, shooter: Tank) -> None:
        if not shooter.is_alive or self.active_bullet is not None:
            return

        target_idx = (self.turn_index + 1) % len(self.tanks)
        target = self.tanks[target_idx]
        if not target.is_alive:
            return

        if not self.bot_pending_shot:
            self._plan_bot_shot(shooter, target, target_idx)

        self.bot_shot_delay -= dt
        if self.bot_shot_delay <= 0.0:
            self._fire_charged_shot(shooter)
            self.bot_pending_shot = False
            self.bot_shot_delay = 0.0

    def update(self, dt: float) -> None:
        # Always tick the game-over overlay even when gameplay is frozen
        if self.state == "game_over" and self._game_over_overlay is not None:
            self._game_over_overlay.update(dt)

        if self.state != "playing" or self.paused:
            return

        current = self.tanks[self.turn_index]

        for tank in self.tanks:
            tank.apply_gravity(dt, self.terrain)

        self._update_tank_motion_estimates(dt)

        if self.active_bullet is None and current.is_alive and self._is_bot_turn():
            self._update_bot_turn(dt, current)

        # Determine whether the human player is actually moving this frame.
        # Must be checked unconditionally every frame so the sound stops
        # when bullets are in flight, charging, or it's the bot's turn.
        _player_moving = False

        if self.active_bullet is None and current.is_alive and not self.is_charging and not self._is_bot_turn():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                current.move_horizontal(-1.0, dt, self.terrain)
                _player_moving = True
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                current.move_horizontal(1.0, dt, self.terrain)
                _player_moving = True

            # Gunny-like cannon control: Up/Down (or W/S) changes barrel angle.
            aim_speed = 95.0
            aiming = False
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                delta = aim_speed * dt
                if self.turn_index == 0:
                    current.aim_angle_deg = min(170.0, current.aim_angle_deg + delta)
                else:
                    current.aim_angle_deg = max(10.0, current.aim_angle_deg - delta)
                aiming = True

            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                delta = aim_speed * dt
                if self.turn_index == 0:
                    current.aim_angle_deg = max(10.0, current.aim_angle_deg - delta)
                else:
                    current.aim_angle_deg = min(170.0, current.aim_angle_deg + delta)
                aiming = True

            # Angle-change SFX: throttle to once per ~200 ms to avoid spam
            if aiming:
                self._angle_sfx_timer = getattr(self, "_angle_sfx_timer", 0.0) - dt
                if self._angle_sfx_timer <= 0.0:
                    audio.play_sfx("angle")
                    self._angle_sfx_timer = 0.20
            else:
                self._angle_sfx_timer = 0.0

        # Always update movement sound — False stops the loop when not moving
        audio.update_movement(_player_moving)


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
            self._explode(self.active_bullet, direct_hit_tank=target)
            return

    def _bullet_hits_tank(self, bullet: Bullet, tank: Tank) -> bool:
        mask, rect = tank.get_mask_and_rect()
        local_x = int(bullet.x - rect.left)
        local_y = int(bullet.y - rect.top)

        if local_x < 0 or local_y < 0 or local_x >= rect.width or local_y >= rect.height:
            return False

        return bool(mask.get_at((local_x, local_y)))

    def _explode(self, bullet: Bullet, direct_hit_tank: Tank | None = None) -> None:
        self.terrain.carve_crater(bullet.x, bullet.y, bullet.explosion_radius)
        self._apply_explosion_damage(bullet.x, bullet.y, bullet, direct_hit_tank)
        # Play the correct explosion sound based on what was hit
        if direct_hit_tank is not None:
            audio.play_sfx("hit_tank")
        else:
            audio.play_sfx("hit_ground")
        self.active_bullet = None
        self._next_turn()
        self._check_game_over()

    def _apply_explosion_damage(
        self,
        x: float,
        y: float,
        bullet: Bullet,
        direct_hit_tank: Tank | None = None,
    ) -> None:
        for tank in self.tanks:
            if not tank.is_alive:
                continue

            if direct_hit_tank is tank:
                tank.take_damage(bullet.damage)
                continue

            blast_radius = max(EXPLOSION_DAMAGE_RADIUS, bullet.explosion_radius * 1.6)
            distance = math.dist((x, y), (tank.x, tank.y))
            if distance <= blast_radius:
                ratio = 1.0 - (distance / blast_radius)
                damage = int(max(1, bullet.damage * (0.45 + 0.55 * ratio)))
                tank.take_damage(damage)

    def _check_game_over(self) -> None:
        alive = [idx for idx, tank in enumerate(self.tanks) if tank.is_alive]
        if len(alive) == 1:
            if self.state != "game_over":  # only trigger once
                winner_idx = alive[0]
                self.state = "game_over"
                self.winner_text = f"Player {winner_idx + 1} wins"
                self.winner_color = self.tanks[alive[0]].color
                self._game_over_overlay = GameOverOverlay(winner_idx)
                # Play victory music for the human player's perspective
                if self.game_mode == "PVE" and alive[0] == 1:
                    audio.play_music("lose", fade_ms=800)
                else:
                    audio.play_music("victory", fade_ms=800)
        elif len(alive) == 0:
            if self.state != "game_over":
                self.state = "game_over"
                self.winner_text = "Draw"
                self.winner_color = (40, 40, 40)
                self._game_over_overlay = GameOverOverlay(None)
                audio.play_music("lose", fade_ms=800)

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
        bg = assets.get_image("bg/battlefield")
        if bg is not None:
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(SKY_BLUE)

        if self.state == "menu":
            self.menu.draw(self.screen)
            return

        # Only draw primitive decorations when no background image is loaded
        # (the image already contains clouds, sun, and scenery)
        if bg is None:
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

        # Game-over animated overlay
        if self.state == "game_over" and self._game_over_overlay is not None:
            self._game_over_overlay.draw(self.screen)

        # Pause overlay on top of everything else
        if self.paused:
            self.pause_menu.draw(self.screen)
