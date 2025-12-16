"""
Модуль для ленивой загрузки LearningSystem.
Позволяет отложить импорт и инициализацию тяжелого модуля до первого использования.
"""

from typing import Optional, Any
from .platform_utils import is_frozen


class LazyLearningSystem:
    """
    Обертка для ленивой загрузки LearningSystem.
    Импортирует и создает экземпляр LearningSystem только при первом обращении.
    """

    _instance: Optional[Any] = None
    _initialized: bool = False

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None):
        """
        Получает единственный экземпляр LearningSystem (Singleton pattern).
        Создает его только при первом вызове.

        Args:
            model_path: Опциональный путь к модели (передается только при первом создании)

        Returns:
            Экземпляр LearningSystem
        """
        if cls._instance is None:
            # Импорт только при первом использовании
            from .learning_system import LearningSystem

            cls._instance = LearningSystem(model_path=model_path)
            cls._initialized = True
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Сбрасывает экземпляр (для тестирования или переинициализации).
        """
        cls._instance = None
        cls._initialized = False

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Проверяет, был ли уже создан экземпляр.

        Returns:
            True если экземпляр уже создан, False иначе
        """
        return cls._initialized

    def __getattr__(self, name: str) -> Any:
        """
        Проксирует доступ к методам и атрибутам LearningSystem.
        При первом обращении автоматически создает экземпляр.
        """
        instance = self.get_instance()
        return getattr(instance, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Позволяет использовать LazyLearningSystem как функцию для получения экземпляра.
        """
        return self.get_instance(*args, **kwargs)


# Глобальный экземпляр для удобного использования
_lazy_learning_system = LazyLearningSystem()


def get_lazy_learning_system(model_path: Optional[str] = None):
    """
    Удобная функция для получения экземпляра LearningSystem с ленивой загрузкой.

    Args:
        model_path: Опциональный путь к модели

    Returns:
        Экземпляр LearningSystem
    """
    return _lazy_learning_system.get_instance(model_path=model_path)
