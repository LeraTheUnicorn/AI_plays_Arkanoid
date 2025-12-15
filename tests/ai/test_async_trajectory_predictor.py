"""
Тесты для модуля async_trajectory_predictor.py
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from ai.async_trajectory_predictor import AsyncTrajectoryPredictor
from ai.game_state import GameState, Point


class TestAsyncTrajectoryPredictor:
    """Тесты для класса AsyncTrajectoryPredictor."""
    
    def test_init(self):
        """Тест инициализации AsyncTrajectoryPredictor."""
        predictor = AsyncTrajectoryPredictor(800, 600, max_workers=2)
        
        assert predictor.trajectory_predictor is not None
        assert predictor.trajectory_predictor.screen_width == 800
        assert predictor.trajectory_predictor.screen_height == 600
        assert predictor.executor is not None
    
    def test_init_default_workers(self):
        """Тест инициализации с количеством воркеров по умолчанию."""
        predictor = AsyncTrajectoryPredictor(800, 600)
        
        assert predictor.executor is not None
        assert predictor.trajectory_predictor is not None
    
    @pytest.mark.asyncio
    async def test_predict_trajectory_async(self):
        """Тест асинхронного предсказания траектории."""
        predictor = AsyncTrajectoryPredictor(800, 600, max_workers=2)
        
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        # Асинхронный вызов
        trajectory = await predictor.predict_trajectory_async(state, max_points=10)
        
        assert isinstance(trajectory, list)
        assert len(trajectory) > 0
        assert all(isinstance(point, Point) for point in trajectory)
    
    def test_predict_trajectory_sync(self):
        """Тест синхронного предсказания траектории."""
        predictor = AsyncTrajectoryPredictor(800, 600, max_workers=2)
        
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        trajectory = predictor.predict_trajectory(state, max_points=10)
        
        assert isinstance(trajectory, list)
        assert len(trajectory) > 0
    
    @pytest.mark.asyncio
    async def test_predict_paddle_intersection_async(self):
        """Тест асинхронного поиска точки пересечения."""
        predictor = AsyncTrajectoryPredictor(800, 600, max_workers=2)
        
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
        
        intersection = await predictor.predict_paddle_intersection_async(state, 550.0)
        
        # Может быть None, но если есть значение, должно быть Point
        if intersection is not None:
            assert isinstance(intersection, Point)
    
    def test_shutdown(self):
        """Тест корректного завершения работы."""
        predictor = AsyncTrajectoryPredictor(800, 600, max_workers=2)
        
        # Не должно быть исключений
        predictor.shutdown()
        
        # Повторный вызов тоже должен работать
        predictor.shutdown()

