"""
Общие фикстуры и вспомогательные функции для всех тестов.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Generator

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_pygame():
    """Фикстура для мокирования pygame."""
    with patch("pygame.init"), patch("pygame.display.set_mode"), patch(
        "pygame.font.Font"
    ), patch("pygame.time.Clock"):
        yield


@pytest.fixture
def mock_game_state():
    """Фикстура для создания мокового GameState."""
    from ai.game_state import GameState, Point

    return GameState(
        ball_position=Point(400, 300),
        ball_velocity=Point(5, -5),
        paddle_position=Point(400, 550),
        paddle_width=120,
        remaining_bricks=[],
        game_score=0,
        game_time=0,
        ball_speed=5,
    )


@pytest.fixture
def mock_ball():
    """Фикстура для создания мокового мяча."""
    ball = Mock()
    ball.rect = Mock()
    ball.rect.centerx = 400
    ball.rect.centery = 300
    ball.vel_x = 5
    ball.vel_y = -5
    ball.get_speed = Mock(return_value=5)
    return ball


@pytest.fixture
def mock_paddle():
    """Фикстура для создания моковой платформы."""
    paddle = Mock()
    paddle.rect = Mock()
    paddle.rect.centerx = 400
    paddle.rect.centery = 550
    paddle.rect.width = 120
    paddle.rect.height = 15
    return paddle


@pytest.fixture
def mock_bricks():
    """Фикстура для создания списка кирпичей."""
    import pygame

    bricks = []
    for i in range(5):
        for j in range(10):
            brick = pygame.Rect(j * 70 + 50, i * 30 + 60, 60, 20)
            bricks.append(brick)
    return bricks


@pytest.fixture
def screen_dimensions():
    """Фикстура для размеров экрана."""
    return {"width": 800, "height": 600}


@pytest.fixture(autouse=True)
def setup_logging():
    """Автоматическая настройка логирования для тестов."""
    import logging

    logging.basicConfig(level=logging.WARNING)  # Минимальный уровень для тестов
    yield
    # Очистка после теста
    logging.shutdown()
