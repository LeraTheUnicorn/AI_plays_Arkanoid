"""
Модуль для расчета позиций платформы в AIPlayer.
Содержит методы расчета оптимальных позиций, предсказания траекторий и обработки зон.
"""

import math
import random
from typing import Dict, Optional, Any

from .exceptions import PredictionError


class AIPlayerPositioningMixin:
    """
    Миксин для методов расчета позиций платформы.
    Добавляет методы расчета оптимальных позиций, предсказания траекторий и обработки зон.
    """
    
    def _predict_exact_landing_position(self) -> float:
        """
        Точное предсказание X-координаты, где мяч встретится с платформой.
        ИСПРАВЛЕННАЯ ВЕРСИЯ с правильным расчетом отскоков от стен.
        """
        if not self.current_game_state:
            return self.screen_width / 2.0
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y

        if vel_y <= 0:
            return ball_x

        ball_radius = self.config.ball.radius
        paddle_height = 15
        screen_width = self.screen_width
        
        paddle_top = paddle_y - paddle_height / 2
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return ball_x

        time_to_paddle = distance_y / vel_y
        if time_to_paddle <= 0:
            return ball_x

        current_x = ball_x
        current_vel_x = vel_x
        remaining_time = time_to_paddle
        min_center_x = ball_radius
        max_center_x = screen_width - ball_radius
        
        while remaining_time > 0 and abs(current_vel_x) > 0.001:
            new_x = current_x + current_vel_x * remaining_time
            
            if new_x < min_center_x:
                time_to_wall = (min_center_x - current_x) / current_vel_x if current_vel_x < 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = min_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            elif new_x > max_center_x:
                time_to_wall = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = max_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            else:
                current_x = new_x
                break

        min_x = self.paddle_width // 2
        max_x = screen_width - self.paddle_width // 2
        return max(min_x, min(max_x, current_x))

    def _handle_ceiling_bounce_positioning(self) -> int:
        """
        Специальная логика для позиционирования при отскоке мяча от потолка.
        Предотвращает симметричные отскоки и зацикливание.
        """
        if not self.current_game_state:
            return self.screen_width // 2
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y

        if ball_y < 30 and vel_y > 0:
            if abs(vel_x) < 2:
                remaining_bricks = self.targeting_system.brick_coordinates
                if remaining_bricks:
                    avg_brick_x = sum(c["x"] for c in remaining_bricks) / len(remaining_bricks)
                    target_x = (ball_x + avg_brick_x) / 2.0
                else:
                    center_x = self.screen_width // 2
                    target_x = center_x + (ball_x - center_x) * 0.3
            else:
                target_x = ball_x + vel_x * 2.0

            target_x += random.choice([-15, -10, 0, 10, 15])

            paddle_half_width = self.paddle_width / 2
            min_x = paddle_half_width + 5
            max_x = self.screen_width - paddle_half_width - 5
            target_x = max(min_x, min(max_x, target_x))
            return int(target_x)

        return int(self._track_ball_position())

    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с небольшим упреждением."""
        if not self.current_game_state:
            return self.screen_width / 2.0
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        vel_x = game_state.ball_velocity.x

        prediction_time = 3
        predicted_x = ball_x + vel_x * prediction_time

        screen_width = self.screen_width
        ball_radius = self.config.ball.radius
        min_x = ball_radius
        max_x = screen_width - ball_radius

        return max(min_x, min(max_x, predicted_x))

    def _calculate_precise_position_for_few_bricks(
        self, landing_x: float
    ) -> Optional[float]:
        """
        Вычисляет точную позицию платформы для попадания в оставшиеся блоки (1-10 блоков).
        КРИТИЧНО: При 1 кубике использует максимально агрессивное прицеливание.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        bricks_count = len(bricks)

        if bricks_count > 10:
            return None
        
        is_critical = bricks_count == 1

        # КРИТИЧНО: Для последнего кирпича используем специальную логику с максимальным приоритетом
        if is_critical:
            brick = bricks[0]
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x + brick_width / 2
            
            self._logger.warning(
                f"[LAST BRICK PRECISION] КРИТИЧНО: Расчет позиции для ПОСЛЕДНЕГО кирпича! "
                f"brick=({brick_x:.0f}, {brick_y:.0f}), center_x={brick_center_x:.0f}"
            )

        paddle_y = self.current_game_state.paddle_position.y
        paddle_half_width = self.paddle_width / 2

        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )

        if intersection_point is None:
            return None

        best_position = None
        best_score = -float("inf")

        # КРИТИЧНО: Для последнего кирпича увеличиваем приоритет точности
        critical_multiplier = 10.0 if is_critical else 1.0

        for brick in bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x + brick_width / 2
            brick_center_y = brick_y + brick_height / 2

            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y

            if dy <= 0:
                continue

            target_angle = math.atan2(dx, dy)
            max_angle = math.atan2(paddle_half_width, 50)
            normalized_angle = max(-max_angle, min(max_angle, target_angle))
            required_offset = normalized_angle / max_angle if max_angle > 0 else 0

            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x

            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))

            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )

            will_hit = False
            hit_confidence = 0.0
            ball_radius = self.config.ball.radius
            
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue

                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    center_x = brick_x + brick_width / 2
                    center_y = brick_y + brick_height / 2
                    distance_to_center = math.sqrt(
                        (point.x - center_x) ** 2 + (point.y - center_y) ** 2
                    )
                    max_distance = math.sqrt((brick_width / 2 + ball_radius) ** 2 + (brick_height / 2 + ball_radius) ** 2)
                    hit_confidence = max(hit_confidence, 1.0 - (distance_to_center / max_distance))
                    break

            if is_critical and not will_hit:
                min_distance_to_brick = float('inf')
                for point in after_bounce_trajectory:
                    if not hasattr(point, "x") or not hasattr(point, "y"):
                        continue
                    closest_x = max(brick_x, min(point.x, brick_x + brick_width))
                    closest_y = max(brick_y, min(point.y, brick_y + brick_height))
                    distance = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    min_distance_to_brick = min(min_distance_to_brick, distance)
                
                if min_distance_to_brick <= 30:
                    will_hit = True
                    hit_confidence = max(0.3, 1.0 - (min_distance_to_brick / 30.0))

            if will_hit:
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)

                if brick_y > 200:
                    score += 5000.0

                center_distance = abs(brick_center_x - self.screen_width // 2)
                score -= center_distance * 0.1
                
                # КРИТИЧНО: Для последнего кирпича максимально увеличиваем приоритет
                if is_critical:
                    score *= critical_multiplier  # Умножаем на 10 для максимального приоритета
                    score += hit_confidence * 50000.0
                    if hit_confidence > 0.2:
                        score += 100000.0
                    self._logger.warning(
                        f"[LAST BRICK SCORE] Позиция найдена! score={score:.0f}, "
                        f"hit_confidence={hit_confidence:.2f}, paddle_position={paddle_position:.0f}"
                    )

                if score > best_score:
                    best_score = score
                    best_position = paddle_position

        if best_position is None and bricks:
            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                brick_center_x = brick_x + brick_width / 2

                for test_offset in [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                    test_bounce_x = intersection_point.x - (test_offset * paddle_half_width)
                    test_paddle_position = test_bounce_x

                    min_position = paddle_half_width
                    max_position = self.screen_width - paddle_half_width
                    test_paddle_position = max(min_position, min(max_position, test_paddle_position))

                    test_trajectory = (
                        self.trajectory_predictor.predict_after_bounce_trajectory(
                            self.current_game_state, intersection_point, test_bounce_x
                        )
                    )

                    for point in test_trajectory:
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue

                        ball_radius = self.config.ball.radius
                        if (
                            brick_x - ball_radius <= point.x <= brick_x + brick_width + ball_radius
                            and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                        ):
                            best_position = test_paddle_position
                            break

                    if best_position is not None:
                        break

            if best_position is None:
                closest_brick = min(
                    bricks,
                    key=lambda b: (
                        paddle_y - getattr(b, "y", 0),
                        abs((getattr(b, "x", 0) + getattr(b, "width", 60) / 2) - landing_x),
                    ),
                )

                brick_center_x = getattr(closest_brick, "x", 0) + getattr(closest_brick, "width", 60) / 2

                if is_critical:
                    for test_offset_multiplier in [1.0, 1.2, 1.5, 2.0]:
                        dx = brick_center_x - landing_x
                        required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * test_offset_multiplier)))
                        test_position = landing_x - (required_offset * paddle_half_width)
                        
                        min_position = paddle_half_width
                        max_position = self.screen_width - paddle_half_width
                        test_position = max(min_position, min(max_position, test_position))
                        
                        if abs(test_position - landing_x) < self.screen_width:
                            best_position = test_position
                            break
                else:
                    dx = brick_center_x - landing_x
                    required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
                    best_position = landing_x - (required_offset * paddle_half_width)

                min_position = paddle_half_width
                max_position = self.screen_width - paddle_half_width
                if best_position is not None:
                    best_position = max(min_position, min(max_position, best_position))

        if best_position is None and bricks_count <= 10 and bricks:
            closest_brick = min(
                bricks,
                key=lambda b: (
                    paddle_y - getattr(b, "y", 0),
                    abs((getattr(b, "x", 0) + getattr(b, "width", 60) / 2) - landing_x),
                ),
            )
            
            brick_center_x = getattr(closest_brick, "x", 0) + getattr(closest_brick, "width", 60) / 2
            
            dx = brick_center_x - landing_x
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))

        return best_position

    def _force_target_brick_from_coordinates(self, landing_x: float) -> Optional[float]:
        """
        Принудительно находит позицию платформы для прицеливания в блок, используя координаты из brick_coordinates.
        """
        if not self.current_game_state:
            return None
        
        brick_coordinates = self.targeting_system.brick_coordinates
        if not brick_coordinates:
            if self.current_game_state and self.current_game_state.remaining_bricks:
                brick_coordinates = []
                for brick in self.current_game_state.remaining_bricks:
                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", self.config.brick.default_width)
                    brick_coordinates.append({
                        "x": brick_x + brick_width / 2,
                        "y": brick_y,
                        "brick": brick,
                    })
        
        if not brick_coordinates:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        paddle_half_width = self.paddle_width / 2
        
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        best_position: Optional[float] = None
        best_score = -float("inf")
        
        sorted_bricks = sorted(
            brick_coordinates,
            key=lambda b: (
                -b.get("y", 0),
                abs(b.get("x", 0) - landing_x)
            )
        )
        
        for brick_info in sorted_bricks[:10]:
            brick_x = brick_info.get("x", 0)
            brick_y = brick_info.get("y", 0)
            brick_obj = brick_info.get("brick")
            
            if brick_obj is None:
                continue
            
            brick_width = getattr(brick_obj, "width", self.config.brick.default_width)
            brick_height = getattr(brick_obj, "height", 20)
            brick_center_x = brick_x
            brick_center_y = brick_y

            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y
            
            if dy <= 0:
                continue

            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))
            
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            will_hit = False
            ball_radius = self.config.ball.radius
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue
                
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    break
            
            if will_hit:
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)
                
                if brick_y > 200:
                    score += 5000.0
                
                current_paddle_x = self.current_game_state.paddle_position.x
                movement_distance = abs(paddle_position - current_paddle_x)
                score -= movement_distance * 0.1
                
                if score > best_score:
                    best_score = score
                    best_position = paddle_position
        
        if best_position is not None:
            return float(best_position)
        
        if brick_coordinates:
            closest_brick = min(
                brick_coordinates,
                key=lambda b: (
                    paddle_y - b.get("y", 0),
                    abs(b.get("x", 0) - landing_x)
                )
            )
            
            brick_center_x = float(closest_brick.get("x", 0))
            dx = brick_center_x - landing_x
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))
            
            return float(best_position)
        
        return None

    def _calculate_position_for_max_destruction(
        self, landing_x: float
    ) -> Optional[float]:
        """
        Вычисляет оптимальную позицию платформы для максимизации разрушений в следующем цикле.
        """
        if not self.current_game_state:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_destruction_count = 0
        best_position = None
        
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        for offset in test_offsets:
            bounce_x = landing_x - (offset * paddle_half_width)
            
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_position = bounce_x
        
        if best_position is not None:
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            return max(min_position, min(max_position, best_position))
        
        return None
