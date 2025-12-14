"""
Модуль стратегий движения ракетки.

Содержит реализации различных стратегий движения ракетки,
использующих паттерн Strategy.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..game_state import GameState


class PaddleMovementStrategy(ABC):
    """Абстрактный класс стратегии движения ракетки."""

    @abstractmethod
    def calculate_movement(self, current_state: GameState) -> int:
        """
        Рассчитывает движение ракетки.

        Args:
            current_state: Текущее состояние игры

        Returns:
            Направление движения (-1, 0, 1)
        """
        pass


class AggressiveStrategy(PaddleMovementStrategy):
    """Агрессивная стратегия движения."""

    def calculate_movement(self, current_state: GameState) -> int:
        """
        Агрессивная логика движения.

        Расчитывает позицию для активного преследования мяча,
        стремясь к точному перехвату.

        Args:
            current_state: Текущее состояние игры

        Returns:
            Направление движения (-1, 0, 1)
        """
        if not current_state:
            return 0

        ball_x = current_state.ball_position.x
        paddle_x = current_state.paddle_position.x
        ball_vel_x = current_state.ball_velocity.x
        ball_vel_y = current_state.ball_velocity.y
        paddle_y = current_state.paddle_position.y

        # Если мяч падает вниз
        if ball_vel_y > 0:
            # Рассчитываем время до достижения платформы
            time_to_paddle = (paddle_y - current_state.ball_position.y) / ball_vel_y

            if time_to_paddle > 0:
                # Предсказываем позицию мяча при достижении платформы
                predicted_x = ball_x + ball_vel_x * time_to_paddle

                # Двигаемся к предсказанной позиции
                if predicted_x > paddle_x + 5:
                    return 1
                elif predicted_x < paddle_x - 5:
                    return -1

        # Если мяч движется вверх, готовимся к следующему удару
        elif ball_vel_y < 0:
            # Двигаемся к центру для лучшей подготовки
            screen_center = 400  # Примерное значение, должно быть передано в конструктор
            if paddle_x < screen_center - 20:
                return 1
            elif paddle_x > screen_center + 20:
                return -1

        return 0


class ConservativeStrategy(PaddleMovementStrategy):
    """Консервативная стратегия движения."""

    def calculate_movement(self, current_state: GameState) -> int:
        """
        Консервативная логика движения.

        Обеспечивает стабильное позиционирование,
        избегая рискованных движений.

        Args:
            current_state: Текущее состояние игры

        Returns:
            Направление движения (-1, 0, 1)
        """
        if not current_state:
            return 0

        ball_x = current_state.ball_position.x
        paddle_x = current_state.paddle_position.x
        ball_vel_y = current_state.ball_velocity.y

        # Консервативная стратегия: остаемся ближе к центру
        screen_center = 400  # Примерное значение, должно быть передано в конструктор
        center_tolerance = 50

        # Если мяч падает вниз и мы далеко от центра
        if ball_vel_y > 0:
            if paddle_x < screen_center - center_tolerance:
                return 1
            elif paddle_x > screen_center + center_tolerance:
                return -1
            else:
                # Остаемся в зоне комфорта
                if abs(ball_x - paddle_x) < 30:
                    return 0
                elif ball_x > paddle_x:
                    return 1
                else:
                    return -1

        # Если мяч движется вверх, возвращаемся к центру
        elif ball_vel_y < 0:
            if paddle_x < screen_center - 10:
                return 1
            elif paddle_x > screen_center + 10:
                return -1

        return 0
