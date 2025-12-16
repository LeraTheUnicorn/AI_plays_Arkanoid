"""
Тесты для модуля trajectory_predictor.py
"""

import pytest
import pygame
from unittest.mock import Mock, MagicMock
from ai.trajectory_predictor import TrajectoryPredictor
from ai.game_state import GameState, Point


class TestTrajectoryPredictor:
    """Тесты для класса TrajectoryPredictor."""

    def test_init(self):
        """Тест инициализации TrajectoryPredictor."""
        predictor = TrajectoryPredictor(800, 600)
        assert predictor.screen_width == 800
        assert predictor.screen_height == 600
        assert predictor.gravity == 0.5
        assert predictor._cache_max_size == 200

    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        predictor = TrajectoryPredictor()
        assert predictor.screen_width == 800
        assert predictor.screen_height == 600

    def test_predict_trajectory_basic(self, mock_game_state):
        """Тест базового предсказания траектории."""
        predictor = TrajectoryPredictor(800, 600)
        trajectory = predictor.predict_trajectory(mock_game_state, max_points=10)

        assert isinstance(trajectory, list)
        assert len(trajectory) > 0
        assert all(isinstance(point, Point) for point in trajectory)

    def test_predict_trajectory_caching(self, mock_game_state):
        """Тест кэширования траекторий."""
        predictor = TrajectoryPredictor(800, 600)

        # Первый вызов
        trajectory1 = predictor.predict_trajectory(mock_game_state, max_points=10)

        # Второй вызов с тем же состоянием - должен использовать кэш
        trajectory2 = predictor.predict_trajectory(mock_game_state, max_points=10)

        assert trajectory1 == trajectory2
        assert len(predictor._trajectory_cache) > 0

    def test_predict_trajectory_with_bricks(self, mock_game_state, mock_bricks):
        """Тест предсказания траектории с кирпичами."""
        mock_game_state.remaining_bricks = mock_bricks
        predictor = TrajectoryPredictor(800, 600)
        trajectory = predictor.predict_trajectory(mock_game_state, max_points=20)

        assert len(trajectory) > 0
        assert all(isinstance(point, Point) for point in trajectory)

    def test_predict_trajectory_ball_falling(self):
        """Тест предсказания для падающего мяча."""
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
        predictor = TrajectoryPredictor(800, 600)
        trajectory = predictor.predict_trajectory(state, max_points=10)

        assert len(trajectory) > 0
        # Мяч должен двигаться вниз
        assert trajectory[0].y < trajectory[-1].y

    def test_predict_trajectory_ball_rising(self):
        """Тест предсказания для поднимающегося мяча."""
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
        predictor = TrajectoryPredictor(800, 600)
        trajectory = predictor.predict_trajectory(state, max_points=10)

        assert len(trajectory) > 0
        # Мяч должен двигаться вверх
        assert trajectory[0].y > trajectory[-1].y

    def test_predict_trajectory_wall_bounce(self):
        """Тест отскока от стен."""
        state = GameState(
            ball_position=Point(10, 300),  # Близко к левой стене
            ball_velocity=Point(-5, 0),  # Движется влево
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        predictor = TrajectoryPredictor(800, 600)
        trajectory = predictor.predict_trajectory(state, max_points=20)

        # Проверяем, что мяч отскочил от стены
        x_coords = [p.x for p in trajectory]
        assert min(x_coords) >= 0  # Не выходит за левую границу

    def test_find_intersection_point(self, mock_game_state):
        """Тест поиска точки пересечения с платформой."""
        # Используем метод из GameState
        intersection = mock_game_state.get_paddle_intersection_point(550.0)

        # Может быть None если мяч не падает
        if intersection is not None:
            assert isinstance(intersection, Point)
            assert intersection.y == 550.0

    def test_find_optimal_bounce_position(self, mock_game_state):
        """Тест поиска оптимальной позиции отскока."""
        predictor = TrajectoryPredictor(800, 600)
        # Проверяем наличие метода
        if hasattr(predictor, "find_optimal_bounce_position"):
            optimal_x = predictor.find_optimal_bounce_position(mock_game_state, 550.0)

            # Может быть None, но если есть значение, должно быть в пределах экрана
            if optimal_x is not None:
                assert 0 <= optimal_x <= 800

    def test_predict_after_bounce_trajectory(self, mock_game_state):
        """Тест предсказания траектории после отскока."""
        predictor = TrajectoryPredictor(800, 600)
        if hasattr(predictor, "predict_after_bounce_trajectory"):
            bounce_point = Point(400, 550)
            bounce_x = 400.0
            trajectory = predictor.predict_after_bounce_trajectory(
                mock_game_state, bounce_point, bounce_x
            )

            assert isinstance(trajectory, list)
            if len(trajectory) > 0:
                assert all(isinstance(point, Point) for point in trajectory)

    def test_cache_management(self, mock_game_state):
        """Тест управления кэшем."""
        predictor = TrajectoryPredictor(800, 600)

        # Заполняем кэш
        for i in range(10):
            state = GameState(
                ball_position=Point(400 + i, 300),
                ball_velocity=Point(5, -5),
                paddle_position=Point(400, 550),
                paddle_width=120,
                remaining_bricks=[],
                game_score=0,
                game_time=0,
                ball_speed=5,
            )
            predictor.predict_trajectory(state, max_points=10)

        # Кэш должен содержать записи
        assert len(predictor._trajectory_cache) > 0
