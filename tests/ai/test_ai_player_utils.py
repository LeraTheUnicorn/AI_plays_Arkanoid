"""
Тесты для модуля ai_player_utils.py
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_utils import AIPlayerUtilsMixin
from ai.game_state import GameState, Point


class TestAIPlayerUtilsMixin:
    """Тесты для миксина AIPlayerUtilsMixin."""

    def test_activate(self):
        """Тест активации AIPlayer."""

        class TestPlayer(AIPlayerUtilsMixin):
            def __init__(self):
                self.is_active = False
                self.paddle_movement_strategy = None
                self.screen_width = 800
                self.screen_height = 600
                self.paddle_width = 120
                self.config = Mock()
                self.position_optimizer = Mock()
                self.learning_system = Mock()
                self.zone_handler = Mock()
                self.target_tracker = Mock()
                self.loop_prevention_system = Mock()
                self.smoothness_system = Mock()
                self.separation_zone_tracker = Mock()
                self._logger = Mock()
                self.trajectory_predictor = Mock()
                self.current_game_state = None

        player = TestPlayer()
        player.get_optimal_paddle_position = Mock()
        player._log_paddle_movement = Mock()
        player._should_log_debug = Mock()
        player._predict_exact_landing_position = Mock()

        player.activate()

        assert player.is_active is True
        assert player.paddle_movement_strategy is not None

    def test_deactivate(self):
        """Тест деактивации AIPlayer."""

        class TestPlayer(AIPlayerUtilsMixin):
            def __init__(self):
                self.is_active = True
                self._logger = Mock()

        player = TestPlayer()
        player.deactivate()

        assert player.is_active is False
        player._logger.info.assert_called_once()

    def test_should_log_debug_debug_level(self):
        """Тест _should_log_debug при уровне DEBUG."""

        class TestPlayer(AIPlayerUtilsMixin):
            def __init__(self):
                self._logger = Mock()
                self._logger.getEffectiveLevel.return_value = logging.DEBUG

        player = TestPlayer()
        result = player._should_log_debug()

        assert result is True

    def test_should_log_debug_info_level(self):
        """Тест _should_log_debug при уровне INFO."""

        class TestPlayer(AIPlayerUtilsMixin):
            def __init__(self):
                self._logger = Mock()
                self._logger.getEffectiveLevel.return_value = logging.INFO

        player = TestPlayer()
        result = player._should_log_debug()

        assert result is False

    def test_is_ball_moving_towards_paddle_true(self):
        """Тест is_ball_moving_towards_paddle когда мяч падает."""

        class TestPlayer(AIPlayerUtilsMixin):
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
        result = player.is_ball_moving_towards_paddle()

        assert result is True

    def test_is_ball_moving_towards_paddle_false(self):
        """Тест is_ball_moving_towards_paddle когда мяч поднимается."""

        class TestPlayer(AIPlayerUtilsMixin):
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
        result = player.is_ball_moving_towards_paddle()

        assert result is False

    def test_is_ball_moving_towards_paddle_no_state(self):
        """Тест is_ball_moving_towards_paddle когда нет состояния."""

        class TestPlayer(AIPlayerUtilsMixin):
            def __init__(self):
                self.current_game_state = None

        player = TestPlayer()
        result = player.is_ball_moving_towards_paddle()

        assert result is False
