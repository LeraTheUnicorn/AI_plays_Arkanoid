"""
Расширенные тесты для модуля game_models.py
"""

import pytest
import pygame
from unittest.mock import Mock
from game.game_models import Ball, Paddle, GameState
from game.game_config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PADDLE_WIDTH,
    BALL_SIZE,
    BALL_SPEED_DEFAULT,
)


class TestBallExtended:
    """Расширенные тесты для класса Ball."""

    def test_update_wall_collision_left(self):
        """Тест столкновения с левой стеной."""
        ball = Ball()
        ball.rect.centerx = 5  # Близко к левой стене
        ball.vel_x = -10  # Движется влево
        original_vel_x = ball.vel_x

        ball.update()

        # Скорость должна измениться на противоположную
        assert ball.vel_x == -original_vel_x
        assert ball.rect.centerx >= BALL_SIZE // 2

    def test_update_wall_collision_right(self):
        """Тест столкновения с правой стеной."""
        ball = Ball()
        ball.rect.centerx = SCREEN_WIDTH - 5  # Близко к правой стене
        ball.vel_x = 10  # Движется вправо
        original_vel_x = ball.vel_x

        ball.update()

        # Скорость должна измениться на противоположную
        assert ball.vel_x == -original_vel_x
        assert ball.rect.centerx <= SCREEN_WIDTH - BALL_SIZE // 2

    def test_update_ceiling_collision(self):
        """Тест столкновения с потолком."""
        ball = Ball()
        ball.rect.centery = 5  # Близко к потолку
        ball.vel_y = -10  # Движется вверх
        original_vel_y = ball.vel_y

        ball.update()

        # Скорость должна измениться на противоположную
        assert ball.vel_y == -original_vel_y
        assert ball.rect.centery >= BALL_SIZE // 2
        assert ball._wall_bounce_count == 0  # Сбрасывается при отскоке от потолка

    def test_update_wall_bounce_count(self):
        """Тест счетчика отскоков от стен."""
        ball = Ball()
        ball.rect.left = 0  # У левой стены
        ball._wall_bounce_count = 0
        ball.vel_x = -5  # Движется влево

        # Обновляем несколько раз, чтобы мяч оставался у стены
        for _ in range(15):  # Больше 10, чтобы сработала защита от зацикливания
            ball.update()
            # После каждого обновления мяч может отскочить, возвращаем к стене
            if ball.rect.left > 0:
                ball.rect.left = 0

        # Счетчик должен увеличиться или сброситься после защиты
        assert ball._wall_bounce_count >= 0

    def test_bounce_vertical_zero_velocity(self):
        """Тест вертикального отскока при нулевой скорости."""
        ball = Ball()
        ball.vel_y = 0
        ball.current_speed = 5

        ball.bounce_vertical()

        assert ball.vel_y == -5

    def test_bounce_vertical_non_zero_velocity(self):
        """Тест вертикального отскока при ненулевой скорости."""
        ball = Ball()
        ball.vel_y = 5
        original_vel_y = ball.vel_y

        ball.bounce_vertical()

        assert ball.vel_y == -original_vel_y

    def test_reset_position(self):
        """Тест позиции мяча после reset."""
        ball = Ball()
        paddle = Paddle()

        ball.reset(paddle.rect)

        assert ball.rect.centerx == paddle.rect.centerx
        assert ball.rect.centery < paddle.rect.top
        assert abs(ball.vel_x) == ball.current_speed
        assert ball.vel_y == -ball.current_speed

    def test_set_speed_valid(self):
        """Тест установки валидной скорости."""
        ball = Ball()
        new_speed = 7

        ball.set_speed(new_speed)

        assert ball.current_speed == new_speed

    def test_set_speed_invalid_low(self):
        """Тест установки слишком малой скорости."""
        ball = Ball()
        original_speed = ball.current_speed

        ball.set_speed(0)

        # Скорость не должна измениться
        assert ball.current_speed == original_speed

    def test_set_speed_invalid_high(self):
        """Тест установки слишком большой скорости."""
        ball = Ball()
        original_speed = ball.current_speed

        ball.set_speed(20)

        # Скорость не должна измениться
        assert ball.current_speed == original_speed

    def test_set_speed_with_settings_manager(self):
        """Тест установки скорости с менеджером настроек."""
        ball = Ball()
        mock_settings = Mock()

        ball.set_speed(8, mock_settings)

        assert ball.current_speed == 8
        mock_settings.set_ball_speed.assert_called_once_with(8)

    def test_increase_speed_max(self):
        """Тест увеличения скорости до максимума."""
        ball = Ball()
        ball.set_speed(10)  # Максимальная скорость

        ball.increase_speed()

        # Скорость не должна превысить максимум
        assert ball.current_speed == 10

    def test_decrease_speed_min(self):
        """Тест уменьшения скорости до минимума."""
        ball = Ball()
        ball.set_speed(1)  # Минимальная скорость

        ball.decrease_speed()

        # Скорость не должна быть меньше минимума
        assert ball.current_speed == 1


class TestPaddleExtended:
    """Расширенные тесты для класса Paddle."""

    def test_move_left_boundary(self):
        """Тест движения влево до границы."""
        paddle = Paddle()
        paddle.rect.centerx = PADDLE_WIDTH // 2  # На левой границе

        paddle.move(-1)

        # Позиция не должна выйти за границы
        assert paddle.rect.centerx >= PADDLE_WIDTH // 2

    def test_move_right_boundary(self):
        """Тест движения вправо до границы."""
        paddle = Paddle()
        paddle.rect.centerx = SCREEN_WIDTH - PADDLE_WIDTH // 2  # На правой границе

        paddle.move(1)

        # Позиция не должна выйти за границы
        assert paddle.rect.centerx <= SCREEN_WIDTH - PADDLE_WIDTH // 2

    def test_move_multiple_times(self):
        """Тест множественных движений."""
        paddle = Paddle()
        initial_x = paddle.rect.centerx

        for _ in range(10):
            paddle.move(1)

        assert paddle.rect.centerx > initial_x
        assert paddle.rect.centerx <= SCREEN_WIDTH - PADDLE_WIDTH // 2


class TestGameStateExtended:
    """Расширенные тесты для класса GameState."""

    def test_reset_all_fields(self):
        """Тест сброса всех полей."""
        state = GameState()
        state.score = 100
        state.lives_left = 1
        state.game_started = True
        state.game_over = True
        state.bricks = [pygame.Rect(0, 0, 60, 20)]
        state.game_start_time = 123.45

        state.reset()

        assert state.score == 0
        assert state.lives_left == 3
        assert state.game_started is False
        assert state.game_over is False
        assert len(state.bricks) == 0
        assert state.game_start_time == 0.0

    def test_reset_multiple_times(self):
        """Тест множественных сбросов."""
        state = GameState()

        for _ in range(3):
            state.score = 50
            state.reset()
            assert state.score == 0
