"""
Модуль логики AI для PyGameBall.py.

Содержит функции для обновления состояния AI, управления платформой и обучения.
"""

import time
import pygame
from typing import Tuple, Optional, Any

try:
    from .game_config import (
        BRICK_ROWS,
        BRICK_COLS,
        FPS,
        MAX_LIVES,
        PADDLE_WIDTH,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
    from .game_models import Ball, Paddle
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import (
        BRICK_ROWS,
        BRICK_COLS,
        FPS,
        MAX_LIVES,
        PADDLE_WIDTH,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
    from game.game_models import Ball, Paddle
    from ai.ai_player import AIPlayer


def update_ai_logic(
    ai_player: AIPlayer,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_start_time: float,
    frame_counter: int,
    training_mode: bool,
    settings_manager: Any,
    logger: Any,
) -> None:
    """
    Обновляет состояние AI и обрабатывает логику обучения.
    
    Args:
        ai_player: Объект AI игрока
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        game_start_time: Время начала игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        settings_manager: Менеджер настроек
        logger: Логгер
    """
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Вызываем update_game_state...")
    ai_player.update_game_state(
        ball, paddle, bricks, score, int(game_start_time)
    )
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] update_game_state завершен")
    
    # КРИТИЧНО: Проверяем нарушение правила фиксации позиции
    # Теперь вместо перезапуска игры просто сбрасываем целевую позицию
    if hasattr(ai_player, 'separation_zone_tracker') and ai_player.separation_zone_tracker.game_restart_required:
        # Нарушение правила - сбрасываем целевую позицию вместо перезапуска игры
        if not getattr(__import__('sys'), 'frozen', False):
            print(f"[WARNING] Обнаружено нарушение правила фиксации позиции! Сбрасываем целевую позицию.")
        # Сбрасываем целевую позицию
        if hasattr(ai_player, 'target_tracker'):
            ai_player.target_tracker.reset_target_position()
        elif hasattr(ai_player.separation_zone_tracker, 'target_position_set'):
            ai_player.separation_zone_tracker.target_position_set = False
            ai_player.separation_zone_tracker.target_position = None
        # Сбрасываем флаг
        ai_player.separation_zone_tracker.game_restart_required = False
    
    # В режиме обучения обновляем статистику и управляем скоростью мяча
    if training_mode:
        # Обновляем статистику обучения
        total_bricks = (BRICK_ROWS * BRICK_COLS) - len(bricks)
        time_elapsed = time.time() - game_start_time
        lives_lost = MAX_LIVES - lives_left
        ai_player.update_training_stats(
            total_bricks, time_elapsed, lives_lost
        )

        # ИИ управляет скоростью мяча во время игры (проверяем каждые 60 кадров = 1 секунда)
        if frame_counter % FPS == 0:  # Каждую секунду (60 кадров)
            optimal_ball_speed = ai_player.get_optimal_ball_speed()
            current_ball_speed = ball.get_speed()
            if current_ball_speed != optimal_ball_speed:
                # Устанавливаем оптимальную скорость (обходя ограничение для режима обучения)
                if optimal_ball_speed > 10:
                    ball.current_speed = optimal_ball_speed
                    # Обновляем скорости движения с сохранением направления
                    if ball.vel_x != 0:
                        ball.vel_x = int(
                            ball.vel_x
                            * optimal_ball_speed
                            / max(current_ball_speed, 1)
                        )
                    if ball.vel_y != 0:
                        ball.vel_y = int(
                            abs(ball.vel_y)
                            * optimal_ball_speed
                            / max(current_ball_speed, 1)
                        ) * (1 if ball.vel_y > 0 else -1)
                else:
                    ball.set_speed(
                        optimal_ball_speed,
                        settings_manager,
                    )


def update_ai_paddle_movement(
    ai_player: AIPlayer,
    ball: Ball,
    paddle: Paddle,
    frame_counter: int,
    logger: Any,
) -> Tuple[int, int]:
    """
    Обновляет движение платформы на основе логики AI.
    
    Args:
        ai_player: Объект AI игрока
        ball: Объект мяча
        paddle: Объект платформы
        frame_counter: Счетчик кадров
        logger: Логгер
        
    Returns:
        Tuple: (movement, adjusted_speed)
        movement: Направление движения (-1, 0, 1)
        adjusted_speed: Скорректированная скорость платформы
    """
    # В режиме обучения используем адаптивную скорость платформы с разумными пределами
    ball_speed = ball.get_speed()
    base_speed = max(35, min(int(ball_speed * 2.5), 60))
    # Применяем множитель от ИИ, но ограничиваем разумными пределами
    paddle_speed_multiplier = (
        ai_player.get_optimal_paddle_speed_multiplier()
    )
    base_speed = int(base_speed * paddle_speed_multiplier)
    # Ограничиваем финальную скорость разумными пределами
    base_speed = max(35, min(base_speed, 60))
    
    # КРИТИЧНО: При малом количестве блоков увеличиваем скорость платформы
    # Но ограничиваем разумными пределами (35-60)
    # Примечание: bricks передается через update_ai_logic, но здесь не используется
    # bricks_remaining будет вычисляться в вызывающем коде
    
    # КРИТИЧНО: Платформа начинает движение когда мяч в зоне разделения
    # Правила работы:
    # 1. Мяч улетает (вверх) - платформа стоит на месте
    # 2. Мяч в зоне кубиков (выше зоны разделения) - платформа стоит на месте
    # 3. Мяч падает вниз и вошел в зону разделения - платформа начинает движение к точке падения
    # 4. Если целевая позиция уже установлена - платформа продолжает движение к ней,
    #    даже если мяч временно не в зоне разделения (например, близко к платформе)
    # Мяч движется вниз (ball.vel_y > 0)
    ball_in_separation_zone = (
        SEPARATION_ZONE_TOP <= ball.rect.centery <= SEPARATION_ZONE_BOTTOM
        and ball.vel_y > 0  # Мяч движется вниз
    )
    
    # Проверяем, установлена ли целевая позиция
    target_position_set = (
        hasattr(ai_player, 'separation_zone_tracker') and
        hasattr(ai_player.separation_zone_tracker, 'target_position_set') and
        ai_player.separation_zone_tracker.target_position_set
    )
    
    # Проверяем, что мяч не потерян (не ниже платформы)
    ball_not_lost = ball.rect.bottom <= paddle.rect.top
    
    # Начинаем движение когда мяч в зоне разделения ИЛИ если целевая позиция уже установлена
    # (это позволяет платформе завершить движение к цели, даже если мяч близко к платформе)
    # НО только если мяч не потерян
    should_move = (ball_in_separation_zone or target_position_set) and ball_not_lost
    
    # КРИТИЧНО: Логируем для диагностики проблем с движением (только в файл, не в консоль)
    if should_move and pygame.time.get_ticks() % 1000 < 16:  # Каждые ~1 секунду
        logger.debug(f"[PADDLE MOVEMENT DEBUG] ball_in_separation_zone={ball_in_separation_zone}, "
                     f"target_position_set={target_position_set}, ball_not_lost={ball_not_lost}, "
                     f"ball_y={ball.rect.centery:.1f}, paddle_x={paddle.rect.centerx:.1f}")
    
    if should_move:
        # Используем AI систему для автоматического управления
        movement = ai_player.move_paddle_towards(
            paddle.rect.centerx, int(base_speed)
        )
        
        # КРИТИЧНО: Логируем результат движения для диагностики (только в файл, не в консоль)
        if movement == 0 and target_position_set and pygame.time.get_ticks() % 1000 < 16:
            target_pos = ai_player.separation_zone_tracker.target_position if hasattr(ai_player, 'separation_zone_tracker') else None
            distance = abs(paddle.rect.centerx - target_pos) if target_pos is not None else 0
            logger.debug(f"[PADDLE MOVEMENT DEBUG] movement=0, но target_position_set=True! "
                         f"paddle_x={paddle.rect.centerx:.1f}, target_pos={target_pos}, distance={distance:.1f}")
        # Получаем скорректированную скорость от AI (с учетом адаптации)
        adjusted_speed = ai_player.get_adjusted_paddle_speed(
            int(base_speed)
        )
        
        # КРИТИЧНО: Используем адаптивную скорость для предотвращения перескакивания через цель
        # Получаем целевую позицию от AI
        target_pos = ai_player.separation_zone_tracker.target_position if hasattr(ai_player, 'separation_zone_tracker') else None
        if target_pos is not None:
            distance_to_target = abs(paddle.rect.centerx - target_pos)
            # Если платформа близко к цели (distance < speed), уменьшаем скорость
            # Это предотвращает перескакивание через цель и дергание
            if distance_to_target < adjusted_speed:
                # Двигаемся только на расстояние до цели, не больше
                adjusted_speed = max(1, int(distance_to_target))
        
        return movement, adjusted_speed
    else:
        # Если мяч не в зоне разделения - платформа остается на месте (movement = 0)
        return 0, base_speed


def calculate_paddle_speed_with_bricks(
    ball: Ball,
    bricks: list,
    ai_player: AIPlayer,
) -> int:
    """
    Вычисляет скорость платформы с учетом количества оставшихся блоков.
    
    Args:
        ball: Объект мяча
        bricks: Список кирпичей
        ai_player: Объект AI игрока
        
    Returns:
        int: Базовая скорость платформы (35-60)
    """
    # КРИТИЧНО: При малом количестве блоков увеличиваем скорость платформы
    # Но ограничиваем разумными пределами (35-60)
    try:
        bricks_remaining = len(bricks) if bricks is not None else 50
    except (NameError, TypeError):
        bricks_remaining = 50
    
    # Вычисляем базовую скорость с учетом количества блоков
    ball_speed = ball.get_speed()
    base_speed = max(35, min(int(ball_speed * 2.5), 60))
    paddle_speed_multiplier = ai_player.get_optimal_paddle_speed_multiplier()
    base_speed = int(base_speed * paddle_speed_multiplier)
    base_speed = max(35, min(base_speed, 60))
    
    if bricks_remaining <= 5:
        base_speed = min(int(base_speed * 1.2), 60)
    if bricks_remaining == 1:
        base_speed = 60
    
    return base_speed


def initialize_ai_before_game_loop(
    ai_player: AIPlayer,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    game_start_time: float,
    logger: Any,
) -> None:
    """
    Инициализирует состояние AI перед входом в основной цикл игры.
    
    Args:
        ai_player: Объект AI игрока
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        game_start_time: Время начала игры
        logger: Логгер
    """
    # КРИТИЧНО: Обновляем состояние игры для AI перед входом в основной цикл
    ai_player.update_game_state(
        ball, paddle, bricks, score, int(game_start_time)
    )
    # Логируем обновление состояния (только в файл, не в консоль)
    logger.debug(f"[AI DEBUG] Состояние игры обновлено для AI перед входом в цикл")
