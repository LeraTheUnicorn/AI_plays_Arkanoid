"""
Тесты для модуля ai_player_ball_tracking.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_ball_tracking import AIPlayerBallTrackingMixin
from ai.game_state import GameState, Point


class TestAIPlayerBallTrackingMixin:
    """Тесты для миксина AIPlayerBallTrackingMixin."""
    
    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type('TestPlayer', (AIPlayerBallTrackingMixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player._logger = Mock()
        player._predict_exact_landing_position = Mock(return_value=400.0)
        
        # Target selector
        player.target_selector = Mock()
        player.target_selector.find_best_target_brick = Mock(return_value=None)
        
        # Targeting system
        player.targeting_system = Mock()
        player.targeting_system.target_brick = None
        player.targeting_system.optimal_offset = 0.0
        
        # Position calculator
        player.position_calculator = Mock()
        player.position_calculator.calculate_optimal_offset = Mock(return_value=0.5)
        
        # Loop prevention system
        player.loop_prevention_system = {
            "movement_history": [],
            "position_history": [],
            "trajectory_history": []
        }
        
        # Smoothness system
        player.smoothness_system = {
            "recent_movements": [],
            "movement_changes": [],
            "smoothness_penalty": 0.0
        }
        
        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.ball_entered_separation_zone = False
        player.separation_zone_tracker.target_position_set = False
        player.separation_zone_tracker.target_position = None
        player.separation_zone_tracker.paddle_moved_after_set = False
        player.separation_zone_tracker.paddle_reached_target = False
        player.separation_zone_tracker.last_movement_frame = 0
        
        # Config
        player.config = Mock()
        player.config.ball = Mock()
        player.config.ball.radius = 8
        
        # For calculate_adaptive_paddle_speed
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        
        return player
    
    def test_reevaluate_after_bounce_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        player._reevaluate_after_bounce()
        
        # Не должно вызвать ошибку
        assert True
    
    def test_reevaluate_after_bounce_with_target_brick(self):
        """Тест переоценки с целевым кубиком."""
        player = self._create_mock_player()
        mock_brick = Mock()
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
        player.target_selector.find_best_target_brick.return_value = mock_brick
        
        player._reevaluate_after_bounce()
        
        assert player.targeting_system.target_brick == mock_brick
        assert player.loop_prevention_system["movement_history"] == []
    
    def test_handle_ceiling_bounce_positioning_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player._handle_ceiling_bounce_positioning()
        
        assert result == 400  # screen_width // 2
    
    def test_handle_ceiling_bounce_positioning_vertical_bounce(self):
        """Тест позиционирования при вертикальном отскоке."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 20),
            ball_velocity=Point(1, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.targeting_system.brick_coordinates = [{"x": 300, "y": 200}]
        
        result = player._handle_ceiling_bounce_positioning()
        
        assert isinstance(result, int)
        assert 60 <= result <= 740
    
    def test_handle_ceiling_bounce_positioning_horizontal_velocity(self):
        """Тест позиционирования с горизонтальной скоростью."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 20),
            ball_velocity=Point(10, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        result = player._handle_ceiling_bounce_positioning()
        
        assert isinstance(result, int)
        assert 60 <= result <= 740
    
    def test_track_ball_position_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player._track_ball_position()
        
        assert result == 400.0  # screen_width / 2.0
    
    def test_track_ball_position_with_velocity(self):
        """Тест отслеживания с учетом скорости."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(10, -5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        result = player._track_ball_position()
        
        # Метод возвращает float, но может быть преобразован в int при ограничении
        assert isinstance(result, (float, int))
        assert 8 <= result <= 792  # В пределах экрана с учетом радиуса
    
    def test_calculate_adaptive_paddle_speed_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player.calculate_adaptive_paddle_speed(400, 400, 5)
        
        assert isinstance(result, int)
        assert 35 <= result <= 60
    
    def test_calculate_adaptive_paddle_speed_close_to_optimal(self):
        """Тест когда платформа близко к оптимальной позиции."""
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
        
        result = player.calculate_adaptive_paddle_speed(400, 402, 5)
        
        assert result == 35  # Минимальная скорость
    
    def test_calculate_adaptive_paddle_speed_urgent(self):
        """Тест в экстренной ситуации."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 540),
            ball_velocity=Point(5, 10),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.is_ball_moving_towards_paddle.return_value = True
        
        result = player.calculate_adaptive_paddle_speed(400, 600, 5)
        
        assert isinstance(result, int)
        assert result >= 35
    
    def test_calculate_adaptive_paddle_speed_far_distance(self):
        """Тест при большом расстоянии."""
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
        
        result = player.calculate_adaptive_paddle_speed(100, 700, 5)
        
        assert isinstance(result, int)
        assert result >= 35

