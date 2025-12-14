"""
Модуль для работы с состоянием игры в AIPlayer.
Содержит методы обновления состояния, кэширования и адаптивных расчетов.
"""

import time
import logging
from typing import List, Optional, Dict, Any

from .game_state import GameState
from .exceptions import PredictionError


class AIPlayerStateMixin:
    """
    Миксин для методов работы с состоянием игры.
    Добавляет методы обновления состояния, кэширования и адаптивных расчетов.
    """
    
    def _invalidate_trajectory_cache(self, brick_changes: List[int]) -> None:
        """
        Инвалидировать кэш траекторий только для измененных блоков.
        
        Этот метод используется для оптимизации кэширования карты кирпичей.
        Когда изменяется состояние блоков (например, при destruction), этот метод
        позволяет инвалидировать только те записи кэша, которые связаны с измененными
        блоками, вместо полной перестройки всей карты.
        
        Args:
            brick_changes: Список идентификаторов измененных блоков (индексы в списке bricks)
                           Например, [3, 5, 7] означает, что изменились блоки с индексами 3, 5 и 7
                           в списке remaining_bricks текущего состояния игры.
        """
        if not brick_changes:
            return
        
        # Если изменены блоки, сбрасываем кэш карты кирпичей
        # Это гарантирует, что при следующем обновлении будет перестроена новая карта
        self._brick_map_cache = None
        
        # Сбрасываем статистику кэша
        self._brick_cache_stats = {
            "hits": 0,
            "misses": 0,
        }
        
        # Логируем инвалидацию кэша
        self._logger.debug(f"[CACHE INVALIDATION] Инвалидирован кэш карты кирпичей для {len(brick_changes)} измененных блоков")

    def update_game_state(
        self,
        ball: Any,
        paddle: Any,
        bricks: Any,
        score: int,
        start_time: int,
    ) -> None:
        """
        Обновляет состояние игры для AI-системы.

        Args:
            ball: Объект мяча из игры.
            paddle: Объект платформы из игры.
            bricks: Список оставшихся кубиков.
            score: Текущий счёт игрока.
            start_time: Время начала игры.

        Raises:
            ValueError: Если входные данные некорректны.
        """
        # Проверка входных данных
        if ball is None or paddle is None or bricks is None:
            raise ValueError("Ball, paddle и bricks не могут быть None")
        if score < 0:
            raise ValueError("Score не может быть отрицательным")
        if start_time < 0:
            raise ValueError("Start_time не может быть отрицательным")

        # Мониторинг производительности
        start_time_monitor = time.time() if self.performance_monitor else None
        
        # Создаём новое состояние игры
        self.current_game_state = GameState.create_from_game_objects(
            ball, paddle, bricks, score, start_time
        )
        
        # Адаптивная частота расчетов - пропускаем некоторые обновления когда мяч далеко
        if self._adaptive_calculation_enabled and self.current_game_state:
            should_skip = self._should_skip_calculation()
            if should_skip:
                # Пропускаем тяжелые расчеты, но обновляем базовое состояние
                if self.paddle_movement_strategy is not None:
                    self.paddle_movement_strategy.current_game_state = self.current_game_state
                return
        
        # Обновляем current_game_state в стратегии движения
        if self.paddle_movement_strategy is not None:
            self.paddle_movement_strategy.current_game_state = self.current_game_state

        # Инициализируем статистику игры, если это новая игра
        if self.current_game_stats["start_time"] is None:
            self.current_game_stats["start_time"] = start_time
            self.performance_logger.log_game_start(self.current_game_state)

        # Обновляем карту кубиков
        self._update_brick_map()

        # Логируем предсказание траектории, если включен debug-режим
        if self.debug_mode and self.is_ball_moving_towards_paddle():
            # Используем оптимизированную траекторию для логирования
            if self.performance_monitor:
                start_time = time.time()
            predicted_trajectory = self.trajectory_predictor.get_optimized_trajectory(
                self.current_game_state, max_relevant_points=40
            )
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.record_metric("trajectory_prediction", duration)
            self.performance_logger.log_trajectory_prediction(
                [{"x": p.x, "y": p.y} for p in predicted_trajectory]
            )
        
        # Обновляем время последнего расчета
        self._last_calculation_time = time.time()
        
        # Записываем метрику производительности
        if self.performance_monitor and start_time_monitor:
            duration = time.time() - start_time_monitor
            self.performance_monitor.record_metric("update_game_state", duration)

    def _should_skip_heavy_calculations(self) -> bool:
        """
        Уменьшить частоту тяжелых расчетов при стабильной траектории.
        
        Пропускает тяжелые расчеты если траектория стабильна (счетчик > 10).
        
        Returns:
            True, если нужно пропустить тяжелые расчеты, False иначе
        """
        if not self._adaptive_calculation_enabled:
            return False
        
        return self._trajectory_stability_counter > 10

    def _should_skip_calculation(self) -> bool:
        """
        Определяет, следует ли пропустить тяжелые расчеты на этом кадре.
        Использует адаптивную логику: пропускает расчеты когда мяч далеко от платформы.
        
        Returns:
            True, если расчеты можно пропустить, False иначе
        """
        if not self.current_game_state:
            return False
        
        ball_y = self.current_game_state.ball_position.y
        paddle_y = self.current_game_state.paddle_position.y
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        
        # Всегда выполняем расчеты если мяч движется к платформе и близко
        if ball_vel_y > 0:  # Мяч движется вниз
            distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
            
            # Если мяч очень близко (< 100px) - всегда рассчитываем
            if distance_to_paddle < 100:
                self._calculation_skip_counter = 0
                return False
            
            # Если мяч на среднем расстоянии (100-300px) - пропускаем каждый 2-й кадр
            if distance_to_paddle < 300:
                self._calculation_skip_counter += 1
                if self._calculation_skip_counter % 2 == 0:
                    return False
                return True
            
            # Если мяч далеко (> 300px) - пропускаем каждый 3-й кадр
            self._calculation_skip_counter += 1
            if self._calculation_skip_counter % 3 == 0:
                return False
            return True
        
        # Если мяч движется вверх - пропускаем чаще (каждый 2-й кадр)
        self._calculation_skip_counter += 1
        if self._calculation_skip_counter % 2 == 0:
            return False
        return True
    
    def _get_current_trajectory_prediction(self) -> Optional[Dict[str, Any]]:
        """Возвращает текущее предсказание траектории мяча (для логирования/обучения)."""
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            return None

        try:
            # Используем адаптивную траекторию для оптимизации
            ball_y = self.current_game_state.ball_position.y
            paddle_y = self.current_game_state.paddle_position.y
            trajectory = self.trajectory_predictor.get_adaptive_trajectory(
                self.current_game_state, ball_y, paddle_y
            )
            intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state,
                self.current_game_state.paddle_position.y,
            )
            return {
                "predicted_points": [{"x": p.x, "y": p.y} for p in trajectory],
                "intersection_point": intersection_point,
            }
        except (AttributeError, TypeError) as e:
            self._logger.warning(f"Ошибка типов при предсказании траектории: {e}", exc_info=True)
            return None
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания траектории: {e}", exc_info=True)
            return None
