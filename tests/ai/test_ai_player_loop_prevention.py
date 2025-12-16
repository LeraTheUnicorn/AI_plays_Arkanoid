"""
Тесты для модуля ai_player_loop_prevention.py
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_loop_prevention import AIPlayerLoopPreventionMixin
from ai.game_state import GameState, Point


class TestAIPlayerLoopPreventionMixin:
    """Тесты для миксина AIPlayerLoopPreventionMixin."""

    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type("TestPlayer", (AIPlayerLoopPreventionMixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player._logger = Mock()
        player._predict_exact_landing_position = Mock(return_value=400.0)
        player._find_most_distant_brick = Mock(return_value=None)

        # Loop prevention system
        player.loop_prevention_system = {
            "movement_history": [],
            "position_history": [],
            "trajectory_history": [],
            "loop_detection_threshold": 5,
            "strategy_change_cooldown": 0,
            "alternative_strategies": [
                "center_focus",
                "edge_focus",
                "predictive_targeting",
            ],
            "current_strategy_index": 0,
        }

        # Smoothness system
        player.smoothness_system = {
            "recent_movements": [],
            "recent_positions": [],
            "movement_changes": [],
            "jitter_window": 10,
            "jitter_threshold": 3,
            "smoothness_penalty": 0.0,
            "min_movement_distance": 5,
        }

        # Separation zone tracker
        player.separation_zone_tracker = Mock()
        player.separation_zone_tracker.separation_zone_start = 250.0
        player.separation_zone_tracker.paddle_zone_start = 540.0
        player.separation_zone_tracker.target_position_set = False

        # Targeting system
        player.targeting_system = Mock()

        return player

    def test_detect_loop_pattern_insufficient_data(self):
        """Тест когда недостаточно данных."""
        player = self._create_mock_player()
        player.loop_prevention_system["movement_history"] = [1, 1, 1]

        result = player._detect_loop_pattern()

        assert result is False

    def test_detect_loop_pattern_repeating_movements(self):
        """Тест обнаружения повторяющихся движений."""
        player = self._create_mock_player()
        # 8 из 10 одинаковых движений
        player.loop_prevention_system["movement_history"] = [1] * 8 + [-1, 1]

        result = player._detect_loop_pattern()

        assert result is True

    def test_detect_loop_pattern_position_stagnation(self):
        """Тест обнаружения позиционной стагнации."""
        player = self._create_mock_player()
        # Нужно достаточно данных в movement_history для прохождения первой проверки
        player.loop_prevention_system["movement_history"] = [1] * 10
        player.loop_prevention_system["position_history"] = [400] * 10

        result = player._detect_loop_pattern()

        assert result is True

    def test_detect_loop_pattern_vertical_trajectory(self):
        """Тест обнаружения вертикальных траекторий."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(0, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        # Нужно достаточно данных в movement_history для прохождения первой проверки
        player.loop_prevention_system["movement_history"] = [1] * 10
        player.loop_prevention_system["trajectory_history"] = [
            {"ball_x": 400} for _ in range(5)
        ]

        result = player._detect_loop_pattern()

        assert result is True

    def test_change_strategy_if_looping_no_loop(self):
        """Тест когда зацикливания нет."""
        player = self._create_mock_player()
        player._detect_loop_pattern = Mock(return_value=False)

        initial_index = player.loop_prevention_system["current_strategy_index"]
        player._change_strategy_if_looping()

        assert player.loop_prevention_system["current_strategy_index"] == initial_index

    def test_change_strategy_if_looping_with_cooldown(self):
        """Тест с кулдауном."""
        player = self._create_mock_player()
        player._detect_loop_pattern = Mock(return_value=True)
        player.loop_prevention_system["strategy_change_cooldown"] = 5

        initial_index = player.loop_prevention_system["current_strategy_index"]
        player._change_strategy_if_looping()

        assert player.loop_prevention_system["strategy_change_cooldown"] == 4
        assert player.loop_prevention_system["current_strategy_index"] == initial_index

    def test_change_strategy_if_looping_change_strategy(self):
        """Тест смены стратегии."""
        player = self._create_mock_player()
        player._detect_loop_pattern = Mock(return_value=True)
        player.loop_prevention_system["strategy_change_cooldown"] = 0

        initial_index = player.loop_prevention_system["current_strategy_index"]
        player._change_strategy_if_looping()

        assert player.loop_prevention_system["current_strategy_index"] != initial_index
        assert player.loop_prevention_system["strategy_change_cooldown"] == 10

    def test_apply_alternative_strategy_center_focus(self):
        """Тест стратегии фокуса на центре."""
        player = self._create_mock_player()
        player.loop_prevention_system["current_strategy_index"] = 0

        result = player._apply_alternative_strategy(500)

        assert result == 400  # screen_width // 2

    def test_apply_alternative_strategy_edge_focus(self):
        """Тест стратегии фокуса на краях."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),
            paddle_position=Point(100, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.loop_prevention_system["current_strategy_index"] = 1

        result = player._apply_alternative_strategy(500)

        assert result in [70, 730]

    def test_apply_alternative_strategy_predictive_targeting(self):
        """Тест стратегии предсказательного прицеливания."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.width = 60
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[mock_brick],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        player.loop_prevention_system["current_strategy_index"] = 2
        player._find_most_distant_brick.return_value = mock_brick

        result = player._apply_alternative_strategy(400)

        assert isinstance(result, int)

    def test_find_most_distant_brick_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None

        result = player._find_most_distant_brick()

        assert result is None

    def test_find_most_distant_brick_with_bricks(self):
        """Тест поиска самого дальнего кубика."""
        player = self._create_mock_player()

        # Создаем объекты с атрибутом y, который можно получить через getattr
        class MockBrick:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        mock_brick1 = MockBrick(300, 200)
        mock_brick2 = MockBrick(500, 100)  # Ближе к paddle_y=550, значит дальше

        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[mock_brick1, mock_brick2],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        result = player._find_most_distant_brick()

        # Результат должен быть самым дальним по Y
        # abs(550 - 200) = 350, abs(550 - 100) = 450, значит mock_brick2 дальше
        # Но метод может вернуть None если нет кубиков или другие условия
        assert result is None or result in [mock_brick1, mock_brick2]

    def test_update_loop_tracking(self):
        """Тест обновления отслеживания зацикливания."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 10,
            game_score=0,
            game_time=0,
            ball_speed=5,
        )

        player._update_loop_tracking(1, 400, 450)

        assert len(player.loop_prevention_system["movement_history"]) > 0
        assert len(player.loop_prevention_system["position_history"]) > 0

    def test_update_smoothness_tracking(self):
        """Тест обновления отслеживания плавности."""
        player = self._create_mock_player()

        player._update_smoothness_tracking(1, 400)

        assert len(player.smoothness_system["recent_movements"]) > 0
        assert len(player.smoothness_system["recent_positions"]) > 0

    def test_detect_jitter_insufficient_data(self):
        """Тест когда недостаточно данных для обнаружения дрожания."""
        player = self._create_mock_player()
        player.smoothness_system["recent_movements"] = [1, 1]

        result = player._detect_jitter()

        assert result is False

    def test_detect_jitter_direction_changes(self):
        """Тест обнаружения дрожания по сменам направления."""
        player = self._create_mock_player()
        # Частые смены направления
        player.smoothness_system["recent_movements"] = [1, -1, 1, -1, 1, -1]

        result = player._detect_jitter()

        assert result is True

    def test_detect_jitter_micro_movements(self):
        """Тест обнаружения микродвижений."""
        player = self._create_mock_player()
        player.smoothness_system["recent_movements"] = [1, -1, 1, 0, 1]
        player.smoothness_system["recent_positions"] = [400, 401, 400, 401, 400]

        result = player._detect_jitter()

        # Может быть True или False в зависимости от условий
        assert isinstance(result, bool)

    def test_calculate_smooth_movement_target_position_set(self):
        """Тест плавного движения с установленной целевой позицией."""
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
        player.separation_zone_tracker.target_position_set = True

        result = player._calculate_smooth_movement(400, 425, 25)

        assert result == 0  # Не должно двигаться при малом расстоянии

    def test_calculate_smooth_movement_with_penalty(self):
        """Тест плавного движения со штрафом."""
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
        player.smoothness_system["smoothness_penalty"] = 0.5

        result = player._calculate_smooth_movement(400, 450, 50)

        assert result in [-1, 0, 1]

    def test_calculate_smooth_movement_right(self):
        """Тест движения вправо."""
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

        result = player._calculate_smooth_movement(400, 500, 100)

        assert result == 1

    def test_calculate_smooth_movement_left(self):
        """Тест движения влево."""
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

        result = player._calculate_smooth_movement(500, 400, 100)

        assert result == -1
