"""
Тесты для модуля ai_player_position_optimization_part1.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_position_optimization_part1 import AIPlayerPositionOptimizationPart1Mixin
from ai.game_state import GameState, Point


class TestAIPlayerPositionOptimizationPart1Mixin:
    """Тесты для миксина AIPlayerPositionOptimizationPart1Mixin."""
    
    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type('TestPlayer', (AIPlayerPositionOptimizationPart1Mixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player.is_active = True
        player.performance_monitor = None
        player._logger = Mock()
        player._predict_exact_landing_position = Mock(return_value=400.0)
        player._calculate_target_position = Mock(return_value=400)
        
        # Zone handler
        player.zone_handler = Mock()
        player.zone_handler.calculate_zones = Mock(return_value={
            "separation_zone_start": 250.0,
            "paddle_zone_start": 540.0
        })
        player.zone_handler.handle_bricks_zone = Mock(return_value=400)
        player.zone_handler.handle_separation_zone = Mock(return_value=None)
        player.zone_handler.handle_upward_movement = Mock(return_value=400)
        
        # Trajectory predictor
        player.trajectory_predictor = Mock()
        player.trajectory_predictor.predict_paddle_intersection = Mock(return_value=Point(400, 550))
        
        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.last_ball_vel_y = 5.0
        
        return player
    
    def test_get_optimal_paddle_position_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player.get_optimal_paddle_position()
        
        assert result == 400  # screen_width // 2
    
    def test_get_optimal_paddle_position_not_active(self):
        """Тест когда AI не активен."""
        player = self._create_mock_player()
        player.is_active = False
        
        result = player.get_optimal_paddle_position()
        
        assert result == 400  # screen_width // 2
    
    def test_get_optimal_paddle_position_in_separation_zone(self):
        """Тест когда мяч в зоне разделения."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.trajectory_predictor.predict_paddle_intersection.return_value = Point(450, 550)
        
        result = player.get_optimal_paddle_position()
        
        assert isinstance(result, int)
        assert 60 <= result <= 740  # В пределах экрана
    
    def test_get_optimal_paddle_position_in_bricks_zone(self):
        """Тест когда мяч в зоне кубиков."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 200),
            ball_velocity=Point(5, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.zone_handler.handle_bricks_zone.return_value = 400
        
        result = player.get_optimal_paddle_position()
        
        assert result == 400
    
    def test_force_target_brick_from_coordinates_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player._force_target_brick_from_coordinates(400.0)
        
        assert result is None
    
    def test_force_target_brick_from_coordinates_no_brick_coordinates(self):
        """Тест когда нет координат кубиков."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.targeting_system = Mock()
        player.targeting_system.brick_coordinates = []
        
        result = player._force_target_brick_from_coordinates(400.0)
        
        assert result is None
    
    def test_force_target_brick_from_coordinates_with_bricks(self):
        """Тест с координатами кубиков."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60
        mock_brick.height = 20
        
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[mock_brick],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.targeting_system = Mock()
        player.targeting_system.brick_coordinates = [{
            "x": 330,
            "y": 200,
            "brick": mock_brick
        }]
        player.trajectory_predictor.predict_paddle_intersection.return_value = Point(400, 550)
        player.trajectory_predictor.predict_after_bounce_trajectory = Mock(return_value=[
            Point(300, 200)
        ])
        player.config = Mock()
        player.config.ball = Mock()
        player.config.ball.radius = 8
        
        result = player._force_target_brick_from_coordinates(400.0)
        
        assert result is not None
        assert isinstance(result, float)
    
    def test_calculate_position_for_max_destruction_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player._calculate_position_for_max_destruction(400.0)
        
        assert result is None
    
    def test_calculate_position_for_max_destruction_with_bricks(self):
        """Тест расчета позиции для максимизации разрушений."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60
        mock_brick.height = 20
        
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[mock_brick],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.trajectory_predictor.predict_paddle_intersection.return_value = Point(400, 550)
        player.trajectory_predictor.predict_after_bounce_trajectory = Mock(return_value=[
            Point(300, 200)
        ])
        player._count_bricks_in_trajectory = Mock(return_value=1)
        player.config = Mock()
        player.config.ball = Mock()
        player.config.ball.radius = 8
        
        result = player._calculate_position_for_max_destruction(400.0)
        
        assert result is not None
        assert isinstance(result, float)

