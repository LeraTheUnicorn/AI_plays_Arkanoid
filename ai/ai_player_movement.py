"""
Модуль для движения платформы в AIPlayer.
Содержит методы расчета скорости, выполнения движения и отслеживания плавности.
"""

import time
import random
from typing import Dict, Optional, Any

from .game_state import Point


class AIPlayerMovementMixin:
    """
    Миксин для методов движения платформы.
    Добавляет методы расчета скорости, выполнения движения и отслеживания плавности.
    """
    
    def calculate_adaptive_paddle_speed(
        self, current_x: int, optimal_x: int, ball_speed: int
    ) -> int:
        """
        Рассчитывает адаптивную скорость платформы на основе физики игры.
        """
        base_paddle_speed = max(35, min(int(ball_speed * 2.5), 60))
        min_speed = 35
        max_speed = 60
        
        if not self.current_game_state:
            return base_paddle_speed
        
        distance_to_optimal = abs(optimal_x - current_x)
        
        if distance_to_optimal <= 5:
            return min_speed
        
        time_to_meeting: float = 0.0
        if self.is_ball_moving_towards_paddle() and self.current_game_state:
            game_state = self.current_game_state
            ball_y = game_state.ball_position.y
            paddle_y = game_state.paddle_position.y
            ball_vel_y = game_state.ball_velocity.y
            
            if ball_vel_y > 0:
                distance_y = paddle_y - ball_y
                if distance_y > 0:
                    time_to_meeting = distance_y / ball_vel_y
                    time_to_meeting = max(0.0, time_to_meeting)
        
        required_speed: float = float(base_paddle_speed)
        
        if time_to_meeting > 0 and time_to_meeting != float("inf"):
            if time_to_meeting <= 20:
                required_speed = max(
                    float(base_paddle_speed * 2.5),
                    float(distance_to_optimal) / max(time_to_meeting * 0.5, 1),
                )
            elif time_to_meeting <= 40:
                required_speed = max(
                    float(base_paddle_speed * 2.0),
                    float(distance_to_optimal) / max(time_to_meeting * 0.6, 1),
                )
            elif time_to_meeting <= 80:
                required_speed = max(
                    float(base_paddle_speed * 1.5),
                    float(distance_to_optimal) / max(time_to_meeting * 0.8, 1),
                )
            else:
                required_speed = max(float(min_speed), float(base_paddle_speed * 1.0))
        else:
            required_speed = float(base_paddle_speed * 0.8)
        
        speed_ratio = float(ball_speed) / 5.0
        speed_multiplier = 0.7 + speed_ratio * 0.6
        required_speed *= speed_multiplier
        
        if distance_to_optimal > 150:
            required_speed *= 1.4
        elif distance_to_optimal > 100:
            required_speed *= 1.2
        elif distance_to_optimal > 50:
            required_speed *= 1.1
        
        if (
            distance_to_optimal > time_to_meeting * ball_speed * 0.8
            and time_to_meeting > 0
        ):
            required_speed *= 1.3
        
        required_speed = max(min_speed, min(max_speed, required_speed))
        
        if distance_to_optimal > 20:
            variation = random.uniform(0.97, 1.03)
            required_speed *= variation
        
        return int(required_speed)

    def _execute_movement_strategy(self, current_x: int, paddle_speed: int) -> int:
        """Выполняет стратегию движения платформы."""
        self._logger.debug(f"[AI_PLAYER_MOVE] Вызываем paddle_movement_strategy.move_paddle_towards: current_x={current_x}, paddle_speed={paddle_speed}")
        self.paddle_movement_strategy.current_game_state = self.current_game_state
        result = self.paddle_movement_strategy.move_paddle_towards(current_x, paddle_speed)
        self._logger.debug(f"[AI_PLAYER_MOVE] paddle_movement_strategy вернул: {result}")
        return result

    def _validate_movement_conditions(self, current_x: int, paddle_speed: int) -> bool:
        """Проверяет условия для движения платформы."""
        if not self.current_game_state or not self.is_active:
            self._logger.debug(f"[PADDLE DEBUG] move_paddle_towards: current_game_state={self.current_game_state is not None}, is_active={self.is_active}")
            return False
        return True

    def _fallback_movement(self, current_x: int) -> int:
        """Резервное движение платформы - улучшенное следование за мячом."""
        if not self.current_game_state:
            return 0

        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y

        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
            if time_to_paddle > 0:
                predicted_x = ball_x + vel_x * time_to_paddle

                screen_width = self.screen_width
                ball_radius = self.config.ball.radius

                while (
                    predicted_x < ball_radius
                    or predicted_x > screen_width - ball_radius
                ):
                    if predicted_x < ball_radius:
                        predicted_x = 2 * ball_radius - predicted_x
                        vel_x = abs(vel_x)
                    elif predicted_x > screen_width - ball_radius:
                        predicted_x = 2 * (screen_width - ball_radius) - predicted_x
                        vel_x = -abs(vel_x)
                target_x = predicted_x
            else:
                target_x = ball_x
        else:
            prediction_factor = abs(vel_x) * 2
            if vel_x > 0:
                target_x = ball_x + prediction_factor
            elif vel_x < 0:
                target_x = ball_x - prediction_factor
            else:
                target_x = ball_x

        distance = target_x - current_x
        tolerance = 3

        if abs(distance) <= tolerance:
            return 0
        return 1 if distance > 0 else -1

    def _reevaluate_after_bounce(self) -> None:
        """Переоценивает ситуацию после отбития мяча."""
        if not self.current_game_state:
            return

        target_brick = self.target_selector.find_best_target_brick(
            self.current_game_state,
            self.current_game_state.paddle_position.y,
            self.current_game_state.ball_position.x,
        )
        if target_brick:
            self.targeting_system.target_brick = target_brick
            landing_x = self._predict_exact_landing_position()
            new_offset = self.position_calculator.calculate_optimal_offset(
                landing_x, target_brick, self.current_game_state
            )
            self.targeting_system.optimal_offset = new_offset

        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        
        self.separation_zone_tracker.ball_entered_separation_zone = False
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        self.separation_zone_tracker.last_movement_frame = 0

    def _update_loop_tracking(self, movement: int, current_x: int, optimal_x: int) -> None:
        """Обновляет данные отслеживания зацикливания."""
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 20:
            self.loop_prevention_system["movement_history"] = (
                self.loop_prevention_system["movement_history"][-10:]
            )

        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        if self.current_game_state:
            trajectory_info = {
                "ball_x": self.current_game_state.ball_position.x,
                "ball_y": self.current_game_state.ball_position.y,
                "optimal_x": optimal_x,
                "timestamp": time.time(),
            }
            self.loop_prevention_system["trajectory_history"].append(trajectory_info)
            if len(self.loop_prevention_system["trajectory_history"]) > 10:
                self.loop_prevention_system["trajectory_history"] = (
                    self.loop_prevention_system["trajectory_history"][-5:]
                )

    def _update_smoothness_tracking(self, movement: int, current_x: int) -> None:
        """Обновляет данные отслеживания плавности движения."""
        self.smoothness_system["recent_movements"].append(movement)
        if (
            len(self.smoothness_system["recent_movements"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_movements"] = self.smoothness_system[
                "recent_movements"
            ][-self.smoothness_system["jitter_window"] :]

        self.smoothness_system["recent_positions"].append(current_x)
        if (
            len(self.smoothness_system["recent_positions"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_positions"] = self.smoothness_system[
                "recent_positions"
            ][-self.smoothness_system["jitter_window"] :]

        if len(self.smoothness_system["recent_movements"]) >= 2:
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                self.smoothness_system["movement_changes"].append(time.time())
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]

    def _detect_jitter(self) -> bool:
        """Обнаруживает дрожание платформы (частые смены направления движения)."""
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False

        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1

        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True

        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True

        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            if (
                position_variance < 10
                and len([m for m in movements[-5:] if m != 0]) >= 3
            ):
                return True

        return False

    def _calculate_smooth_movement(
        self, current_x: int, optimal_x: int, distance: float
    ) -> int:
        """Вычисляет плавное движение с учетом штрафов за дрожание."""
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if self.current_game_state and hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        if self.separation_zone_tracker.target_position_set:
            effective_min_distance = 30
        else:
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (
                1 + penalty
            )

        if distance < effective_min_distance:
            return 0

        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0
