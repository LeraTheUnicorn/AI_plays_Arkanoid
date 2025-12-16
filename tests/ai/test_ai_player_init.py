"""
Тесты для модуля ai_player_init.py
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from ai.ai_player_init import AIPlayerInitMixin


class TestAIPlayerInitMixin:
    """Тесты для миксина AIPlayerInitMixin."""

    def test_validate_dimensions_valid(self):
        """Тест валидации корректных размеров."""

        # Создаем минимальный мок для вызова метода экземпляра
        class TestClass(AIPlayerInitMixin):
            pass

        instance = TestClass()
        # Не должно быть исключений
        instance._validate_dimensions(800, 600)
        instance._validate_dimensions(400, 300)  # Минимальные размеры

    def test_validate_dimensions_invalid_types(self):
        """Тест валидации некорректных типов."""

        class TestClass(AIPlayerInitMixin):
            pass

        instance = TestClass()
        with pytest.raises(TypeError):
            instance._validate_dimensions("800", 600)

        with pytest.raises(TypeError):
            instance._validate_dimensions(800, "600")

    def test_validate_dimensions_invalid_values(self):
        """Тест валидации некорректных значений."""

        class TestClass(AIPlayerInitMixin):
            pass

        instance = TestClass()
        with pytest.raises(ValueError):
            instance._validate_dimensions(0, 600)

        with pytest.raises(ValueError):
            instance._validate_dimensions(800, -100)

        with pytest.raises(ValueError):
            instance._validate_dimensions(300, 200)  # Меньше минимума

    def test_get_env_bool(self):
        """Тест получения булевого значения из переменной окружения."""
        # _get_env_bool - это статический метод
        with patch("os.getenv", return_value="true"):
            assert AIPlayerInitMixin._get_env_bool("TEST_KEY", default=False) is True

        with patch("os.getenv", return_value="1"):
            assert AIPlayerInitMixin._get_env_bool("TEST_KEY", default=False) is True

        with patch("os.getenv", return_value="false"):
            assert AIPlayerInitMixin._get_env_bool("TEST_KEY", default=True) is False

        with patch("os.getenv", return_value=""):
            assert AIPlayerInitMixin._get_env_bool("TEST_KEY", default=True) is True

        with patch("os.getenv", return_value=None):
            assert AIPlayerInitMixin._get_env_bool("TEST_KEY", default=False) is False
