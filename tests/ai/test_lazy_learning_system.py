"""
Тесты для модуля lazy_learning_system.py
"""

import pytest
from unittest.mock import Mock, patch
from ai.lazy_learning_system import LazyLearningSystem, get_lazy_learning_system


class TestLazyLearningSystem:
    """Тесты для класса LazyLearningSystem."""

    def test_get_instance_first_call(self):
        """Тест первого вызова get_instance."""
        # Сбрасываем экземпляр перед тестом
        LazyLearningSystem.reset_instance()

        instance = LazyLearningSystem.get_instance()

        assert instance is not None
        assert LazyLearningSystem.is_initialized() is True

    def test_get_instance_singleton(self):
        """Тест что возвращается один и тот же экземпляр."""
        LazyLearningSystem.reset_instance()

        instance1 = LazyLearningSystem.get_instance()
        instance2 = LazyLearningSystem.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """Тест сброса экземпляра."""
        LazyLearningSystem.reset_instance()

        instance1 = LazyLearningSystem.get_instance()
        assert LazyLearningSystem.is_initialized() is True

        LazyLearningSystem.reset_instance()
        assert LazyLearningSystem.is_initialized() is False

        instance2 = LazyLearningSystem.get_instance()
        assert instance1 is not instance2

    def test_is_initialized(self):
        """Тест проверки инициализации."""
        LazyLearningSystem.reset_instance()

        assert LazyLearningSystem.is_initialized() is False

        LazyLearningSystem.get_instance()

        assert LazyLearningSystem.is_initialized() is True

    def test_getattr_proxy(self):
        """Тест проксирования атрибутов."""
        LazyLearningSystem.reset_instance()

        lazy = LazyLearningSystem()

        # Доступ к атрибуту должен создать экземпляр и вернуть значение
        # Проверяем, что можем получить доступ к атрибутам LearningSystem
        assert hasattr(lazy.get_instance(), "model_path") or hasattr(
            lazy.get_instance(), "learning_data"
        )

    def test_call_method(self):
        """Тест использования как функции."""
        LazyLearningSystem.reset_instance()

        lazy = LazyLearningSystem()
        instance = lazy()

        assert instance is not None


class TestGetLazyLearningSystem:
    """Тесты для функции get_lazy_learning_system."""

    def test_get_lazy_learning_system(self):
        """Тест получения экземпляра через функцию."""
        instance = get_lazy_learning_system()

        assert instance is not None

    def test_get_lazy_learning_system_singleton(self):
        """Тест что функция возвращает тот же экземпляр."""
        instance1 = get_lazy_learning_system()
        instance2 = get_lazy_learning_system()

        assert instance1 is instance2
