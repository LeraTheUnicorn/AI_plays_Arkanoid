"""
Тесты для модуля position_optimizer.py
"""

import pytest
from unittest.mock import Mock, MagicMock
from ai.position_optimizer import PositionOptimizer
from ai.game_state import GameState, Point


class TestPositionOptimizer:
    """Тесты для класса PositionOptimizer."""

    def test_init(self):
        """Тест инициализации PositionOptimizer."""
        optimizer = PositionOptimizer(800, 600)
        assert optimizer.screen_width == 800
        assert optimizer.screen_height == 600
        assert optimizer.paddle_safety_margin == 20

    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        optimizer = PositionOptimizer()
        assert optimizer.screen_width == 800
        assert optimizer.screen_height == 600

    def test_find_optimal_position_ball_falling(self):
        """Тест поиска оптимальной позиции для падающего мяча."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),  # Движется вниз
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        # Мокируем trajectory_predictor
        mock_predictor = Mock()
        mock_predictor.find_optimal_bounce_position.return_value = 400.0

        optimal_pos = optimizer.find_optimal_position(state, mock_predictor)

        assert isinstance(optimal_pos, (int, float))
        assert 0 <= optimal_pos <= 800

    def test_find_optimal_position_ball_rising(self):
        """Тест поиска оптимальной позиции для поднимающегося мяча."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 200),
            ball_velocity=Point(5, -5),  # Движется вверх
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        mock_predictor = Mock()
        optimal_pos = optimizer.find_optimal_position(state, mock_predictor)

        # Для поднимающегося мяча должна использоваться стратегия следования
        assert isinstance(optimal_pos, int)
        assert 0 <= optimal_pos <= 800

    def test_find_optimal_position_with_optimal_bounce(self):
        """Тест поиска позиции с оптимальным отскоком."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        mock_predictor = Mock()
        mock_predictor.find_optimal_bounce_position.return_value = 350.0

        optimal_pos = optimizer.find_optimal_position(state, mock_predictor)

        assert isinstance(optimal_pos, (int, float))
        # Позиция должна учитывать ширину платформы
        assert 0 <= optimal_pos <= 800

    def test_find_optimal_position_fallback(self):
        """Тест fallback стратегии при ошибке."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        # Мокируем predictor, который выбрасывает исключение
        mock_predictor = Mock()
        mock_predictor.find_optimal_bounce_position.side_effect = Exception(
            "Test error"
        )

        # Не должно быть исключения, должен использоваться fallback
        optimal_pos = optimizer.find_optimal_position(state, mock_predictor)

        assert isinstance(optimal_pos, int)
        assert 0 <= optimal_pos <= 800

    def test_follow_ball_position(self):
        """Тест стратегии следования за мячом."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(300, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        position = optimizer._follow_ball_position(state)

        assert isinstance(position, int)
        assert 0 <= position <= 800

    def test_follow_ball_position_rising_ball(self):
        """Тест следования за поднимающимся мячом."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 200),
            ball_velocity=Point(5, -5),  # Движется вверх
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        position = optimizer._follow_ball_position(state)

        assert isinstance(position, int)
        # Для поднимающегося мяча просто следуем за текущей позицией
        assert 0 <= position <= 800

    def test_bounce_x_to_paddle_x(self):
        """Тест преобразования X-координаты отскока в позицию платформы."""
        optimizer = PositionOptimizer(800, 600)

        bounce_x = 400.0
        paddle_width = 120

        # Используем метод через find_optimal_position, так как _bounce_x_to_paddle_x приватный
        # Создаем состояние, которое вызовет этот метод
        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=paddle_width,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        mock_predictor = Mock()
        mock_predictor.find_optimal_bounce_position.return_value = bounce_x

        paddle_x = optimizer.find_optimal_position(state, mock_predictor)

        # Может быть int или float
        assert isinstance(paddle_x, (int, float))
        assert 0 <= paddle_x <= 800

    def test_bounce_x_to_paddle_x_edge_cases(self):
        """Тест преобразования для крайних случаев."""
        optimizer = PositionOptimizer(800, 600)

        # Тестируем через find_optimal_position с разными значениями отскока
        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        mock_predictor = Mock()

        # Левая граница
        mock_predictor.find_optimal_bounce_position.return_value = 0.0
        paddle_x_left = optimizer.find_optimal_position(state, mock_predictor)
        assert paddle_x_left >= 0

        # Правая граница
        mock_predictor.find_optimal_bounce_position.return_value = 800.0
        paddle_x_right = optimizer.find_optimal_position(state, mock_predictor)
        assert paddle_x_right <= 800

        # Центр
        mock_predictor.find_optimal_bounce_position.return_value = 400.0
        paddle_x_center = optimizer.find_optimal_position(state, mock_predictor)
        assert 0 <= paddle_x_center <= 800

    def test_fallback_position(self):
        """Тест fallback позиции."""
        optimizer = PositionOptimizer(800, 600)

        state = GameState(
            ball_position=Point(400, 500),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        position = optimizer._fallback_position(state)

        assert isinstance(position, int)
        assert 0 <= position <= 800
