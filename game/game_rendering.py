"""
Функции отрисовки для игры Арканоид.
"""

from typing import List, Tuple, Optional
import pygame  # pyright: ignore[reportMissingImports]

try:
    from .game_config import (
        BRICK_COLS,
        BRICK_COLORS,
        BRICK_BORDER_COLOR,
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
    )
    from .game_models import Ball
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import (
        BRICK_COLS,
        BRICK_COLORS,
        BRICK_BORDER_COLOR,
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
    )
    from game.game_models import Ball
    from ai.ai_player import AIPlayer


def draw_bricks(screen: pygame.Surface, bricks: List[pygame.Rect]) -> None:
    """
    Отрисовывает все кирпичи на экране.
    
    Каждый ряд кирпичей имеет свой цвет из палитры. Кирпичи отрисовываются
    с цветной заливкой и темной рамкой.
    
    Args:
        screen: Поверхность pygame для отрисовки
        bricks: Список прямоугольников кирпичей для отрисовки
        
    Note:
        Для использования новой архитектуры с оптимизацией отрисовки см. game_views.BricksView
    """
    for idx, brick in enumerate(bricks):
        color = BRICK_COLORS[idx // BRICK_COLS % len(BRICK_COLORS)]
        pygame.draw.rect(screen, color, brick)
        pygame.draw.rect(screen, BRICK_BORDER_COLOR, brick, 2)


def draw_hud(
    screen: pygame.Surface,
    score: int,
    lives_left: int,
    font: pygame.font.Font,
    ball: Ball,
    training_mode: bool = False,
    ai_player: Optional[AIPlayer] = None,
) -> None:
    """
    Отрисовывает HUD (информацию о счете, жизнях и скорости).
    
    Args:
        screen: Поверхность pygame для отрисовки
        score: Текущий счет игрока
        lives_left: Количество оставшихся жизней
        font: Шрифт для отрисовки текста
        ball: Объект мяча для получения скорости
        training_mode: Режим обучения
        ai_player: Опциональный объект AI игрока
    """
    # Добавляем индикатор режима обучения
    if training_mode:
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость мяча: {ball.get_speed()} | РЕЖИМ ОБУЧЕНИЯ"
    else:
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость: {ball.get_speed()} | ↑ ↓ - скорость"

    surf = font.render(
        text,
        True,
        (255, 255, 255) if not training_mode else (255, 255, 0),
    )
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 20, 20))


def render_colored_hint(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[int, int],
    base_color: Tuple[int, int, int] = (200, 200, 200),
    key_color: Tuple[int, int, int] = (255, 255, 0),
) -> int:
    """
    Отображает подсказку с выделенными ключевыми словами цветом.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для отрисовки текста
        text: Текст подсказки
        pos: Позиция (x, y) для начала отрисовки
        base_color: Базовый цвет текста
        key_color: Цвет для ключевых слов
        
    Returns:
        Ширина отрисованного текста
    """
    words = text.split()
    x, y = pos
    key_words = ["Enter", "H", "M", "ESC", "↑", "↓", "0", "8"]

    for word in words:
        # Убираем знаки препинания для сравнения
        clean_word = word.rstrip(".,:!?")

        if clean_word in key_words:
            # Выделяем ключевое слово цветом
            color = key_color
        else:
            color = base_color

        surf = font.render(word, True, color)
        screen.blit(surf, (x, y))
        x += surf.get_width() + font.size(" ")[0]  # добавляем пробел

    return x - pos[0]  # возвращаем ширину текста


def draw_start_hint(screen: pygame.Surface, font: pygame.font.Font) -> None:
    """
    Отрисовывает подсказку для начала игры.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для отрисовки текста
    """
    text = "Для начала игры нажми ← или →"
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(surf, rect)
