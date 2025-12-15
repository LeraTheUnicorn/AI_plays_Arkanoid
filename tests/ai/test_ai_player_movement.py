"""
Тесты для модуля ai_player_movement.py
"""

import pytest
from unittest.mock import Mock, patch
from ai.ai_player_movement import AIPlayerMovementMixin
from ai.game_state import GameState, Point


class TestAIPlayerMovementMixin:
    """Тесты для миксина AIPlayerMovementMixin."""
    
    def test_calculate_adaptive_paddle_speed_no_state(self):
        """Тест расчета скорости без состояния игры."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = None
        
        player = TestPlayer()
        speed = player.calculate_adaptive_paddle_speed(400, 450, 5)
        
        assert isinstance(speed, int)
        assert 35 <= speed <= 60
    
    def test_calculate_adaptive_paddle_speed_small_distance(self):
        """Тест расчета скорости для малого расстояния."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 500),
                    ball_velocity=Point(5, 5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        
        # Малое расстояние
        speed = player.calculate_adaptive_paddle_speed(400, 403, 5)
        
        assert isinstance(speed, int)
        assert speed >= 35  # Минимальная скорость
    
    def test_calculate_adaptive_paddle_speed_large_distance(self):
        """Тест расчета скорости для большого расстояния."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 500),
                    ball_velocity=Point(5, 5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        
        # Большое расстояние
        speed = player.calculate_adaptive_paddle_speed(100, 600, 5)
        
        assert isinstance(speed, int)
        assert speed >= 35
    
    def test_calculate_adaptive_paddle_speed_ball_moving_towards(self):
        """Тест расчета скорости когда мяч движется к платформе."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 500),
                    ball_velocity=Point(5, 5),  # Движется вниз
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        
        speed = player.calculate_adaptive_paddle_speed(400, 450, 5)
        
        assert isinstance(speed, int)
        assert 35 <= speed <= 60
    
    def test_calculate_adaptive_paddle_speed_ball_not_moving_towards(self):
        """Тест расчета скорости когда мяч не движется к платформе."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 200),
                    ball_velocity=Point(5, -5),  # Движется вверх
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        player.is_ball_moving_towards_paddle = Mock(return_value=False)
        
        speed = player.calculate_adaptive_paddle_speed(400, 450, 5)
        
        assert isinstance(speed, int)
        assert 35 <= speed <= 60
    
    def test_calculate_adaptive_paddle_speed_different_ball_speeds(self):
        """Тест расчета скорости для разных скоростей мяча."""
        class TestPlayer(AIPlayerMovementMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 500),
                    ball_velocity=Point(5, 5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        
        # Медленный мяч
        speed_slow = player.calculate_adaptive_paddle_speed(400, 450, 3)
        
        # Быстрый мяч
        speed_fast = player.calculate_adaptive_paddle_speed(400, 450, 8)
        
        assert isinstance(speed_slow, int)
        assert isinstance(speed_fast, int)
        assert 35 <= speed_slow <= 60
        assert 35 <= speed_fast <= 60

