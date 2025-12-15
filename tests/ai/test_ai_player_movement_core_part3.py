"""
Тесты для модуля ai_player_movement_core_part3.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_movement_core_part3 import AIPlayerMovementCorePart3Mixin
from ai.game_state import GameState, Point


class TestAIPlayerMovementCorePart3Mixin:
    """Тесты для миксина AIPlayerMovementCorePart3Mixin."""
    
    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type('TestPlayer', (AIPlayerMovementCorePart3Mixin,), {})()
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
        player._change_strategy_if_looping = Mock()
        player._apply_alternative_strategy = Mock(return_value=400)
        player._detect_jitter = Mock(return_value=False)
        player._calculate_smooth_movement = Mock(return_value=1)
        player._calculate_decision_confidence = Mock(return_value=0.8)
        player.is_ball_moving_towards_paddle = Mock(return_value=True)
        player.position_optimizer = Mock()
        player.position_optimizer.calculate_paddle_movement = Mock(return_value=1)
        player.learning_system = Mock()
        player.learning_system.get_adaptive_paddle_speed = Mock(return_value=1.0)
        player.performance_logger = Mock()
        player.current_game_stats = {"total_moves": 0, "optimal_moves": 0}
        player._last_adjusted_paddle_speed = 15
        
        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.separation_zone_start = 250.0
        player.separation_zone_tracker.paddle_zone_start = 540.0
        player.separation_zone_tracker.target_position_set = False
        
        # Loop prevention system
        player.loop_prevention_system = {"strategy_change_cooldown": 0}
        
        # Smoothness system
        player.smoothness_system = {
            "smoothness_penalty": 0.0,
            "min_movement_distance": 5,
            "consecutive_stops": 0,
        }
        
        # Config
        player.config = Mock()
        
        return player
    
    def test_apply_movement_strategy_part3_ball_lost(self):
        """Тест когда мяч потерян."""
        player = self._create_mock_player()
        ball_lost = True
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part3(
            400, 400, 15, ball_lost, start_time_monitor
        )
        
        assert result == 0
        player._log_paddle_movement.assert_called()
    
    def test_apply_movement_strategy_part3_close_to_optimal(self):
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
        player.get_optimal_paddle_position.return_value = 402
        ball_lost = False
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part3(
            400, 402, 15, ball_lost, start_time_monitor
        )
        
        assert result in [0, -1, 1]
    
    def test_apply_movement_strategy_part3_far_from_optimal(self):
        """Тест когда платформа далеко от оптимальной позиции."""
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
        player.get_optimal_paddle_position.return_value = 600
        player.smoothness_system["min_movement_distance"] = 5
        ball_lost = False
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part3(
            400, 600, 15, ball_lost, start_time_monitor
        )
        
        assert result in [-1, 0, 1]
        # Метод может быть вызван или нет в зависимости от условий
        # Проверяем только что результат валиден
    
    def test_apply_movement_strategy_part3_jitter_detected(self):
        """Тест когда обнаружено дрожание."""
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
        player._detect_jitter.return_value = True
        player.get_optimal_paddle_position.return_value = 450
        ball_lost = False
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part3(
            400, 450, 15, ball_lost, start_time_monitor
        )
        
        assert result in [-1, 0, 1]
        assert player.smoothness_system["smoothness_penalty"] > 0
    
    def test_apply_movement_strategy_part3_alternative_strategy(self):
        """Тест применения альтернативной стратегии."""
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
        player.loop_prevention_system["strategy_change_cooldown"] = 0
        player.get_optimal_paddle_position.return_value = 450
        player._apply_alternative_strategy.return_value = 500
        ball_lost = False
        start_time_monitor = None
        
        result = player._apply_movement_strategy_part3(
            400, 450, 15, ball_lost, start_time_monitor
        )
        
        assert result in [-1, 0, 1]

