"""
Тесты для модуля game_utils.py
"""

import pytest
import pygame
import sys
import os
from unittest.mock import patch, MagicMock
from game.game_utils import (
    suppress_pkg_resources_warnings,
    resource_path,
    is_valid_player_name_char,
    build_bricks,
    create_ai_player,
)


class TestSuppressPkgResourcesWarnings:
    """Тесты для функции suppress_pkg_resources_warnings."""

    def test_suppress_warnings_context_manager(self):
        """Тест контекстного менеджера для подавления предупреждений."""
        with suppress_pkg_resources_warnings():
            # Внутри контекста предупреждения должны подавляться
            pass
        # После выхода из контекста все должно работать нормально


class TestResourcePath:
    """Тесты для функции resource_path."""

    @patch("sys._MEIPASS", "/tmp/pyinstaller", create=True)
    def test_resource_path_pyinstaller(self):
        """Тест resource_path в режиме PyInstaller."""
        path = resource_path("audio/test.mp3")
        assert "src" in path
        assert "resources" in path
        assert "audio" in path
        assert "test.mp3" in path

    def test_resource_path_development(self):
        """Тест resource_path в режиме разработки."""
        # Удаляем _MEIPASS если он есть
        if hasattr(sys, "_MEIPASS"):
            delattr(sys, "_MEIPASS")

        path = resource_path("images/test.png")
        assert "resources" in path
        assert "images" in path
        assert "test.png" in path

    def test_resource_path_normalization(self):
        """Тест нормализации пути."""
        path = resource_path("audio/../images/test.png")
        # Путь должен быть нормализован
        assert ".." not in path


class TestIsValidPlayerNameChar:
    """Тесты для функции is_valid_player_name_char."""

    def test_valid_latin_letters(self):
        """Тест валидных латинских букв."""
        assert is_valid_player_name_char("a") is True
        assert is_valid_player_name_char("Z") is True
        assert is_valid_player_name_char("M") is True

    def test_valid_cyrillic_letters(self):
        """Тест валидных кириллических букв."""
        assert is_valid_player_name_char("а") is True
        assert is_valid_player_name_char("Я") is True
        assert is_valid_player_name_char("ё") is True

    def test_invalid_characters(self):
        """Тест невалидных символов."""
        assert is_valid_player_name_char("1") is False
        assert is_valid_player_name_char("@") is False
        assert is_valid_player_name_char(" ") is False
        assert is_valid_player_name_char("!") is False

    def test_empty_string(self):
        """Тест пустой строки."""
        assert is_valid_player_name_char("") is False

    def test_multiple_chars(self):
        """Тест многосимвольной строки."""
        assert is_valid_player_name_char("ab") is False
        assert is_valid_player_name_char("abc") is False


class TestBuildBricks:
    """Тесты для функции build_bricks."""

    def test_build_bricks_returns_list(self):
        """Тест что build_bricks возвращает список."""
        bricks = build_bricks()
        assert isinstance(bricks, list)

    def test_build_bricks_count(self):
        """Тест количества кирпичей."""
        bricks = build_bricks()
        # Должно быть BRICK_ROWS * BRICK_COLS кирпичей
        from game.game_config import BRICK_ROWS, BRICK_COLS

        assert len(bricks) == BRICK_ROWS * BRICK_COLS

    def test_build_bricks_rects(self):
        """Тест что все элементы - pygame.Rect."""
        bricks = build_bricks()
        assert all(isinstance(brick, pygame.Rect) for brick in bricks)

    def test_build_bricks_dimensions(self):
        """Тест размеров кирпичей."""
        bricks = build_bricks()
        from game.game_config import BRICK_WIDTH, BRICK_HEIGHT

        assert all(brick.width == BRICK_WIDTH for brick in bricks)
        assert all(brick.height == BRICK_HEIGHT for brick in bricks)


class TestCreateAIPlayer:
    """Тесты для функции create_ai_player."""

    @patch("os.getenv")
    @patch("ai.ai_player.AIPlayer")
    def test_create_ai_player_default(self, mock_ai_player_class, mock_getenv):
        """Тест создания AIPlayer с параметрами по умолчанию."""
        mock_getenv.side_effect = lambda key, default: {
            "AI_USE_ASYNC_TRAJECTORY": "true",
            "AI_ASYNC_MAX_WORKERS": "2",
        }.get(key, default)

        mock_ai_player_instance = MagicMock()
        mock_ai_player_class.return_value = mock_ai_player_instance

        result = create_ai_player(800, 600, debug_mode=True)

        mock_ai_player_class.assert_called_once()
        call_args = mock_ai_player_class.call_args
        assert call_args[0][0] == 800  # screen_width
        assert call_args[0][1] == 600  # screen_height
        assert call_args[1]["debug_mode"] is True
        assert call_args[1]["use_async_trajectory"] is True
        assert call_args[1]["async_max_workers"] == 2

    @patch("os.getenv")
    @patch("ai.ai_player.AIPlayer")
    def test_create_ai_player_custom_env(self, mock_ai_player_class, mock_getenv):
        """Тест создания AIPlayer с кастомными переменными окружения."""
        mock_getenv.side_effect = lambda key, default: {
            "AI_USE_ASYNC_TRAJECTORY": "false",
            "AI_ASYNC_MAX_WORKERS": "4",
        }.get(key, default)

        mock_ai_player_instance = MagicMock()
        mock_ai_player_class.return_value = mock_ai_player_instance

        result = create_ai_player(800, 600, debug_mode=False)

        call_args = mock_ai_player_class.call_args
        assert call_args[1]["use_async_trajectory"] is False
        assert call_args[1]["async_max_workers"] == 4
