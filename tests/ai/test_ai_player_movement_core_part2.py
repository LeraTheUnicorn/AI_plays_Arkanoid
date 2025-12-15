"""
Тесты для модуля ai_player_movement_core_part2.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_movement_core_part2 import AIPlayerMovementCorePart2Mixin
from ai.game_state import GameState, Point


class TestAIPlayerMovementCorePart2Mixin:
    """Тесты для миксина AIPlayerMovementCorePart2Mixin."""
    
    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type('TestPlayer', (AIPlayerMovementCorePart2Mixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player.performance_monitor = None
        player._logger = Mock()
        player._log_paddle_movement = Mock()
        player._fallback_movement = Mock(return_value=0)
        player._update_loop_tracking = Mock()
        player._update_smoothness_tracking = Mock()
        player.get_optimal_paddle_position = Mock(return_value=400)
        player.config = Mock()
        player.config.paddle = Mock()
        player.config.paddle.zone_size = 30
        
        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.separation_zone_start = 250.0
        player.separation_zone_tracker.paddle_zone_start = 540.0
        player.separation_zone_tracker.target_position_set = False
        player.separation_zone_tracker.target_position = None
        player.separation_zone_tracker.saved_ball_vel_x = None
        player.separation_zone_tracker.paddle_moved_after_set = False
        player.separation_zone_tracker.paddle_reached_target = False
        player.separation_zone_tracker.frames_since_target_set = 0
        
        return player
    
    def test_apply_movement_strategy_part2_set_target_position(self):
        """Тест установки целевой позиции (ПРАВИЛО 4)."""
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
        player.get_optimal_paddle_position.return_value = 450
        
        ball_y = 400.0
        ball_vel_y = 5.0
        separation_zone_start = 250.0
        paddle_zone_start = 540.0
        paddle_y = 550.0
        ball_lost = False
        in_separation_zone = True
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part2(
            400, 450, 15, ball_y, ball_vel_y,
            separation_zone_start, paddle_zone_start, paddle_y,
            ball_lost, in_separation_zone, start_time_monitor
        )
        
        assert player.separation_zone_tracker.target_position_set is True
        assert result in [-1, 0, 1]
    
    def test_apply_movement_strategy_part2_target_unreachable(self):
        """Тест когда цель недостижима."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 540),
            ball_velocity=Point(5, 10),
            paddle_position=Point(100, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.get_optimal_paddle_position.return_value = 700
        
        ball_y = 540.0
        ball_vel_y = 10.0
        separation_zone_start = 250.0
        paddle_zone_start = 540.0
        paddle_y = 550.0
        ball_lost = False
        in_separation_zone = True
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part2(
            100, 700, 15, ball_y, ball_vel_y,
            separation_zone_start, paddle_zone_start, paddle_y,
            ball_lost, in_separation_zone, start_time_monitor
        )
        
        # Должно использовать промежуточную цель
        assert result in [-1, 0, 1]
    
    def test_apply_movement_strategy_part2_target_at_current_position(self):
        """Тест когда цель совпадает с текущей позицией."""
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
        player.get_optimal_paddle_position.return_value = 400
        
        ball_y = 400.0
        ball_vel_y = 5.0
        separation_zone_start = 250.0
        paddle_zone_start = 540.0
        paddle_y = 550.0
        ball_lost = False
        in_separation_zone = True
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part2(
            400, 400, 15, ball_y, ball_vel_y,
            separation_zone_start, paddle_zone_start, paddle_y,
            ball_lost, in_separation_zone, start_time_monitor
        )
        
        assert result == 0
        assert player.separation_zone_tracker.paddle_reached_target is True
    
    def test_apply_movement_strategy_part2_not_in_separation_zone(self):
        """Тест когда мяч не в зоне разделения."""
        player = self._create_mock_player()
        
        ball_y = 200.0
        ball_vel_y = -5.0
        separation_zone_start = 250.0
        paddle_zone_start = 540.0
        paddle_y = 550.0
        ball_lost = False
        in_separation_zone = False
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part2(
            400, 450, 15, ball_y, ball_vel_y,
            separation_zone_start, paddle_zone_start, paddle_y,
            ball_lost, in_separation_zone, start_time_monitor
        )
        
        assert result is None

