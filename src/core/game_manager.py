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
from src.core.map_config import get_map_config
from src.utils.settings_store import settings
from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
from src.utils.constants import (
    EXPLOSION_DAMAGE_RADIUS,
    FONT_SIZE_TITLE,
    FUEL_COST_PER_PIXEL,
    GRAVITY,
    GREEN,
    HEIGHT,
    RED,
    SHOT_CHARGE_RATE,
    SHOT_POWER_MAX,
    SHOT_POWER_MIN,
    SKY_BLUE,
    TANK_MAX_DROP,
    TANK_MOVE_SPEED,
    TANK_STEP_UP,
    WIND_MAX,
    WIND_MIN,
    WIDTH,
)


class GameManager:
    """High-level game state coordinator."""

    def __init__(self, screen: pygame.Surface, level_id: int = 1) -> None:
        self.screen = screen
        self.state = "menu"
        
        # Load map config and apply physics settings early so Terrain can use it
        self.level_id = level_id
        config = get_map_config(level_id)
        self.map_config = config
        
        self.menu = MainMenu()
        self.hud = HUD()
        self.terrain = Terrain(config)
        self.pause_menu = PauseMenu()
        self.paused = False
        self._game_over_overlay: GameOverOverlay | None = None
        audio.play_music("menu")  # start BGM immediately on launch / restart

        self.game_mode = "PVP"
        self.difficulty = "Medium"

        self._effective_gravity = config.gravity
        self._effective_wind_min = config.wind_mag_min
        self._effective_wind_max = config.wind_mag_max
        self._effective_fuel_cost = config.fuel_cost

        # Determine wind magnitude and randomize direction
        mag = random.uniform(self._effective_wind_min, self._effective_wind_max)
        self.wind = mag if random.choice([True, False]) else -mag
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
        self.bot_move_direction = 0.0
        self.bot_move_time_left = 0.0
        self.bot_reposition_done = False
        self.tank_prev_x = [tank.x for tank in self.tanks]
        self.tank_est_vel_x = [0.0 for _ in self.tanks]
        self.explosion_effects: list[dict[str, object]] = []

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
        mag = random.uniform(self._effective_wind_min, self._effective_wind_max)
        self.wind = mag if random.choice([True, False]) else -mag
        self.current_bullet_type = random.choice(BULLET_TYPES)
        self._reset_turn_inputs()
        self.bot_pending_shot = False
        self.bot_shot_delay = 0.0
        self.bot_move_direction = 0.0
        self.bot_move_time_left = 0.0
        self.bot_reposition_done = False
        audio.stop_movement()  # ensure movement loop stops on turn change

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "menu":
            action = self.menu.handle_event(event)
            if isinstance(action, tuple) and action[0] == "start":
                level_id = action[1]
                # Preserve menu selection before __init__ resets self.menu
                mode = self.menu.selected_mode
                diff = self.menu.selected_difficulty
                
                # Re-init with selected level
                self.__init__(self.screen, level_id)
                self.game_mode = mode
                self.difficulty = diff
                self.state = "playing"
                audio.play_music("battle")
            elif action is None and event.type == pygame.MOUSEBUTTONDOWN:
                audio.play_sfx("click")
            return

        # --- Pause overlay intercepts all events while paused ---
        if self.paused:
            result = self.pause_menu.handle_event(event)
            if result == "resume":
                self.paused = False
            elif result == "main_menu":
                self.paused = False
                self.__init__(self.screen, 1) # Back to level 1 for safety, menu state will be reset anyway
                self.state = "menu"
            return

        if self.state == "game_over" and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            # Preserve level, mode, difficulty
            saved_level = self.level_id
            saved_mode = self.game_mode
            saved_difficulty = self.difficulty
            self.__init__(self.screen, saved_level)
            self.game_mode = saved_mode
            self.difficulty = saved_difficulty
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

        # If muzzle is too close to terrain/obstacle, shot backfires onto shooter.
        blocked = False
        for probe in (0.0, 8.0, 15.0):
            px = muzzle_x + dir_x * probe
            py = muzzle_y + dir_y * probe
            if self.terrain.is_solid_at(px, py):
                blocked = True
                break

        if blocked:
            backfire_damage = int(max(8, self.current_bullet_type.damage * 0.62))
            tank.take_damage(backfire_damage)
            backfire_radius = max(12, int(self.current_bullet_type.explosion_radius * 0.45))
            self.terrain.carve_crater(muzzle_x, muzzle_y, backfire_radius)
            self._spawn_explosion_effect(muzzle_x, muzzle_y, backfire_radius, direct_hit=False)
            audio.play_sfx("hit_ground")
            self.aim_ready = False
            self._next_turn()
            self._check_game_over()
            return

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
            vy += self._effective_gravity * dt
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

    def _is_path_navigable(self, from_x: float, to_x: float) -> bool:
        """Reject moves that cross cliffs too steep for the tank step/drop limits."""
        if abs(to_x - from_x) < 1.0:
            return True

        direction = 1.0 if to_x > from_x else -1.0
        probe_step = 22.0
        x = from_x
        prev_ground = self.terrain.get_surface_y(x)
        if prev_ground is None:
            return False

        while (direction > 0 and x < to_x) or (direction < 0 and x > to_x):
            x += direction * probe_step
            if (direction > 0 and x > to_x) or (direction < 0 and x < to_x):
                x = to_x

            ground = self.terrain.get_surface_y(x)
            if ground is None:
                return False

            climb = ground - prev_ground
            if climb > TANK_STEP_UP + 4:
                return False
            if climb < -(TANK_MAX_DROP + 6):
                return False

            prev_ground = ground

        return True

    def _estimate_error_for_x(self, shooter: Tank, target: Tank, target_idx: int, candidate_x: float) -> float:
        """Estimate shot quality from a hypothetical x-position (lower is better)."""
        original_x = shooter.x
        original_y = shooter.y
        original_vy = shooter.vy
        original_slope = shooter.slope_angle_deg

        shooter.x = candidate_x
        shooter.snap_to_ground(self.terrain)

        predicted_target_x = self._predict_target_x(shooter, target, target_idx, SHOT_POWER_MAX)
        distance = abs(predicted_target_x - shooter.x)
        dist_ratio = max(0.0, min(1.0, distance / (WIDTH * 0.72)))

        power_span = SHOT_POWER_MAX - SHOT_POWER_MIN
        power = SHOT_POWER_MIN + power_span * (0.25 + 0.65 * dist_ratio)
        angle_left = 152.0 - 40.0 * dist_ratio
        angle = self._orient_angle_toward(angle_left, shooter.x, predicted_target_x)
        target_y = target.y - 18.0
        shot_error, _, _ = self._eval_shot_error(shooter, predicted_target_x, target_y, angle, power)

        shooter.x = original_x
        shooter.y = original_y
        shooter.vy = original_vy
        shooter.slope_angle_deg = original_slope
        return shot_error

    def _choose_bot_reposition(self, shooter: Tank, target: Tank, target_idx: int) -> None:
        """Choose a short strategic move before shooting.

        Bot evaluates nearby positions by estimated hit error + tactical spacing,
        then moves only when there is a meaningful improvement.
        """
        if shooter.fuel <= 1.0:
            self.bot_reposition_done = True
            return

        if self.difficulty == "Easy":
            offsets = (-80.0, -48.0, 0.0, 48.0, 80.0)
            max_travel = 95.0
            ideal_distance = 440.0
            move_penalty = 0.48
            improve_threshold = 44.0
        elif self.difficulty == "Hard":
            offsets = (-210.0, -140.0, -90.0, -48.0, 0.0, 48.0, 90.0, 140.0, 210.0)
            max_travel = 220.0
            ideal_distance = 600.0
            move_penalty = 0.26
            improve_threshold = 18.0
        else:
            offsets = (-150.0, -96.0, -56.0, 0.0, 56.0, 96.0, 150.0)
            max_travel = 165.0
            ideal_distance = 540.0
            move_penalty = 0.34
            improve_threshold = 28.0

        current_x = shooter.x
        baseline_error = self._estimate_error_for_x(shooter, target, target_idx, current_x)
        baseline_score = baseline_error + abs(abs(target.x - current_x) - ideal_distance) * 0.28

        best_x = current_x
        best_score = baseline_score

        for offset in offsets:
            candidate_x = max(12.0, min(WIDTH - 12.0, current_x + offset))
            travel = abs(candidate_x - current_x)
            if travel > max_travel + 1e-5:
                continue
            if not self._is_path_navigable(current_x, candidate_x):
                continue

            error = self._estimate_error_for_x(shooter, target, target_idx, candidate_x)
            tactical_spacing = abs(abs(target.x - candidate_x) - ideal_distance) * 0.28
            danger_penalty = 0.0
            if abs(target.x - candidate_x) < 190.0:
                danger_penalty += (190.0 - abs(target.x - candidate_x)) * 0.35

            score = error + tactical_spacing + travel * move_penalty + danger_penalty
            if score < best_score:
                best_score = score
                best_x = candidate_x

        gain = baseline_score - best_score
        if gain <= improve_threshold or abs(best_x - current_x) < 8.0:
            self.bot_reposition_done = True
            return

        self.bot_move_direction = 1.0 if best_x > current_x else -1.0
        self.bot_move_time_left = abs(best_x - current_x) / max(1.0, TANK_MOVE_SPEED)
        self.bot_reposition_done = True

    def _update_bot_turn(self, dt: float, shooter: Tank) -> None:
        if not shooter.is_alive or self.active_bullet is not None:
            return

        target_idx = (self.turn_index + 1) % len(self.tanks)
        target = self.tanks[target_idx]
        if not target.is_alive:
            return

        if self.bot_move_time_left > 0.0 and abs(self.bot_move_direction) > 0.0:
            prev_x = shooter.x
            shooter.move_horizontal(self.bot_move_direction, dt, self.terrain, self._effective_fuel_cost)
            moved = abs(shooter.x - prev_x) > 0.04
            if moved:
                self.bot_move_time_left = max(0.0, self.bot_move_time_left - dt)
            else:
                self.bot_move_time_left = 0.0

            if self.bot_move_time_left <= 0.0:
                self.bot_move_direction = 0.0

            # Reposition phase consumes this frame; shoot on subsequent frame.
            return

        if not self.bot_reposition_done:
            self._choose_bot_reposition(shooter, target, target_idx)
            if self.bot_move_time_left > 0.0:
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

        self._update_explosion_effects(dt)

        if self.state != "playing" or self.paused:
            return

        current = self.tanks[self.turn_index]

        for tank in self.tanks:
            tank.apply_gravity(dt, self.terrain, self._effective_gravity)

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
                current.move_horizontal(-1.0, dt, self.terrain, self._effective_fuel_cost)
                _player_moving = True
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                current.move_horizontal(1.0, dt, self.terrain, self._effective_fuel_cost)
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

        self.active_bullet.update(dt, self.wind, self._effective_gravity)

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
        self._spawn_explosion_effect(bullet.x, bullet.y, bullet.explosion_radius, direct_hit=direct_hit_tank is not None)
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
                self._game_over_overlay = GameOverOverlay(winner_idx, self.game_mode)
                # Play victory music for PVP wins or Human PVE wins
                if self.game_mode == "PVP":
                    audio.play_music("victory", fade_ms=800)
                elif self.game_mode == "PVE" and alive[0] == 1: # Bot won
                    audio.play_music("lose", fade_ms=800)
                else: # Human won PVE
                    audio.play_music("victory", fade_ms=800)
                    # Unlock next level if this was the highest level in PVE
                    if self.game_mode == "PVE" and self.level_id == settings.max_unlocked_level:
                        settings.max_unlocked_level = min(6, self.level_id + 1)
        elif len(alive) == 0:
            if self.state != "game_over":
                self.state = "game_over"
                self.winner_text = "Draw"
                self.winner_color = (40, 40, 40)
                self._game_over_overlay = GameOverOverlay(None, self.game_mode)
                audio.play_music("lose", fade_ms=800)

    def _spawn_explosion_effect(self, x: float, y: float, radius: int, direct_hit: bool) -> None:
        """Create a short-lived VFX packet for one explosion event."""
        particle_count = max(12, min(36, radius // 2))
        particles: list[dict[str, float | tuple[int, int, int]]] = []
        for _ in range(particle_count):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(90.0, 280.0) * (0.9 + radius / 110.0)
            ttl = random.uniform(0.18, 0.48)
            if direct_hit:
                color = random.choice(((255, 245, 170), (255, 182, 74), (255, 108, 66), (225, 70, 62)))
            else:
                color = random.choice(((255, 236, 140), (255, 166, 76), (212, 110, 66), (126, 90, 78)))

            particles.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "age": 0.0,
                    "ttl": ttl,
                    "size": random.uniform(2.0, 5.8),
                    "color": color,
                }
            )

        self.explosion_effects.append(
            {
                "x": x,
                "y": y,
                "age": 0.0,
                "duration": 0.40,
                "radius": float(radius),
                "particles": particles,
                "direct_hit": direct_hit,
            }
        )

    def _update_explosion_effects(self, dt: float) -> None:
        if not self.explosion_effects:
            return

        alive_effects: list[dict[str, object]] = []
        for effect in self.explosion_effects:
            effect["age"] = float(effect["age"]) + dt
            duration = float(effect["duration"])

            alive_particles: list[dict[str, float | tuple[int, int, int]]] = []
            for p in effect["particles"]:  # type: ignore[index]
                p["age"] = float(p["age"]) + dt
                if float(p["age"]) >= float(p["ttl"]):
                    continue

                p["x"] = float(p["x"]) + float(p["vx"]) * dt
                p["y"] = float(p["y"]) + float(p["vy"]) * dt
                p["vy"] = float(p["vy"]) + 560.0 * dt
                alive_particles.append(p)

            effect["particles"] = alive_particles

            if float(effect["age"]) < duration or alive_particles:
                alive_effects.append(effect)

        self.explosion_effects = alive_effects

    def _draw_explosion_effects(self, screen: pygame.Surface) -> None:
        if not self.explosion_effects:
            return

        for effect in self.explosion_effects:
            x = int(float(effect["x"]))
            y = int(float(effect["y"]))
            age = float(effect["age"])
            duration = float(effect["duration"])
            radius = float(effect["radius"])
            direct_hit = bool(effect["direct_hit"])
            progress = min(1.0, age / max(1e-5, duration))

            # Expanding bright core and shockwave ring.
            core_radius = int(max(1.0, (0.22 + 0.35 * (1.0 - progress)) * radius))
            if core_radius > 0:
                core_color = (255, 246, 188) if direct_hit else (255, 232, 150)
                pygame.draw.circle(screen, core_color, (x, y), core_radius)

            ring_radius = int((0.35 + 1.05 * progress) * radius)
            ring_width = max(1, int(4 * (1.0 - progress)))
            if ring_radius > 1 and ring_width > 0:
                ring_color = (255, 145, 86) if direct_hit else (224, 138, 92)
                pygame.draw.circle(screen, ring_color, (x, y), ring_radius, width=ring_width)

            for p in effect["particles"]:  # type: ignore[index]
                life_ratio = 1.0 - float(p["age"]) / max(1e-5, float(p["ttl"]))
                r = int(max(1.0, float(p["size"]) * life_ratio))
                if r <= 0:
                    continue
                px = int(float(p["x"]))
                py = int(float(p["y"]))
                pygame.draw.circle(screen, p["color"], (px, py), r)

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
        bg_key = self.map_config.bg_image if self.state != "menu" else "bg/main_menu"
        bg = assets.get_image(bg_key)
        if bg is not None:
            if bg.get_size() != (WIDTH, HEIGHT):
                bg = pygame.transform.smoothscale(bg, (WIDTH, HEIGHT))
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(SKY_BLUE if self.state != "menu" else (100, 200, 255))

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

        self._draw_explosion_effects(self.screen)

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
