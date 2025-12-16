"""
Тесты для модуля game_models.py
"""

import pytest
import pygame
from unittest.mock import Mock, patch
from game.game_models import Ball, Paddle, GameState
from game.game_config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PADDLE_WIDTH,
    PADDLE_HEIGHT,
    BALL_SIZE,
    BALL_SPEED_DEFAULT,
)


class TestPaddle:
    """Тесты для класса Paddle."""

    def test_paddle_creation(self):
        """Тест создания платформы."""
        paddle = Paddle()
        assert isinstance(paddle.rect, pygame.Rect)
        assert paddle.rect.width == PADDLE_WIDTH
        assert paddle.rect.height == PADDLE_HEIGHT

    def test_paddle_move_left(self):
        """Тест движения платформы влево."""
        paddle = Paddle()
        initial_x = paddle.rect.centerx
        paddle.move(-1)
        assert paddle.rect.centerx < initial_x

    def test_paddle_move_right(self):
        """Тест движения платформы вправо."""
        paddle = Paddle()
        initial_x = paddle.rect.centerx
        paddle.move(1)
        assert paddle.rect.centerx > initial_x

    def test_paddle_boundary_left(self):
        """Тест ограничения движения платформы слева."""
        paddle = Paddle()
        paddle.rect.centerx = PADDLE_WIDTH // 2
        paddle.move(-1)
        assert paddle.rect.centerx >= PADDLE_WIDTH // 2

    def test_paddle_boundary_right(self):
        """Тест ограничения движения платформы справа."""
        paddle = Paddle()
        paddle.rect.centerx = SCREEN_WIDTH - PADDLE_WIDTH // 2
        paddle.move(1)
        assert paddle.rect.centerx <= SCREEN_WIDTH - PADDLE_WIDTH // 2


class TestBall:
    """Тесты для класса Ball."""

    def test_ball_creation(self):
        """Тест создания мяча."""
        ball = Ball()
        assert isinstance(ball.rect, pygame.Rect)
        assert ball.rect.width == BALL_SIZE
        assert ball.rect.height == BALL_SIZE
        assert ball.current_speed == BALL_SPEED_DEFAULT

    def test_ball_update(self):
        """Тест обновления позиции мяча."""
        ball = Ball()
        initial_x = ball.rect.centerx
        initial_y = ball.rect.centery
        ball.update()
        # Мяч должен переместиться
        assert ball.rect.centerx != initial_x or ball.rect.centery != initial_y

    def test_ball_bounce_vertical(self):
        """Тест вертикального отскока мяча."""
        ball = Ball()
        original_vel_y = ball.vel_y
        ball.bounce_vertical()
        assert ball.vel_y == -original_vel_y

    def test_ball_reset(self):
        """Тест сброса мяча на платформу."""
        ball = Ball()
        paddle = Paddle()
        ball.reset(paddle.rect)
        assert ball.rect.centerx == paddle.rect.centerx
        assert ball.rect.centery < paddle.rect.top

    def test_ball_set_speed(self):
        """Тест установки скорости мяча."""
        ball = Ball()
        new_speed = 7
        ball.set_speed(new_speed)
        assert ball.current_speed == new_speed

    def test_ball_set_speed_boundaries(self):
        """Тест границ скорости мяча."""
        ball = Ball()
        # Слишком малая скорость
        ball.set_speed(0)
        assert ball.current_speed != 0  # Должна остаться предыдущая

        # Слишком большая скорость
        ball.set_speed(20)
        assert ball.current_speed <= 10  # Максимум 10

    def test_ball_increase_speed(self):
        """Тест увеличения скорости мяча."""
        ball = Ball()
        initial_speed = ball.current_speed
        ball.increase_speed()
        assert ball.current_speed == initial_speed + 1

    def test_ball_decrease_speed(self):
        """Тест уменьшения скорости мяча."""
        ball = Ball()
        ball.set_speed(5)
        ball.decrease_speed()
        assert ball.current_speed == 4

    def test_ball_get_speed(self):
        """Тест получения скорости мяча."""
        ball = Ball()
        ball.set_speed(8)
        assert ball.get_speed() == 8


class TestGameState:
    """Тесты для класса GameState."""

    def test_game_state_creation(self):
        """Тест создания состояния игры."""
        state = GameState()
        assert state.score == 0
        assert state.lives_left == 3
        assert state.game_started is False
        assert state.game_over is False
        assert isinstance(state.bricks, list)

    def test_game_state_reset(self):
        """Тест сброса состояния игры."""
        state = GameState()
        state.score = 100
        state.lives_left = 1
        state.game_started = True
        state.game_over = True
        state.bricks = [pygame.Rect(0, 0, 60, 20)]

        state.reset()
        assert state.score == 0
        assert state.lives_left == 3
        assert state.game_started is False
        assert state.game_over is False
        assert len(state.bricks) == 0
