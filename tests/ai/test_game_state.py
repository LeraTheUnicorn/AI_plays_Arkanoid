"""
Тесты для модуля game_state.py
"""

import pytest
import pygame
from ai.game_state import GameState, Point


class TestPoint:
    """Тесты для класса Point."""
    
    def test_point_creation(self):
        """Тест создания точки."""
        point = Point(10, 20)
        assert point.x == 10
        assert point.y == 20
    
    def test_point_addition(self):
        """Тест сложения точек."""
        p1 = Point(1, 2)
        p2 = Point(3, 4)
        result = p1 + p2
        assert result.x == 4
        assert result.y == 6
    
    def test_point_subtraction(self):
        """Тест вычитания точек."""
        p1 = Point(5, 7)
        p2 = Point(2, 3)
        result = p1 - p2
        assert result.x == 3
        assert result.y == 4
    
    def test_point_multiplication(self):
        """Тест умножения точки на скаляр."""
        p = Point(2, 3)
        result = p * 2
        assert result.x == 4
        assert result.y == 6
    
    def test_point_distance(self):
        """Тест вычисления расстояния между точками."""
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        distance = p1.distance_to(p2)
        assert distance == 5.0  # 3-4-5 треугольник


class TestGameState:
    """Тесты для класса GameState."""
    
    def test_game_state_creation(self):
        """Тест создания состояния игры."""
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
        assert state.ball_position.x == 400
        assert state.ball_position.y == 300
        assert state.ball_velocity.x == 5
        assert state.ball_velocity.y == -5
        assert state.paddle_width == 120
        assert state.game_score == 0
    
    def test_is_ball_falling(self):
        """Тест проверки падения мяча."""
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),  # Движется вниз
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        assert state.is_ball_falling() is True
        
        state.ball_velocity = Point(5, -5)  # Движется вверх
        assert state.is_ball_falling() is False
    
    def test_get_ball_trajectory_direction(self):
        """Тест определения направления траектории."""
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
        assert state.get_ball_trajectory_direction() == "right"
        
        state.ball_velocity = Point(-5, -5)
        assert state.get_ball_trajectory_direction() == "left"
        
        state.ball_velocity = Point(0, -5)
        assert state.get_ball_trajectory_direction() == "vertical"
    
    def test_get_nearest_bricks(self, mock_bricks):
        """Тест получения ближайших кирпичей."""
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=mock_bricks,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        nearest = state.get_nearest_bricks(count=3)
        assert len(nearest) == 3
        assert all(isinstance(item, tuple) and len(item) == 2 for item in nearest)
    
    def test_get_paddle_intersection_point(self):
        """Тест вычисления точки пересечения с платформой."""
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),  # Движется вниз
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        intersection = state.get_paddle_intersection_point(550.0)
        assert intersection is not None
        assert intersection.y == 550.0
        
        # Мяч движется вверх - пересечения нет
        state.ball_velocity = Point(5, -5)
        intersection = state.get_paddle_intersection_point(550.0)
        assert intersection is None
    
    def test_update_from_result(self):
        """Тест обновления состояния из результата действия."""
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[pygame.Rect(100, 100, 60, 20)],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        result = {
            "success": True,
            "hit_bricks": [pygame.Rect(100, 100, 60, 20)]
        }
        state.update_from_result(result)
        
        assert state.game_score == 1
        assert len(state.remaining_bricks) == 0
        assert state.last_action_result == result
    
    def test_clone(self):
        """Тест клонирования состояния."""
        state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[pygame.Rect(100, 100, 60, 20)],
            game_score=10,
            game_time=100,
            ball_speed=5,
        )
        
        cloned = state.clone()
        assert cloned.ball_position.x == state.ball_position.x
        assert cloned.ball_position.y == state.ball_position.y
        assert cloned.game_score == state.game_score
        assert cloned is not state  # Разные объекты

