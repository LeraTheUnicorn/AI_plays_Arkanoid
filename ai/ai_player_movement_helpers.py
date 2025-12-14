"""
Модуль вспомогательных методов движения AIPlayer.

Содержит вспомогательные методы для выполнения и валидации движения платформы.
"""

import time
from typing import Optional


class AIPlayerMovementHelpersMixin:
    """Миксин для вспомогательных методов движения AIPlayer."""

    def _execute_movement_strategy(self, current_x: int, paddle_speed: int) -> int:
        """
        Выполняет стратегию движения платформы.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        # ТЕСТ: Логируем вызов стратегии
        self._logger.debug(f"[AI_PLAYER_MOVE] Вызываем paddle_movement_strategy.move_paddle_towards: current_x={current_x}, paddle_speed={paddle_speed}")
        # Обновляем current_game_state в стратегии
        self.paddle_movement_strategy.current_game_state = self.current_game_state
        result = self.paddle_movement_strategy.move_paddle_towards(current_x, paddle_speed)
        self._logger.debug(f"[AI_PLAYER_MOVE] paddle_movement_strategy вернул: {result}")
        return result

    def _validate_movement_conditions(self, current_x: int, paddle_speed: int) -> bool:
        """
        Проверяет условия для движения платформы.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            True, если движение возможно, False иначе.
        """
        if not self.current_game_state or not self.is_active:
            self._logger.debug(f"[PADDLE DEBUG] move_paddle_towards: current_game_state={self.current_game_state is not None}, is_active={self.is_active}")
            return False
        return True

    def _calculate_optimal_position(self) -> int:
        """
        Рассчитывает оптимальную позицию платформы.
        
        Returns:
            Оптимальная X-координата платформы.
        """
        # Получаем состояние мяча
        ball_y = self.current_game_state.ball_position.y
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        
        # КРИТИЧНО: Логируем состояние мяча для диагностики
        # Фильтрация по уровню выполняется автоматически системой логирования Python
        start_time_monitor = time.time() if self.performance_monitor else None
        optimal_x = self.get_optimal_paddle_position()
        current_x = int(self.current_game_state.paddle_position.x) if self.current_game_state else 0
        self._logger.debug(f"[PADDLE DEBUG] ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y}, current_x={current_x}, optimal_x={optimal_x}, distance={abs(current_x - optimal_x):.1f}")
        
        # Записываем метрику производительности перед возвратом
        if self.performance_monitor and start_time_monitor:
            duration = time.time() - start_time_monitor
            self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
        
        return optimal_x
