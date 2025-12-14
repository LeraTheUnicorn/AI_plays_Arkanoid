"""
Модуль предотвращения зацикливания AIPlayer.

Содержит методы для обнаружения и предотвращения зацикливания движений платформы,
а также отслеживания плавности движения.
"""

from typing import Optional, Any


class AIPlayerLoopPreventionMixin:
    """Миксин для методов предотвращения зацикливания AIPlayer."""

    def _detect_loop_pattern(self) -> bool:
        """
        Обнаруживает зацикливание в движениях платформы.

        Возвращает True, если обнаружен повторяющийся паттерн движений
        или вертикальные траектории мяча.
        """
        history = self.loop_prevention_system["movement_history"]
        trajectory_history = self.loop_prevention_system["trajectory_history"]

        threshold = self.loop_prevention_system["loop_detection_threshold"]

        # Нужно достаточно данных
        if len(history) < threshold * 2:
            return False

        # Проверяем последние движения
        recent_movements = history[-threshold:]
        movement_counts: dict[int, int] = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1

        max_count = max(movement_counts.values())
        # 80% одинаковых движений считается зацикливанием
        if max_count >= threshold * 0.8:
            return True

        # Позиционная стагнация
        position_history = self.loop_prevention_system["position_history"]
        if len(position_history) >= 10:
            recent_positions = position_history[-10:]
            # Если за последние 8 кадров платформа почти не меняла позицию
            if len(set(recent_positions[-8:])) <= 2:
                return True

        # Вертикальные траектории мяча
        if len(trajectory_history) >= 5 and self.current_game_state:
            recent_trajectories = trajectory_history[-5:]
            vertical_count = 0
            for traj in recent_trajectories:
                prev_ball_x = traj.get("ball_x")
                if prev_ball_x is None:
                    continue
                current_ball_x = self.current_game_state.ball_position.x
                if abs(current_ball_x - prev_ball_x) < 3:
                    vertical_count += 1
            # 4 из 5 почти вертикальные — считаем зацикливанием
            if vertical_count >= 4:
                return True

        return False
    
    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания."""
        if not self._detect_loop_pattern():
            return

        # Учитываем кулдаун
        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return

        # Смена стратегии
        strategies = self.loop_prevention_system["alternative_strategies"]
        idx = self.loop_prevention_system["current_strategy_index"]
        self.loop_prevention_system["current_strategy_index"] = (idx + 1) % len(
            strategies
        )
        new_strategy = strategies[self.loop_prevention_system["current_strategy_index"]]

        # Кулдаун и сброс истории
        self.loop_prevention_system["strategy_change_cooldown"] = 10
        
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []

    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """
        Применяет альтернативную стратегию позиционирования для выхода из зацикливания.
        """
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]
        screen_center = self.screen_width // 2

        if strategy == "center_focus":
            # Фокусируемся на центре экрана
            return screen_center

        if strategy == "edge_focus":
            # Фокусируемся на краях для смены паттерна
            current_pos = getattr(self.current_game_state, "paddle_position", None)
            if current_pos and hasattr(current_pos, "x"):
                return self.screen_width - 70 if current_pos.x < screen_center else 70
            return 70

        if strategy == "predictive_targeting":
            # Агрессивное прицеливание в дальние кубики
            target_brick = self._find_most_distant_brick()
            if target_brick:
                landing_x = self._predict_exact_landing_position()
                brick_center_x = (
                    getattr(target_brick, "x", 0)
                    + getattr(target_brick, "width", 60) / 2
                )
                offset_direction = 1 if brick_center_x > landing_x else -1
                return int(optimal_position + offset_direction * 30)

        return optimal_position

    def _find_most_distant_brick(self) -> Optional[Any]:
        """Находит самый дальний по Y кубик от платформы."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        paddle_y = self.current_game_state.paddle_position.y

        most_distant_brick = None
        max_distance = -1.0

        for brick in bricks:
            brick_y = getattr(brick, "y", 0)
            distance = abs(paddle_y - brick_y)
            if distance > max_distance:
                max_distance = distance
                most_distant_brick = brick

        return most_distant_brick

    def _update_loop_tracking(
        self,
        movement: int,
        current_x: int,
        optimal_x: int,
    ) -> None:
        """Обновляет данные отслеживания зацикливания."""
        # История движений
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = (
                self.loop_prevention_system["movement_history"][-10:]
            )

        # История позиций
        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        # История траекторий
        if self.current_game_state:
            import time
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
        # История движений
        self.smoothness_system["recent_movements"].append(movement)
        if (
            len(self.smoothness_system["recent_movements"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_movements"] = self.smoothness_system[
                "recent_movements"
            ][-self.smoothness_system["jitter_window"] :]

        # История позиций
        self.smoothness_system["recent_positions"].append(current_x)
        if (
            len(self.smoothness_system["recent_positions"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_positions"] = self.smoothness_system[
                "recent_positions"
            ][-self.smoothness_system["jitter_window"] :]

        # Отслеживание смен направления движения
        if len(self.smoothness_system["recent_movements"]) >= 2:
            import time
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                # Произошла смена направления
                self.smoothness_system["movement_changes"].append(time.time())
                # Очищаем старые записи (старше 1 секунды)
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]

    def _detect_jitter(self) -> bool:
        """
        Обнаруживает дрожание платформы (частые смены направления движения).
        
        Returns:
            True, если обнаружено дрожание.
        """
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False

        # Подсчитываем количество смен направления в последних движениях
        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            # Смена направления: с -1 на 1, с 1 на -1, или с любого на противоположное
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1

        # Если слишком много смен направления - это дрожание
        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True

        # Дополнительная проверка: частые смены направления за короткое время
        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True

        # Проверка на микродвижения (очень маленькие изменения позиции)
        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            # Если позиция меняется очень мало, но часто - это дрожание
            if (
                position_variance < 10
                and len([m for m in movements[-5:] if m != 0]) >= 3
            ):
                return True

        return False

    def _calculate_smooth_movement(
        self, current_x: int, optimal_x: int, distance: float
    ) -> int:
        """
        Вычисляет плавное движение с учетом штрафов за дрожание.
        
        Args:
            current_x: Текущая позиция платформы.
            optimal_x: Оптимальная позиция платформы.
            distance: Расстояние до оптимальной позиции.
            
        Returns:
            Направление движения (-1, 0, 1).
        """
        # КРИТИЧНО: Проверяем, находится ли мяч в зоне разделения с установленной позицией
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if self.current_game_state and hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        # КРИТИЧНО: Если целевая позиция установлена, используем увеличенный допуск
        # Когда мяч движется точно вниз по известной траектории, платформа должна оставаться на месте
        if self.separation_zone_tracker.target_position_set:
            # Увеличенный допуск для предотвращения дрожания в зоне разделения
            effective_min_distance = 30  # Увеличенный допуск 30 пикселей для стабильности
        else:
            # Если есть штраф за дрожание, увеличиваем порог для движения
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (
                1 + penalty
            )

        if distance < effective_min_distance:
            # Не двигаемся, если расстояние слишком мало (с учетом штрафа или зоны разделения)
            # КРИТИЧНО: Это предотвращает уход платформы с траектории мяча
            return 0

        # Определяем направление движения
        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0
