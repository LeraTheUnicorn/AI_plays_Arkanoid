"""
Тесты для модуля ai_player_positioning.py
"""

import pytest
from unittest.mock import Mock
from ai.ai_player_positioning import AIPlayerPositioningMixin
from ai.game_state import GameState, Point


class TestAIPlayerPositioningMixin:
    """Тесты для миксина AIPlayerPositioningMixin."""

    def test_predict_exact_landing_position_no_state(self):
        """Тест предсказания позиции без состояния."""

        class TestPlayer(AIPlayerPositioningMixin):
            def __init__(self):
                self.current_game_state = None
                self.screen_width = 800
                self.paddle_width = 120

        player = TestPlayer()
        position = player._predict_exact_landing_position()

        assert position == 400.0  # Центр экрана

    def test_predict_exact_landing_position_ball_rising(self):
        """Тест предсказания когда мяч поднимается."""

        class TestPlayer(AIPlayerPositioningMixin):
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
                self.screen_width = 800
                self.paddle_width = 120
                self.config = Mock()
                self.config.ball = Mock()
                self.config.ball.radius = 8

        player = TestPlayer()
        position = player._predict_exact_landing_position()

        # Когда мяч поднимается, возвращается текущая X координата
        assert position == 400.0

    def test_predict_exact_landing_position_ball_falling(self):
        """Тест предсказания когда мяч падает."""

        class TestPlayer(AIPlayerPositioningMixin):
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
                self.screen_width = 800
                self.paddle_width = 120
                self.config = Mock()
                self.config.ball = Mock()
                self.config.ball.radius = 8

        player = TestPlayer()
        position = player._predict_exact_landing_position()

        assert isinstance(position, float)
        assert 0 <= position <= 800

    def test_predict_exact_landing_position_with_wall_bounce(self):
        """Тест предсказания с учетом отскока от стен."""

        class TestPlayer(AIPlayerPositioningMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(10, 500),  # Близко к левой стене
                    ball_velocity=Point(-5, 5),  # Движется влево и вниз
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.screen_width = 800
                self.paddle_width = 120
                self.config = Mock()
                self.config.ball = Mock()
                self.config.ball.radius = 8

        player = TestPlayer()
        position = player._predict_exact_landing_position()

        # Может быть float или int после приведения
        assert isinstance(position, (int, float))
        assert 0 <= position <= 800

    def test_handle_ceiling_bounce_positioning_no_state(self):
        """Тест обработки отскока от потолка без состояния."""

        class TestPlayer(AIPlayerPositioningMixin):
            def __init__(self):
                self.current_game_state = None
                self.screen_width = 800
                self.targeting_system = Mock()
                self.targeting_system.brick_coordinates = []

        player = TestPlayer()
        position = player._handle_ceiling_bounce_positioning()

        assert position == 400  # Центр экрана

    def test_handle_ceiling_bounce_positioning_with_bounce(self):
        """Тест обработки отскока от потолка."""

        class TestPlayer(AIPlayerPositioningMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 20),  # Близко к потолку
                    ball_velocity=Point(5, 2),  # Движется вниз после отскока
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.screen_width = 800
                self.paddle_width = 120
                self.targeting_system = Mock()
                self.targeting_system.brick_coordinates = []
                self._track_ball_position = Mock(return_value=400.0)

        player = TestPlayer()
        position = player._handle_ceiling_bounce_positioning()

        assert isinstance(position, int)
        assert 0 <= position <= 800

    def test_handle_ceiling_bounce_positioning_low_velocity(self):
        """Тест обработки отскока при низкой скорости."""

        class TestPlayer(AIPlayerPositioningMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 20),
                    ball_velocity=Point(1, 2),  # Низкая горизонтальная скорость
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.screen_width = 800
                self.paddle_width = 120
                self.targeting_system = Mock()
                self.targeting_system.brick_coordinates = [
                    {"x": 200, "center_x": 200, "center_y": 100},
                    {"x": 600, "center_x": 600, "center_y": 100},
                ]

        player = TestPlayer()
        position = player._handle_ceiling_bounce_positioning()

        assert isinstance(position, int)
        assert 0 <= position <= 800
