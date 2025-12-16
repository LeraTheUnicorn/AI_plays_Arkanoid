"""
Модуль обработки событий игры для PyGameBall.py.

Содержит функции для обработки событий клавиатуры, мыши и системных событий.
"""

import pygame  # pyright: ignore[reportMissingImports]
from typing import Tuple


def process_keyboard_events(
    events: list,
) -> Tuple[bool, bool]:
    """
    Обрабатывает события клавиатуры в игровом цикле.
    В авторежиме обрабатываются только ESC и QUIT для выхода.

    Args:
        events: Список событий pygame.

    Returns:
        Tuple: (running, exit_game)
        running: Продолжать ли игровой цикл
        exit_game: Выход из игры
    """
    running = True
    exit_game = False

    for event in events:
        if event.type == pygame.QUIT:
            # QUIT всегда закрывает приложение немедленно
            running = False
            exit_game = True
            break  # Выходим из игрового цикла
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC всегда закрывает приложение немедленно
                running = False
                exit_game = True
                break  # Выходим из игрового цикла

    return running, exit_game
