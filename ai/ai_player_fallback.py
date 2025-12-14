"""
Модуль fallback логики AIPlayer.

Содержит методы для резервных стратегий движения и проверки временного давления.
"""

from typing import Dict, Any


class AIPlayerFallbackMixin:
    """Миксин для методов fallback логики AIPlayer."""

    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервная стратегия движения, когда основная логика не может определить оптимальную позицию.
        
        Args:
            current_x: Текущая X-координата платформы.
            
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state:
            return 0
        
        # Простое слежение за мячом
        ball_x = self.current_game_state.ball_position.x
        ball_vel_x = (
            self.current_game_state.ball_velocity.x
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        
        # Предсказываем позицию мяча через несколько кадров
        prediction_frames = 5
        predicted_ball_x = ball_x + ball_vel_x * prediction_frames
        
        # Ограничиваем границами экрана
        screen_center = self.screen_width // 2
        paddle_half_width = self.paddle_width / 2
        min_x = paddle_half_width
        max_x = self.screen_width - paddle_half_width
        
        # Нормализуем предсказанную позицию
        predicted_ball_x = max(min_x, min(max_x, predicted_ball_x))
        
        # Определяем направление движения
        distance = abs(current_x - predicted_ball_x)
        if distance < 10:
            return 0  # Уже на месте
        elif predicted_ball_x > current_x:
            return 1  # Движение вправо
        else:
            return -1  # Движение влево

    def _is_time_pressure(self) -> bool:
        """
        Проверяет, есть ли временное давление (мало времени или много блоков осталось).
        
        Returns:
            True, если есть временное давление.
        """
        if not self.current_game_state:
            return False
        
        bricks_count = len(self.current_game_state.remaining_bricks)
        
        # Временное давление возникает при большом количестве оставшихся блоков
        # или при малом количестве времени (если есть таймер)
        time_pressure_threshold = 30  # Блоков
        
        return bricks_count > time_pressure_threshold

    def _calculate_decision_confidence(self, target_position: int) -> float:
        """
        Рассчитывает уверенность в принятом решении о позиции платформы.
        
        Args:
            target_position: Целевая позиция платформы.
            
        Returns:
            Уверенность в решении (0.0-1.0).
        """
        if not self.current_game_state:
            return 0.5
        
        confidence = 0.7  # Базовая уверенность
        
        # Увеличиваем уверенность, если есть целевой кирпич
        if self.targeting_system.target_brick:
            confidence += 0.1
        
        # Увеличиваем уверенность, если позиция находится в безопасной зоне
        screen_center = self.screen_width // 2
        distance_from_center = abs(target_position - screen_center)
        safe_zone_size = self.screen_width * 0.3  # 30% экрана от центра
        
        if distance_from_center < safe_zone_size:
            confidence += 0.1
        
        # Уменьшаем уверенность при временном давлении
        if self._is_time_pressure():
            confidence -= 0.1
        
        # Ограничиваем диапазон
        return max(0.0, min(1.0, confidence))
