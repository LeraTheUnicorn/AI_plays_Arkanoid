"""
Модуль оптимизации позиций AIPlayer (часть 1).

Содержит методы для расчета оптимальной позиции платформы и принудительного прицеливания.
"""

import math
import time
from typing import Optional, Any

from .exceptions import InvalidStateError, PredictionError


class AIPlayerPositionOptimizationPart1Mixin:
    """Миксин для методов оптимизации позиций AIPlayer (часть 1)."""

    def get_optimal_paddle_position(self) -> int:
        """
        Получает оптимальную позицию центра платформы
        с прицельным отбиванием по кубикам.
        
        ВАЖНО: Всегда пересчитывает цель, если мяч движется вверх или меняет направление,
        чтобы учесть отскок от верхней границы.
        """
        start_time_monitor = time.time() if self.performance_monitor else None
        if not self.current_game_state or not self.is_active:
            # Резервная позиция — центр экрана
            result = self.screen_width // 2
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
            return result

        try:
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            ball_x = self.current_game_state.ball_position.x
            
            # КРИТИЧНО: Обновляем отслеживание направления мяча для обнаружения изменений направления
            # Это позволяет пересчитывать целевую позицию при смене направления движения мяча
            self.separation_zone_tracker.last_ball_vel_y = ball_vel_y

            # Рассчитываем зоны
            zones = self.zone_handler.calculate_zones()
            separation_zone_start = zones["separation_zone_start"]
            paddle_zone_start = zones["paddle_zone_start"]

            # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ (Задача 1): Если мяч в зоне разделения, вычисляем предсказанную позицию приземления
            # Это исправляет проблему, когда get_optimal_paddle_position() возвращает текущую позицию платформы
            # вместо предсказанной позиции приземления
            in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

            if in_separation_zone:
                # КРИТИЧНО: Вычисляем предсказанную позицию приземления, а не возвращаем текущую позицию
                intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                    self.current_game_state,
                    self.current_game_state.paddle_position.y
                )
                
                if intersection_point is None:
                    # Если предсказание невозможно, используем fallback
                    landing_x = self._predict_exact_landing_position()
                else:
                    landing_x = intersection_point.x
                
                # Обновляем отслеживание позиции мяча при расчете цели
                if not hasattr(self, '_last_target_ball_x'):
                    self._last_target_ball_x = None
                self._last_target_ball_x = ball_x
                
                # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ V3: В зоне разделения используем предсказанную позицию напрямую
                # НЕ вызываем _calculate_target_position(), которая корректирует позицию для прицеливания в кирпичи
                # В зоне разделения нужно просто отбить мяч, а не прицеливаться в кирпичи
                # Просто ограничиваем границами экрана
                paddle_half_width = self.paddle_width // 2
                min_x = paddle_half_width
                max_x = self.screen_width - paddle_half_width
                optimal_position = max(min_x, min(max_x, int(landing_x)))
                
                self._logger.debug(
                    f"[OPTIMAL POSITION] Мяч в зоне разделения (y={ball_y:.1f}), "
                    f"предсказанная позиция приземления: {landing_x:.1f}px, "
                    f"целевая позиция (без коррекции для прицеливания): {optimal_position:.1f}px"
                )
                if self.performance_monitor and start_time_monitor:
                    duration = time.time() - start_time_monitor
                    self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
                return optimal_position

            # Если мяч в зоне кубиков - платформа НЕ должна двигаться
            if ball_y < separation_zone_start:
                result = self.zone_handler.handle_bricks_zone(ball_y, self.current_game_state)
                if self.performance_monitor and start_time_monitor:
                    duration = time.time() - start_time_monitor
                    self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
                return result
            
            # Обрабатываем зону разделения (для других случаев, когда мяч не в зоне разделения)
            separation_result = self.zone_handler.handle_separation_zone(ball_y, ball_vel_y, zones, self.current_game_state)
            if separation_result is not None:
                if self.performance_monitor and start_time_monitor:
                    duration = time.time() - start_time_monitor
                    self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
                return separation_result

            # Мяч ниже кубиков и движется вниз/в разделительной зоне — считаем прицельную позицию
            if ball_y < paddle_zone_start:
                # КРИТИЧНО: Используем predict_paddle_intersection для правильной обработки отскоков
                # Это учитывает отскоки от верхней границы и блоков
                intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                    self.current_game_state,
                    self.current_game_state.paddle_position.y
                )
                
                if intersection_point is None:
                    # Если предсказание невозможно, используем fallback
                    landing_x = self._predict_exact_landing_position()
                else:
                    landing_x = intersection_point.x
                
                # Обновляем отслеживание позиции мяча при расчете цели
                if not hasattr(self, '_last_target_ball_x'):
                    self._last_target_ball_x = None
                self._last_target_ball_x = ball_x
                
                return self._calculate_target_position(landing_x, ball_y, zones)
            else:
                # Мяч движется вверх — обрабатываем возможный отскок от потолка
                # self.current_game_state гарантированно не None (проверено на строке 1507)
                current_x = int(self.current_game_state.paddle_position.x)
                return self.zone_handler.handle_upward_movement(ball_y, self.current_game_state, current_x)

        except (AttributeError, TypeError) as e:
            self._logger.error(f"Ошибка типов при расчете оптимальной позиции: {e}", exc_info=True)
            if self.current_game_state and hasattr(self.current_game_state, "paddle_position"):
                return int(self.current_game_state.paddle_position.x)
            return self.screen_width // 2
        except InvalidStateError as e:
            self._logger.error(f"Недопустимое состояние при расчете позиции: {e}", exc_info=True)
            return self.screen_width // 2
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при расчете позиции: {e}", exc_info=True)
            if self.current_game_state and hasattr(self.current_game_state, "paddle_position"):
                return int(self.current_game_state.paddle_position.x)
            return self.screen_width // 2

    def _force_target_brick_from_coordinates(self, landing_x: float) -> Optional[float]:
        """
        Принудительно находит позицию платформы для прицеливания в блок, используя координаты из brick_coordinates.
        Используется когда обычные методы не находят позицию, но координаты блоков известны.
        
        Args:
            landing_x: X-координата приземления мяча
            
        Returns:
            Оптимальная X-координата центра платформы или None
        """
        if not self.current_game_state:
            return None
        
        brick_coordinates = self.targeting_system.brick_coordinates
        if not brick_coordinates:
            # КРИТИЧНО: Если координаты не загружены, используем remaining_bricks напрямую
            if self.current_game_state and self.current_game_state.remaining_bricks:
                # Создаем координаты из remaining_bricks
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
        
        # Получаем точку пересечения с платформой
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        best_position: Optional[float] = None
        best_score = -float("inf")
        
        # КРИТИЧНО: Сортируем кубики по приоритету (ближайшие и нижние получают больший приоритет)
        sorted_bricks = sorted(
            brick_coordinates,
            key=lambda b: (
                -b.get("y", 0),  # Нижние кубики в приоритете (больше Y = ниже)
                abs(b.get("x", 0) - landing_x)  # Ближе к траектории приземления
            )
        )
        
        # Для каждого блока из координат рассчитываем позицию
        for brick_info in sorted_bricks[:10]:  # Проверяем только первые 10 приоритетных кубиков
            brick_x = brick_info.get("x", 0)
            brick_y = brick_info.get("y", 0)
            brick_obj = brick_info.get("brick")
            
            if brick_obj is None:
                continue
            
            brick_width = getattr(brick_obj, "width", self.config.brick.default_width)
            brick_height = getattr(brick_obj, "height", 20)
            brick_center_x = brick_x  # brick_x уже центр кубика из координат
            brick_center_y = brick_y
            
            # Расстояние от платформы до блока
            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y
            
            if dy <= 0:
                continue  # Блок выше платформы
            
            # КРИТИЧНО: Рассчитываем необходимое смещение для попадания в блок
            # Используем более агрессивную формулу для гарантированного попадания
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))  # Более агрессивное смещение
            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x
            
            # Ограничиваем границами
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))
            
            # Симулируем траекторию для проверки попадания
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Проверяем попадание
            will_hit = False
            ball_radius = self.config.ball.radius
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue
                
                # Более широкая проверка попадания
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    break
            
            if will_hit:
                # Оцениваем качество позиции
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)
                
                if brick_y > 200:  # Нижние блоки
                    score += 5000.0
                
                # Бонус за близость к текущей позиции платформы (меньше движения = лучше)
                current_paddle_x = self.current_game_state.paddle_position.x
                movement_distance = abs(paddle_position - current_paddle_x)
                score -= movement_distance * 0.1  # Небольшой штраф за большое движение
                
                if score > best_score:
                    best_score = score
                    best_position = paddle_position
        
        # Если нашли позицию, возвращаем её
        if best_position is not None:
            return float(best_position)
        
        # Fallback: используем ближайший блок по координатам
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
        Используется на поздних этапах игры (<= 15 блоков).
        
        Args:
            landing_x: X-координата приземления мяча.
            
        Returns:
            Оптимальная X-координата центра платформы или None.
        """
        if not self.current_game_state:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        # Тестируем различные углы удара (смещения на платформе)
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0
        
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        for offset in test_offsets:
            # Вычисляем позицию отскока на платформе
            bounce_x = landing_x - (offset * paddle_half_width)
            
            # Ограничиваем границами платформы
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Подсчитываем количество блоков, которые будут разрушены
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            # Если это лучший результат, сохраняем
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset
        
        # Вычисляем оптимальную позицию платформы
        optimal_position = landing_x - (best_offset * paddle_half_width)
        
        # Границы по центру платформы
        min_position = paddle_half_width
        max_position = self.screen_width - paddle_half_width
        optimal_position = max(min_position, min(max_position, optimal_position))
        
        return optimal_position
