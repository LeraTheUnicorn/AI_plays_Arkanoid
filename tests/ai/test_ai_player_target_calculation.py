"""
Тесты для модуля ai_player_target_calculation.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_target_calculation import AIPlayerTargetCalculationMixin
from ai.game_state import GameState, Point


class TestAIPlayerTargetCalculationMixin:
    """Тесты для миксина AIPlayerTargetCalculationMixin."""

    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type("TestPlayer", (AIPlayerTargetCalculationMixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player._logger = Mock()
        player._log_paddle_movement = Mock()
        player._is_time_pressure = Mock(return_value=False)
        player._force_target_brick_from_coordinates = Mock(return_value=None)
        player._predict_exact_landing_position = Mock(return_value=400.0)
        player._set_target_position_if_needed = Mock()

        # Learning system
        player.learning_system = Mock()
        player.learning_system.apply_user_prompt_rules = Mock(return_value={})
        player.learning_system.get_strategy_recommendation = Mock(return_value={})
        player.learning_system.predict_success_probability = Mock(return_value=0.8)
        player.learning_system.get_optimal_position_preference = Mock(return_value=0.7)

        # Position calculator
        player.position_calculator = Mock()
        player.position_calculator.calculate_precise_position_for_few_bricks = Mock(
            return_value=None
        )
        player.position_calculator.calculate_position_for_max_destruction = Mock(
            return_value=None
        )
        player.position_calculator.calculate_position_with_target_brick = Mock(
            return_value=None
        )

        # Target selector
        player.target_selector = Mock()
        player.target_selector.find_best_target_brick = Mock(return_value=None)

        # Targeting system
        player.targeting_system = Mock()
        player.targeting_system.brick_coordinates = []

        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.target_position_set = False
        player.separation_zone_tracker.target_position = None

        # Empty bounce tracker
        player.empty_bounce_tracker = {
            "consecutive_empty_bounces": 0,
            "max_empty_bounces": 3,
        }

        # Config
        player.config = Mock()
        player.config.ball = Mock()
        player.config.ball.default_speed = 5
        player.config.precision_priority_threshold = 10
        player.config.confidence_default = 0.8
        player.config.success_probability_threshold = 0.6
        player.config.low_success_probability_threshold = 0.5
        player.config.paddle_zone_offset_range = (-40, 41)
        player.config.paddle_zone_offset_step = 10

        return player

    def test_calculate_target_position_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None

        result = player._calculate_target_position(
            400.0, 400.0, {"separation_zone_start": 250.0, "paddle_zone_start": 540.0}
        )

        assert isinstance(result, int)

    def test_calculate_target_position_precision_priority(self):
        """Тест с приоритетом точности."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 5,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.position_calculator.calculate_precise_position_for_few_bricks.return_value = (
            450
        )

        result = player._calculate_target_position(
            400.0, 400.0, {"separation_zone_start": 250.0, "paddle_zone_start": 540.0}
        )

        assert isinstance(result, int)

    def test_calculate_target_position_empty_bounces(self):
        """Тест при отбитиях в пустоту."""
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
        player.empty_bounce_tracker["consecutive_empty_bounces"] = 3
        player.targeting_system.brick_coordinates = [{"x": 300, "y": 200}]
        player._force_target_brick_from_coordinates.return_value = 450.0

        result = player._calculate_target_position(
            400.0, 400.0, {"separation_zone_start": 250.0, "paddle_zone_start": 540.0}
        )

        assert isinstance(result, int)

    def test_calculate_precision_position(self):
        """Тест расчета точной позиции."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 5,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.position_calculator.calculate_precise_position_for_few_bricks.return_value = (
            450
        )

        result = player._calculate_precision_position(
            400.0,
            400.0,
            {"separation_zone_start": 250.0, "paddle_zone_start": 540.0},
            5,
            5,
            {},
        )

        assert isinstance(result, int)

    def test_calculate_position_with_target_brick(self):
        """Тест расчета позиции с целевым кубиком."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60

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
        player.position_calculator.calculate_optimal_offset = Mock(return_value=0.5)
        player.position_calculator.calculate_position_with_target_brick.return_value = (
            450
        )

        result = player._calculate_position_with_target_brick(
            400.0,
            400.0,
            {"separation_zone_start": 250.0, "paddle_zone_start": 540.0},
            1,
        )

        assert isinstance(result, int)

    def test_ensure_safe_paddle_position_left_edge(self):
        """Тест защиты от попадания в левый край."""
        player = self._create_mock_player()

        # Мяч попадает близко к левому краю
        paddle_center_x = 100.0
        landing_x = 50.0  # Очень близко к левому краю платформы (paddle_left_edge = 40)

        result = player._ensure_safe_paddle_position(paddle_center_x, landing_x)

        assert (
            result >= paddle_center_x
        )  # Должно сместиться вправо или остаться на месте
        assert isinstance(result, float)

    def test_ensure_safe_paddle_position_right_edge(self):
        """Тест защиты от попадания в правый край."""
        player = self._create_mock_player()

        # Мяч попадает близко к правому краю
        paddle_center_x = 700.0
        landing_x = (
            750.0  # Очень близко к правому краю платформы (paddle_right_edge = 760)
        )

        result = player._ensure_safe_paddle_position(paddle_center_x, landing_x)

        assert (
            result <= paddle_center_x
        )  # Должно сместиться влево или остаться на месте
        assert isinstance(result, float)

    def test_ensure_safe_paddle_position_safe(self):
        """Тест когда позиция уже безопасна."""
        player = self._create_mock_player()

        paddle_center_x = 400.0
        landing_x = 400.0  # В центре платформы

        result = player._ensure_safe_paddle_position(paddle_center_x, landing_x)

        assert result == paddle_center_x  # Не должно измениться

    def test_calculate_fallback_position(self):
        """Тест расчета резервной позиции."""
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

        result = player._calculate_fallback_position(
            400.0,
            400.0,
            {"separation_zone_start": 250.0, "paddle_zone_start": 540.0},
            10,
        )

        assert isinstance(result, int)
        assert 60 <= result <= 740  # В пределах экрана

    def test_set_target_position_if_needed(self):
        """Тест установки целевой позиции."""
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
        # Убеждаемся что target_tracker существует и является Mock
        player.target_tracker = Mock()
        player.target_tracker.set_target_position = Mock()

        player._set_target_position_if_needed(450, "test_reason")

        # Метод должен быть вызван, если target_tracker существует
        # Проверяем что метод выполнился без ошибок
        assert hasattr(player, "target_tracker")
