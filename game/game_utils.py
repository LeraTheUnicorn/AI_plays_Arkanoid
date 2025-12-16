"""
Утилиты для игры Арканоид.
"""

import os
import sys
import warnings
from contextlib import contextmanager
from typing import Generator, List
import pygame  # type: ignore[reportMissingImports]


# Контекстный менеджер для ограниченного подавления предупреждений
@contextmanager
def suppress_pkg_resources_warnings() -> Generator[None, None, None]:
    """Временно подавляет предупреждения о pkg_resources от pygame в ограниченной области"""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=".*pkg_resources.*", category=UserWarning
        )
        yield


def resource_path(relative_path: str) -> str:
    """
    Получает абсолютный путь к ресурсу, работает как в разработке, так и в exe.

    Кросс-платформенная функция для получения правильного пути к ресурсам.
    Использует os.path.join для корректной работы на разных ОС.

    Args:
        relative_path: Относительный путь к ресурсу (например, "FVCK_AI.mp3" или "images/d2.gif")
                      Путь должен быть относительно resources/

    Returns:
        Абсолютный путь к ресурсу, нормализованный для текущей ОС

    Note:
        В режиме разработки использует директорию resources/ в корне проекта.
        В скомпилированном exe (PyInstaller) ресурсы находятся в _MEIPASS/resources/.
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
        # В exe ресурсы находятся в resources/ (как указано в --add-data)
        resources_path = os.path.join(base_path, "resources")
    except AttributeError:
        # В режиме разработки файл находится в game/, нужно подняться на уровень вверх и войти в resources/
        current_dir = os.path.dirname(os.path.abspath(__file__))  # game/
        project_root = os.path.dirname(current_dir)  # корень проекта
        resources_path = os.path.join(project_root, "resources")  # resources/

    # Используем os.path.join для кросс-платформенной совместимости
    # и нормализуем путь для корректной работы на всех ОС
    full_path = os.path.join(resources_path, relative_path)
    return os.path.normpath(full_path)


def is_valid_player_name_char(char: str) -> bool:
    """
    Проверяет, является ли символ допустимым для имени игрока.

    Args:
        char: Символ для проверки

    Returns:
        True если символ допустим (латинские или кириллические буквы), False иначе

    Note:
        Функция не используется в основном коде (авторежим не требует ввода имени),
        но сохранена для совместимости с тестами.
    """
    if not char or len(char) != 1:  # Проверяем пустые строки и многосимвольные строки
        return False
    # Разрешаем только буквы (латинские и кириллические)
    # isalpha() поддерживает Unicode, включая кириллицу
    return char.isalpha() and not char.isspace()


def build_bricks() -> List[pygame.Rect]:
    """
    Создает сетку кирпичей для игры.

    Returns:
        Список pygame.Rect объектов, представляющих кирпичи на экране

    Note:
        Для использования новой архитектуры см. game_controllers.GameController.build_bricks()
    """
    try:
        from .game_config import (
            BRICK_COLS,
            BRICK_HEIGHT,
            BRICK_OFFSET_TOP,
            BRICK_PADDING,
            BRICK_ROWS,
            BRICK_WIDTH,
            SCREEN_WIDTH,
        )
    except ImportError:
        from game.game_config import (
            BRICK_COLS,
            BRICK_HEIGHT,
            BRICK_OFFSET_TOP,
            BRICK_PADDING,
            BRICK_ROWS,
            BRICK_WIDTH,
            SCREEN_WIDTH,
        )

    bricks = []
    start_x = (
        SCREEN_WIDTH - (BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * BRICK_PADDING)
    ) // 2
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLS):
            x = start_x + col * (BRICK_WIDTH + BRICK_PADDING)
            y = BRICK_OFFSET_TOP + row * (BRICK_HEIGHT + BRICK_PADDING)
            bricks.append(pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT))
    return bricks


def create_ai_player(screen_width: int, screen_height: int, debug_mode: bool = True):
    """
    Создает AIPlayer с настройками многопоточности.

    Args:
        screen_width: Ширина экрана
        screen_height: Высота экрана
        debug_mode: Режим отладки

    Returns:
        Экземпляр AIPlayer с настроенным многопоточным режимом (если включен)
    """
    from ai.ai_player import AIPlayer

    # Настройки многопоточности для асинхронных расчетов траектории
    # ✅ ИЗМЕНЕНО: Многопоточность включена по умолчанию для лучшей производительности
    USE_ASYNC_TRAJECTORY = (
        os.getenv("AI_USE_ASYNC_TRAJECTORY", "true").lower() == "true"
    )
    ASYNC_MAX_WORKERS = int(os.getenv("AI_ASYNC_MAX_WORKERS", "2"))

    return AIPlayer(
        screen_width,
        screen_height,
        debug_mode=debug_mode,
        use_async_trajectory=USE_ASYNC_TRAJECTORY,
        async_max_workers=ASYNC_MAX_WORKERS,
    )
