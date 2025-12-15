"""
Модуль отрисовки игры для PyGameBall.py.

Содержит функции для отрисовки игровых объектов, UI и обновления экрана.
"""

import pygame
from typing import Optional, Any

try:
    from .game_config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
    from .game_models import Ball, Paddle
    from .game_rendering import draw_bricks, draw_hud, draw_start_hint
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
    from game.game_models import Ball, Paddle
    from game.game_rendering import draw_bricks, draw_hud, draw_start_hint
    from ai.ai_player import AIPlayer


def render_game_frame(
    screen: pygame.Surface,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    clock: pygame.time.Clock,
    frame_counter: int,
    game_started: bool,
    training_mode: bool,
    training_rounds: int,
    ai_player: Optional[AIPlayer],
    logger: Any,
) -> None:
    """
    Отрисовывает один кадр игры.
    
    Args:
        screen: Поверхность pygame для отрисовки
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Количество жизней
        font: Шрифт для текста
        big_font: Большой шрифт для заголовков
        clock: Объект clock для управления FPS
        frame_counter: Счетчик кадров
        game_started: Флаг запуска игры
        training_mode: Режим обучения
        training_rounds: Количество раундов обучения
        ai_player: Объект AI игрока
        logger: Логгер
    """
    # Отладочное сообщение только в первых 3 кадрах
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Конец блока if not game_over, переходим к отрисовке")
        logger.debug(f"[AI DEBUG] Начинаем отрисовку, game_over=False, bricks={len(bricks) if 'bricks' in locals() else 'N/A'}")
    
    # КРИТИЧНО: Отрисовка игры
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Вызываем screen.fill()...")
    screen.fill((10, 10, 30))  # Темно-синий фон
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] screen.fill() завершен")
    draw_bricks(screen, bricks)  # Отрисовка кубиков
    
    # Отрисовка платформы с цветными секциями для подсказки направления отскока
    left_rect = pygame.Rect(
        paddle.rect.x, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height
    )
    pygame.draw.rect(
        screen, (255, 0, 0), left_rect
    )  # Красный для отскока влево
    mid_rect = pygame.Rect(
        paddle.rect.x + paddle.rect.width // 3,
        paddle.rect.y,
        paddle.rect.width // 3,
        paddle.rect.height,
    )
    pygame.draw.rect(
        screen, (240, 240, 240), mid_rect
    )  # Белый для прямого отскока
    right_rect = pygame.Rect(
        paddle.rect.x + 2 * paddle.rect.width // 3,
        paddle.rect.y,
        paddle.rect.width - 2 * paddle.rect.width // 3,
        paddle.rect.height,
    )
    pygame.draw.rect(
        screen, (0, 0, 255), right_rect
    )  # Синий для отскока вправо
    pygame.draw.ellipse(screen, (230, 90, 90), ball.rect)

    # Визуализация отладочной информации AI системы
    if training_mode and ai_player is not None:
        ai_player.visualize_debug_info(screen)

    draw_hud(
        screen,
        score,
        lives_left,
        font,
        ball,
        training_mode,
        ai_player,
    )

    if not game_started:
        if training_mode:
            # В режиме обучения показываем специальную подсказку
            training_hint = big_font.render(
                f"РЕЖИМ ОБУЧЕНИЯ | Раунд: {training_rounds + 1}",
                True,
                (0, 255, 255),
            )
            training_rect = training_hint.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            )
            screen.blit(training_hint, training_rect)
        else:
            draw_start_hint(screen, big_font)

    pygame.display.flip()
    clock.tick(FPS)
    
    # Отладочное сообщение только в первом кадре (только в файл, не в консоль)
    if frame_counter == 1:
        logger.debug(f"[AI DEBUG] Первый кадр отрисован, bricks={len(bricks)}, paddle.x={paddle.rect.x}, ball.x={ball.rect.centerx}, game_started={game_started}")
