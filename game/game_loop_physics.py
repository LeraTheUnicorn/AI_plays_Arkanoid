"""
Модуль физики и столкновений для PyGameBall.py.

Содержит функции для обновления физики мяча, обработки столкновений и логики игры.
"""

import random
import sys
import time
from typing import Tuple, Optional, Any

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore

try:
    from .game_config import (
        BALL_SIZE,
        BRICK_COLS,
        BRICK_ROWS,
        MAX_LIVES,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
    from .game_models import Ball, Paddle
    from .game_utils import build_bricks, create_ai_player
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import (
        BALL_SIZE,
        BRICK_COLS,
        BRICK_ROWS,
        MAX_LIVES,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
    from game.game_models import Ball, Paddle
    from game.game_utils import build_bricks, create_ai_player
    from ai.ai_player import AIPlayer


def update_ball_physics(
    ball: Ball,
    paddle: Paddle,
    frame_counter: int,
    game_started: bool,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
) -> Tuple[bool, bool]:
    """
    Обновляет физику мяча и проверяет базовые условия.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        frame_counter: Счетчик кадров
        game_started: Флаг запуска игры
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        
    Returns:
        Tuple: (ball_was_at_top, should_continue)
        ball_was_at_top: Мяч был у потолка перед обновлением
        should_continue: Продолжить обработку (False если нужно пропустить кадр)
    """
    # КРИТИЧНО: Проверяем отскок от потолка БЕЗ попадания в кубики ПЕРЕД обновлением мяча
    # Это позволяет отследить отбитие в пустоту
    ball_was_at_top = ball.rect.top <= 0 and ball.vel_y < 0
    
    # Обычное обновление мяча (непрерывная проверка столкновений встроена в update)
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Вызываем ball.update()...")
    try:
        ball.update()
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] ball.update() завершен")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[ERROR] Ошибка в ball.update(): {e}")
            import traceback
            traceback.print_exc()
        raise
    
    # КРИТИЧНО: Проверяем, не попал ли мяч обратно в платформу после ball.update()
    # Это может произойти, если мяч был установлен слишком близко к платформе
    # НО: не обрабатываем, если мяч только что отскочил (предотвращаем ложные срабатывания)
    just_bounced = getattr(ball, '_just_bounced', False)
    bounce_frame = getattr(ball, '_bounce_frame', -1)
    if (ball.rect.colliderect(paddle.rect) and ball.vel_y > 0 
        and not (just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1))):
        # Мяч попал обратно в платформу - принудительно перемещаем его выше
        ball_radius = BALL_SIZE // 2
        min_distance = abs(ball.vel_y) + 15  # Скорость + запас
        ball.rect.centery = paddle.rect.top - ball_radius - min_distance
        # Убеждаемся, что мяч движется вверх
        if ball.vel_y >= 0:
            ball.vel_y = -ball.get_speed()
        # Устанавливаем флаг отскока
        ball._just_bounced = True
        ball._bounce_frame = frame_counter
    
    # Сбрасываем флаг отскока через несколько кадров (чтобы не блокировать новые столкновения)
    if just_bounced and frame_counter - bounce_frame > 3:
        ball._just_bounced = False
    
    # КРИТИЧНО: Защита от vel_y == 0 во время игры (кроме начального состояния)
    # Если мяч не двигается по вертикали и игра запущена - это ошибка
    if game_started and ball.vel_y == 0:
        # Мяч застрял с нулевой скоростью - принудительно запускаем его
        ball.vel_y = -ball.get_speed()
        # Логируем для диагностики
        if training_mode and ai_player is not None:
            ai_player.performance_logger.log_ball_paddle_positions(
                ball.rect.centerx,
                ball.rect.centery,
                ball.vel_x,
                ball.vel_y,
                paddle.rect.x,
                paddle.rect.y,
                paddle.rect.width,
                paddle.rect.height,
                "VEL_Y_ZERO_FIXED"
            )
    
    # КРИТИЧНО: Логируем координаты мяча и платформы для диагностики
    # Логируем каждый 10-й кадр для экономии, НО всегда логируем при обнаружении прилипания
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Проверяем логирование координат...")
    should_log = False
    if training_mode:
        # Логируем каждый 10-й кадр или при обнаружении прилипания
        if frame_counter % 10 == 0:
            should_log = True
        # Также проверяем возможное прилипание каждый кадр (для детекции)
        elif ball.rect.colliderect(paddle.rect) and abs(ball.vel_y) < 0.1:
            # Возможное прилипание - логируем для анализа
            should_log = True
    
    if should_log and ai_player is not None:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Вызываем log_ball_paddle_positions...")
        try:
            ai_player.performance_logger.log_ball_paddle_positions(
                ball.rect.centerx,
                ball.rect.centery,
                ball.vel_x,
                ball.vel_y,
                paddle.rect.x,
                paddle.rect.y,
                paddle.rect.width,
                paddle.rect.height,
                "frame_update"
            )
            if frame_counter <= 3:
                logger.debug(f"[AI DEBUG] log_ball_paddle_positions завершен")
        except Exception as e:
            if not getattr(sys, "frozen", False):
                print(f"[ERROR] Ошибка в log_ball_paddle_positions: {e}")
    
    # КРИТИЧНО: После обновления проверяем, отскочил ли мяч от потолка
    # Если мяч был у потолка и теперь движется вниз - это отскок от потолка
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Проверяем отскок от потолка...")
    if ball_was_at_top and ball.vel_y > 0:
        # Мяч отскочил от потолка - проверяем, попадет ли он в кубики
        # Если в следующем кадре не будет попадания в кубик - это отбитие в пустоту
        if training_mode and ai_player is not None:
            # Увеличиваем счетчик отскоков от потолка
            ai_player.empty_bounce_tracker["ceiling_bounces"] += 1
            # Будем проверять попадание в кубики ниже
    
    return ball_was_at_top, True


def check_paddle_collisions(
    ball: Ball,
    paddle: Paddle,
    frame_counter: int,
    game_started: bool,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
) -> Tuple[bool, bool, bool]:
    """
    Проверяет столкновения мяча с платформой.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        frame_counter: Счетчик кадров
        game_started: Флаг запуска игры
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        
    Returns:
        Tuple: (ball_hits_paddle_top, ball_hits_paddle_side, ball_stuck)
        ball_hits_paddle_top: Мяч попал в верхнюю поверхность платформы
        ball_hits_paddle_side: Мяч попал в боковую сторону платформы
        ball_stuck: Мяч прилип к платформе
    """
    # КРИТИЧНО: Проверяем столкновение ТОЛЬКО с верхней поверхностью платформы
    # ВАЖНО: Проверка столкновения должна быть ДО проверки потери мяча!
    # Мяч может быть отбит только верхней поверхностью платформы
    # Если мяч попадает на боковую сторону - это потеря мяча
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Проверяем столкновения с платформой...")
    
    # КРИТИЧНО: Проверяем столкновение ТОЛЬКО с верхней поверхностью платформы
    # Верхняя поверхность: мяч должен быть по горизонтали в пределах платформы
    # и нижняя часть мяча должна касаться верхней части платформы
    # Боковое столкновение: мяч касается боковой стороны платформы (левой или правой)
    
    # Проверяем, попадает ли мяч в верхнюю поверхность платформы
    # Условия для верхней поверхности:
    # 1. Мяч движется вниз (vel_y > 0)
    # 2. Центр мяча по горизонтали в пределах платформы (с небольшим запасом)
    # 3. Нижняя часть мяча касается верхней части платформы
    # 4. Мяч НЕ находится слишком глубоко внутри платформы (не боковой удар)
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Вычисляем ball_hits_paddle_top...")
    try:
        # КРИТИЧНО: Проверяем, не отскочил ли мяч только что (предотвращаем повторную обработку)
        just_bounced = getattr(ball, '_just_bounced', False)
        bounce_frame = getattr(ball, '_bounce_frame', -1)
        # Если мяч отскочил в текущем или предыдущем кадре, не обрабатываем столкновение
        if just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1):
            ball_hits_paddle_top = False
        else:
            ball_hits_paddle_top = (
                ball.rect.colliderect(paddle.rect) 
                and ball.vel_y > 0  # Мяч движется вниз
                and paddle.rect.left - 5 <= ball.rect.centerx <= paddle.rect.right + 5  # Мяч по горизонтали в пределах платформы (с запасом 5px)
                and ball.rect.bottom >= paddle.rect.top  # Нижняя часть мяча касается или ниже верхней части платформы
                and ball.rect.bottom <= paddle.rect.top + 15  # Мяч в пределах 15 пикселей от верха платформы
                and ball.rect.top < paddle.rect.top + 10  # КРИТИЧНО: Мяч не слишком глубоко внутри платформы (верхняя часть мяча не ниже 10px от верха платформы)
            )
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] ball_hits_paddle_top={ball_hits_paddle_top}")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[ERROR] Ошибка в вычислении ball_hits_paddle_top: {e}")
            import traceback
            traceback.print_exc()
        raise
    
    # Проверяем боковое столкновение - это потеря мяча
    # Боковое столкновение: мяч касается платформы, но НЕ попадает в верхнюю поверхность
    # Это происходит, когда мяч касается левой или правой стороны платформы
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Вычисляем ball_hits_paddle_side...")
    try:
        ball_hits_paddle_side = (
            ball.rect.colliderect(paddle.rect)
            and ball.vel_y > 0
            and not ball_hits_paddle_top  # Не верхняя поверхность
            and (
                # Мяч касается левой стороны платформы
                (ball.rect.right >= paddle.rect.left and ball.rect.right <= paddle.rect.left + 10 and ball.rect.centerx < paddle.rect.left)
                or
                # Мяч касается правой стороны платформы
                (ball.rect.left <= paddle.rect.right and ball.rect.left >= paddle.rect.right - 10 and ball.rect.centerx > paddle.rect.right)
                or
                # Мяч полностью сбоку от платформы (не попадает в верхнюю поверхность)
                (ball.rect.bottom < paddle.rect.top and (ball.rect.centerx < paddle.rect.left or ball.rect.centerx > paddle.rect.right))
            )
        )
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] ball_hits_paddle_side={ball_hits_paddle_side}")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[ERROR] Ошибка в вычислении ball_hits_paddle_side: {e}")
            import traceback
            traceback.print_exc()
        raise
    
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Проверяем условия ball_hits_paddle_side и ball_hits_paddle_top...")
        try:
            logger.debug(f"[AI DEBUG] ball_hits_paddle_side={ball_hits_paddle_side}, ball_hits_paddle_top={ball_hits_paddle_top}")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при выводе значений: {e}")
            logger.debug(f"[AI DEBUG] ball_hits_paddle_side type: {type(ball_hits_paddle_side) if 'ball_hits_paddle_side' in locals() else 'NOT DEFINED'}")
            logger.debug(f"[AI DEBUG] ball_hits_paddle_top type: {type(ball_hits_paddle_top) if 'ball_hits_paddle_top' in locals() else 'NOT DEFINED'}")
    
    # КРИТИЧНО: Проверяем, что мяч не "прилип" к платформе
    # Если мяч находится слишком близко к платформе и не движется вниз - это ошибка
    # Это может произойти после бокового удара или других ошибок координат
    # Улучшенная проверка: мяч считается "прилипшим", если он внутри платформы или слишком близко
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] ball_hits_paddle_side=False, проверяем прилипание мяча...")
    try:
        # КРИТИЧНО: Прилипание определяется только если мяч ВНУТРИ платформы и НЕ движется
        # Не проверяем прилипание, если мяч просто находится над платформой и движется вверх - это нормально
        # КРИТИЧНО: Прилипание определяется только если мяч ВНУТРИ платформы и НЕ движется
        # НО: не проверяем прилипание, если игра только что запущена (game_started=True, но мяч еще не двигался)
        ball_stuck = (
            ball.rect.colliderect(paddle.rect)  # Мяч ВНУТРИ платформы (пересекается с ней)
            and ball.vel_y == 0  # КРИТИЧНО: Мяч неподвижен по вертикали (vel_y == 0)
            and not ball_hits_paddle_top  # Не обрабатываем, если это нормальный отскок
            and game_started  # КРИТИЧНО: Игра должна быть запущена (не начальное состояние ожидания)
        )
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] ball_stuck={ball_stuck}")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[ERROR] Ошибка в вычислении ball_stuck: {e}")
            import traceback
            traceback.print_exc()
        ball_stuck = False
    
    return ball_hits_paddle_top, ball_hits_paddle_side, ball_stuck


def handle_paddle_top_bounce(
    ball: Ball,
    paddle: Paddle,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    bricks: list,
) -> None:
    """
    Обрабатывает отскок мяча от верхней поверхности платформы.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        bricks: Список кирпичей
    """
    # КРИТИЧНО: Логируем столкновение с верхней поверхностью платформы
    if training_mode and ai_player is not None:
        ai_player.performance_logger.log_ball_paddle_positions(
            ball.rect.centerx,
            ball.rect.centery,
            ball.vel_x,
            ball.vel_y,
            paddle.rect.x,
            paddle.rect.y,
            paddle.rect.width,
            paddle.rect.height,
            "PADDLE_TOP_HIT"
        )
    
    # КРИТИЧНО: Сначала вычисляем и устанавливаем скорости, ПОТОМ корректируем позицию
    # Это важно, чтобы мяч начал двигаться в правильном направлении ДО корректировки позиции
    
    # Вычисляем точное смещение от центра платформы
    paddle_center = paddle.rect.centerx
    ball_center = ball.rect.centerx
    offset = (ball_center - paddle_center) / (paddle.rect.width / 2)

    # Ограничиваем offset в диапазоне [-1, 1]
    offset = max(-1.0, min(1.0, offset))

    # ✅ ДОБАВЛЕНО: Логирование фактической и предсказанной позиций при успешном отскоке
    if training_mode and ai_player is not None:
        try:
            # Получаем предсказанную позицию приземления
            predicted_landing_x = None
            if (hasattr(ai_player, 'trajectory_predictor') and 
                hasattr(ai_player, 'current_game_state') and 
                ai_player.current_game_state is not None):
                try:
                    intersection_point = ai_player.trajectory_predictor.predict_paddle_intersection(
                        ai_player.current_game_state,
                        paddle.rect.centery
                    )
                    if intersection_point:
                        predicted_landing_x = intersection_point.x
                except:
                    # Если predict_paddle_intersection не работает, используем _predict_exact_landing_position
                    try:
                        predicted_landing_x = ai_player._predict_exact_landing_position()
                    except:
                        pass
            
            # Фактическая позиция мяча при отскоке
            actual_ball_x = ball.rect.centerx
            actual_paddle_x = paddle.rect.centerx
            
            # Логируем сравнение
            if predicted_landing_x is not None:
                prediction_error = abs(actual_ball_x - predicted_landing_x)
                logger.info(
                    f"[BALL BOUNCE SUCCESS] ✅ Мяч успешно отскочил от платформы! "
                    f"Фактическая позиция мяча: {actual_ball_x:.1f}px, "
                    f"Предсказанная позиция: {predicted_landing_x:.1f}px, "
                    f"Ошибка предсказания: {prediction_error:.1f}px, "
                    f"Позиция платформы: {actual_paddle_x:.1f}px, "
                    f"Смещение от центра: {offset:.2f}"
                )
            else:
                logger.info(
                    f"[BALL BOUNCE SUCCESS] ✅ Мяч успешно отскочил от платформы! "
                    f"Фактическая позиция мяча: {actual_ball_x:.1f}px, "
                    f"Предсказанная позиция: НЕ ДОСТУПНА, "
                    f"Позиция платформы: {actual_paddle_x:.1f}px, "
                    f"Смещение от центра: {offset:.2f}"
                )
        except Exception as e:
            # Не блокируем игру при ошибке логирования
            logger.debug(f"[BALL BOUNCE LOG ERROR] Ошибка логирования: {e}")
    
    # Устанавливаем новые скорости ПЕРВЫМ ДЕЛОМ
    ball.bounce_vertical()
    # КРИТИЧНО: Убеждаемся, что мяч движется вверх (vel_y < 0)
    if ball.vel_y >= 0:
        ball.vel_y = -ball.get_speed()
    ball.vel_x = int(offset * ball.get_speed())
    
    # ТЕПЕРЬ корректируем позицию мяча, чтобы он был выше платформы
    # Используем centery для согласованности с методом update()
    ball_radius = BALL_SIZE // 2
    # КРИТИЧНО: Устанавливаем мяч достаточно далеко от платформы
    # Расстояние должно быть больше скорости мяча, чтобы в следующем кадре мяч не попал обратно
    # Минимум: скорость мяча + запас 10 пикселей
    min_distance = abs(ball.vel_y) + 10  # Скорость + запас
    ball.rect.centery = paddle.rect.top - ball_radius - min_distance
    
    # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
    if ball.rect.colliderect(paddle.rect):
        # Если мяч все еще внутри платформы, перемещаем его еще выше
        ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 10)
    
    # КРИТИЧНО: Убеждаемся, что нижняя часть мяча выше верхней части платформы
    if ball.rect.bottom >= paddle.rect.top:
        ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 5)
    
    # КРИТИЧНО: Устанавливаем флаг, что мяч только что отскочил
    # Это предотвратит повторную обработку столкновения в следующем кадре
    ball._just_bounced = True
    if not hasattr(ball, '_bounce_frame'):
        ball._bounce_frame = 0
    ball._bounce_frame = frame_counter

    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Предотвращение зацикливания
    # Если offset слишком мал, принудительно устанавливаем значительное горизонтальное движение
    min_horizontal_speed = max(
        2, ball.get_speed() // 2
    )  # Минимум 2 пикселя или половина скорости
    if abs(ball.vel_x) < min_horizontal_speed:
        # Принудительно устанавливаем направление в сторону от текущего положения
        if ball.rect.centerx < SCREEN_WIDTH // 2:
            ball.vel_x = min_horizontal_speed  # Двигаемся вправо
        else:
            ball.vel_x = -min_horizontal_speed  # Двигаемся влево

        # Добавляем небольшую случайность для разнообразия
        ball.vel_x += random.choice([-1, 0, 1])

    # Дополнительная защита от зацикливания - проверяем, не была ли предыдущая скорость слишком малой
    # Если предыдущая горизонтальная скорость была очень малой, а новая тоже
    if not hasattr(ball, '_last_vel_x'):
        ball._last_vel_x = 0
    if abs(ball._last_vel_x) <= 1 and abs(ball.vel_x) <= 1:
        # Принудительно меняем направление
        ball.vel_x = random.choice(
            [-min_horizontal_speed, min_horizontal_speed]
        )

    # Сохраняем текущую скорость для следующей проверки
    ball._last_vel_x = ball.vel_x

    # Ограничиваем горизонтальную скорость (но оставляем место для мин. скорости)
    max_horizontal = ball.get_speed()
    ball.vel_x = max(
        -max_horizontal, min(max_horizontal, ball.vel_x)
    )
    
    # КРИТИЧНО: Финальная проверка - убеждаемся, что мяч находится выше платформы и движется вверх
    # Проверяем несколько раз, чтобы гарантировать, что мяч не пересекается с платформой
    max_attempts = 5
    for attempt in range(max_attempts):
        if ball.rect.colliderect(paddle.rect) or ball.rect.bottom >= paddle.rect.top:
            # Если мяч все еще пересекается с платформой, перемещаем его еще выше
            ball.rect.centery = paddle.rect.top - ball_radius - (25 + attempt * 5)
        else:
            break
    
    # КРИТИЧНО: Убеждаемся, что мяч движется вверх с достаточной скоростью
    # НИКОГДА не допускаем vel_y == 0 после отскока (кроме начального состояния)
    if ball.vel_y == 0:
        # КРИТИЧНО: Если vel_y == 0, это ошибка - устанавливаем скорость вверх
        ball.vel_y = -ball.get_speed()
    elif ball.vel_y >= 0:
        ball.vel_y = -ball.get_speed()
    # Дополнительная проверка: если скорость слишком мала, увеличиваем её
    if abs(ball.vel_y) < ball.get_speed():
        ball.vel_y = -ball.get_speed()
    
    # Обучаем AI на результате отскока
    if training_mode and ai_player is not None:
        ai_result = {
            "action_type": "paddle_bounce",
            "success": True,  # Отскок от платформы всегда успешен
            "confidence": 0.8,
            "movement_distance": abs(offset * paddle.rect.width),
            "ball_speed": ball.get_speed(),
            "remaining_bricks": len(bricks),
        }
        ai_player.learn_from_result(ai_result)
        # КРИТИЧНО: Сбрасываем отслеживание зоны разделения после отскока
        ai_player._reevaluate_after_bounce()


def handle_ball_stuck(
    ball: Ball,
    paddle: Paddle,
    frame_counter: int,
    game_started: bool,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
) -> None:
    """
    Обрабатывает прилипание мяча к платформе.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        frame_counter: Счетчик кадров
        game_started: Флаг запуска игры
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
    """
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] Мяч прилип! Обрабатываем...")
    # КРИТИЧНО: Логируем прилипание мяча для диагностики
    if training_mode and ai_player is not None:
        ai_player.performance_logger.log_ball_paddle_positions(
            ball.rect.centerx,
            ball.rect.centery,
            ball.vel_x,
            ball.vel_y,
            paddle.rect.x,
            paddle.rect.y,
            paddle.rect.width,
            paddle.rect.height,
            "BALL_STUCK_DETECTED"
        )
    
    # Мяч "прилип" к платформе - принудительно перемещаем его выше
    ball_radius = BALL_SIZE // 2
    # КРИТИЧНО: Перемещаем мяч ВЫШЕ платформы, используя centerx/centery для согласованности
    ball.rect.centery = paddle.rect.top - ball_radius - 15  # Увеличиваем расстояние для надежности
    # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
    if ball.rect.colliderect(paddle.rect):
        # Если мяч все еще внутри платформы, перемещаем его еще выше
        ball.rect.centery = paddle.rect.top - ball_radius - 25
    # Устанавливаем скорость вверх, чтобы мяч оторвался
    if ball.vel_y <= 0:
        ball.vel_y = -ball.get_speed()
    # Также устанавливаем горизонтальную скорость, чтобы мяч не оставался на месте
    if abs(ball.vel_x) < 2:
        ball.vel_x = random.choice([-ball.get_speed(), ball.get_speed()])
    # КРИТИЧНО: Убеждаемся, что координаты согласованы (используем только centerx/centery)
    # Не используем x/y напрямую, чтобы избежать конфликтов координат
    
    # КРИТИЧНО: Логируем исправление прилипания
    if training_mode and ai_player is not None:
        ai_player.performance_logger.log_ball_paddle_positions(
            ball.rect.centerx,
            ball.rect.centery,
            ball.vel_x,
            ball.vel_y,
            paddle.rect.x,
            paddle.rect.y,
            paddle.rect.width,
            paddle.rect.height,
            "BALL_STUCK_FIXED"
        )


def check_brick_collisions(
    ball: Ball,
    bricks: list,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
) -> Tuple[int, Optional[Any]]:
    """
    Проверяет столкновения мяча с кирпичами.
    
    Args:
        ball: Объект мяча
        bricks: Список кирпичей
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        
    Returns:
        Tuple: (score_increase, destroyed_brick)
        score_increase: Увеличение счета (1 если кирпич уничтожен, 0 если нет)
        destroyed_brick: Уничтоженный кирпич или None
    """
    # Оптимизация: проверяем столкновения только если есть кирпичи
    # и мяч находится в области кирпичей (выше зоны разделения)
    hit_index = -1
    if bricks and ball.rect.bottom <= SEPARATION_ZONE_TOP + 50:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Проверяем столкновения с кубиками...")
        try:
            hit_index = ball.rect.collidelist(bricks)
            if frame_counter <= 3:
                logger.debug(f"[AI DEBUG] hit_index={hit_index}")
        except Exception as e:
            if not getattr(sys, "frozen", False):
                print(f"[ERROR] Ошибка в collidelist: {e}")
                import traceback
                traceback.print_exc()
            hit_index = -1
    
    if hit_index != -1:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Попадание в кубик! hit_index={hit_index}")
        ball.bounce_vertical()
        destroyed_brick = bricks.pop(hit_index)

        # КРИТИЧНО: При попадании в кубик сбрасываем счетчик отбитий в пустоту
        if training_mode and ai_player is not None:
            ai_player.empty_bounce_tracker["consecutive_empty_bounces"] = 0
            ai_player.empty_bounce_tracker["ceiling_bounces"] = 0

        # Обучаем AI на результате попадания в кубик
        if training_mode and ai_player is not None:
            try:
                ai_result = {
                    "action_type": "brick_hit",
                    "success": True,
                    "confidence": 1.0,
                    "bricks_destroyed": [
                        {"x": destroyed_brick.x, "y": destroyed_brick.y}
                    ],
                    "remaining_bricks": len(bricks),
                    "ball_speed": ball.get_speed(),
                }
                ai_player.learn_from_result(ai_result)
            except Exception as e:
                if not getattr(sys, "frozen", False):
                    print(f"[ERROR] Ошибка при обучении AI: {e}")
                    import traceback
                    traceback.print_exc()
        
        return 1, destroyed_brick
    else:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Столкновений с кубиками нет")
        # КРИТИЧНО: Мяч не попал в кубики - проверяем, был ли отскок от потолка
        # Если был отскок от потолка и мяч не попал в кубики - это отбитие в пустоту
        if training_mode and ai_player is not None:
            ceiling_bounces = ai_player.empty_bounce_tracker.get("ceiling_bounces", 0) or 0
            if ceiling_bounces > 0:
                # Мяч отскочил от потолка и не попал в кубики - увеличиваем счетчик
                ai_player.empty_bounce_tracker["consecutive_empty_bounces"] += 1
                # Логируем отбитие в пустоту (paddle не нужен для этой функции)
                brick_coords_count = len(ai_player.targeting_system.brick_coordinates if hasattr(ai_player, 'targeting_system') else [])
                # Примечание: paddle не передается в эту функцию, поэтому логирование движения пропущено
                # Сбрасываем счетчик отскоков от потолка для следующей проверки
                ai_player.empty_bounce_tracker["ceiling_bounces"] = 0
        
        return 0, None


def handle_ball_loss(
    ball: Ball,
    paddle: Paddle,
    ball_hits_paddle_top: bool,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    bricks: list,
) -> Tuple[bool, bool]:
    """
    Обрабатывает потерю мяча (мяч ниже платформы).
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        ball_hits_paddle_top: Мяч попал в верхнюю поверхность платформы
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        bricks: Список кирпичей
        
    Returns:
        Tuple: (ball_lost, should_reset_ball)
        ball_lost: Мяч потерян (True если мяч ниже платформы)
        should_reset_ball: Нужно сбросить мяч (True если нужно сбросить позицию)
    """
    # КРИТИЧНО: Проверяем потерю мяча ПОСЛЕ проверки столкновения с платформой
    # Если мяч ниже верхней границы платформы И не было столкновения - он потерян
    if ball.rect.bottom > paddle.rect.top and not ball_hits_paddle_top:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Мяч потерян! Обрабатываем...")
        
        # КРИТИЧНО: Подробное логирование потери мяча для диагностики
        if training_mode and ai_player is not None:
            if not getattr(sys, "frozen", False):
                # Получаем информацию о состоянии для диагностики
                ball_x = ball.rect.centerx
                ball_y = ball.rect.centery
                ball_bottom = ball.rect.bottom
                paddle_x = paddle.rect.centerx
                paddle_top = paddle.rect.top
                paddle_left = paddle.rect.left
                paddle_right = paddle.rect.right
                ball_vel_x = ball.vel_x
                ball_vel_y = ball.vel_y
                ball_speed = ball.get_speed()
                
                # Получаем информацию от AI о целевой позиции
                optimal_x = ai_player.get_optimal_paddle_position() if hasattr(ai_player, 'get_optimal_paddle_position') else paddle_x
                distance_to_optimal = abs(paddle_x - optimal_x) if optimal_x is not None else 0
                
                # Получаем предсказанную позицию приземления мяча
                predicted_landing_x = None
                prediction_error = None
                try:
                    if (hasattr(ai_player, 'trajectory_predictor') and 
                        hasattr(ai_player, 'current_game_state')):
                        current_state = ai_player.current_game_state
                        if current_state is not None:
                            try:
                                intersection_point = ai_player.trajectory_predictor.predict_paddle_intersection(
                                    current_state,
                                    paddle.rect.centery
                                )
                                if intersection_point:
                                    predicted_landing_x = intersection_point.x
                                    prediction_error = abs(ball_x - predicted_landing_x)
                            except:
                                try:
                                    if hasattr(ai_player, '_predict_exact_landing_position'):
                                        predicted_landing_x = ai_player._predict_exact_landing_position()
                                        prediction_error = abs(ball_x - predicted_landing_x)
                                except:
                                    pass
                except:
                    pass
                
                # Получаем информацию о зонах
                separation_zone_start = ai_player.separation_zone_tracker.separation_zone_start if hasattr(ai_player, 'separation_zone_tracker') else 226
                paddle_zone_start = ai_player.separation_zone_tracker.paddle_zone_start if hasattr(ai_player, 'separation_zone_tracker') else 540
                
                # Получаем информацию о скорости платформы
                base_speed = PADDLE_SPEED
                adjusted_speed = ai_player.get_adjusted_paddle_speed(base_speed) if hasattr(ai_player, 'get_adjusted_paddle_speed') else base_speed
                
                # Рассчитываем, где должна была быть платформа
                ball_was_in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start
                
                # Рассчитываем расстояние от мяча до платформы по горизонтали
                horizontal_distance = abs(ball_x - paddle_x)
                
                # Определяем, в какую зону относительно платформы находится мяч
                paddle_zone_size = PADDLE_WIDTH / 3
                ball_offset_from_paddle_center = ball_x - paddle_x
                if ball_offset_from_paddle_center < -paddle_zone_size:
                    ball_zone = "LEFT (слева от платформы)"
                elif ball_offset_from_paddle_center > paddle_zone_size:
                    ball_zone = "RIGHT (справа от платформы)"
                else:
                    ball_zone = "CENTER (над платформой)"
                
                # Проверяем, действительно ли мяч попал в платформу
                ball_hit_paddle = (paddle_left <= ball_x <= paddle_right and 
                                  ball_bottom >= paddle_top and 
                                  ball_bottom <= paddle_top + 5)
                
                print(f"[BALL LOST] ========== ДИАГНОСТИКА ПОТЕРИ МЯЧА ==========")
                print(f"  Мяч: pos=({ball_x:.1f}, {ball_y:.1f}) bottom={ball_bottom:.1f} vel=({ball_vel_x:.1f}, {ball_vel_y:.1f}) speed={ball_speed:.1f}")
                print(f"  Платформа: center_x={paddle_x:.1f} top={paddle_top:.1f} left={paddle_left:.1f} right={paddle_right:.1f}")
                print(f"  Расстояние: horizontal={horizontal_distance:.1f}px vertical={ball_bottom - paddle_top:.1f}px")
                print(f"  Мяч относительно платформы: {ball_zone} (offset={ball_offset_from_paddle_center:.1f}px)")
                print(f"  Мяч ударился о платформу: {ball_hit_paddle} (если False - мяч пролетел мимо)")
                print(f"  Целевая позиция AI: optimal_x={optimal_x:.1f} distance_to_optimal={distance_to_optimal:.1f}px")
                if predicted_landing_x is not None:
                    print(f"  🔴 ПРЕДСКАЗАНИЕ: Предсказанная позиция приземления: {predicted_landing_x:.1f}px")
                    print(f"  🔴 ПРЕДСКАЗАНИЕ: Фактическая позиция мяча: {ball_x:.1f}px")
                    print(f"  🔴 ПРЕДСКАЗАНИЕ: Ошибка предсказания: {prediction_error:.1f}px")
                    print(f"  🔴 ПРЕДСКАЗАНИЕ: Мяч пролетел мимо на: {abs(ball_x - paddle_x):.1f}px от центра платформы")
                else:
                    print(f"  🔴 ПРЕДСКАЗАНИЕ: Предсказанная позиция НЕ ДОСТУПНА")
                print(f"  Скорость платформы: base={base_speed} adjusted={adjusted_speed}")
                print(f"  Зоны: separation_start={separation_zone_start} paddle_start={paddle_zone_start} ball_was_in_zone={ball_was_in_separation_zone}")
                print(f"  Целевая позиция установлена: {ai_player.separation_zone_tracker.target_position_set if hasattr(ai_player, 'separation_zone_tracker') else False}")
                if hasattr(ai_player, 'separation_zone_tracker') and ai_player.separation_zone_tracker.target_position:
                    target_pos = ai_player.separation_zone_tracker.target_position
                    if target_pos is not None:
                        print(f"  Сохраненная целевая позиция: {target_pos:.1f} distance={abs(paddle_x - target_pos):.1f}px")
                print(f"========================================================")
                
                # Логирование в файл для анализа
                if hasattr(ai_player, '_logger'):
                    ai_player._logger.warning(
                        f"[BALL LOST PREDICTION] "
                        f"Фактическая позиция мяча: {ball_x:.1f}px, "
                        f"Предсказанная позиция: {predicted_landing_x:.1f}px (ошибка: {prediction_error:.1f}px), "
                        f"Позиция платформы: {paddle_x:.1f}px, "
                        f"Целевая позиция: {optimal_x:.1f}px, "
                        f"Мяч пролетел мимо на: {abs(ball_x - paddle_x):.1f}px"
                    )
        
        # Обучаем AI на результате потери мяча
        if training_mode and ai_player is not None:
            ai_result = {
                "action_type": "ball_lost",
                "success": False,
                "confidence": 0.0,
                "ball_speed": ball.get_speed(),
                "remaining_bricks": len(bricks),
            }
            ai_player.learn_from_result(ai_result)
            ai_player._log_paddle_movement(
                paddle.rect.centerx,
                paddle.rect.centerx,
                f"ПОТЕРЯ МЯЧА: мяч ниже платформы. Мяч Y={ball.rect.bottom}, Платформа top={paddle.rect.top}",
                0.0
            )
            # КРИТИЧНО: Сбрасываем все трекеры после потери мяча
            ai_player._reset_game_state_trackers()
        
        return True, True  # Мяч потерян, нужно сбросить
    
    return False, False  # Мяч не потерян


def handle_game_restart_training(
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_start_time: float,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    settings_manager: Any,
    logger: Any,
    is_victory: bool = False,
) -> Tuple[Paddle, Ball, list, int, int, bool, bool, float]:
    """
    Обрабатывает перезапуск игры в режиме обучения.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Количество жизней
        game_start_time: Время начала игры
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        settings_manager: Менеджер настроек
        logger: Логгер
        is_victory: Победа (True) или проигрыш (False)
        
    Returns:
        Tuple: (new_paddle, new_ball, new_bricks, new_score, new_lives_left, game_over, game_started, new_game_start_time)
    """
    if not training_mode or ai_player is None:
        # В обычном режиме не перезапускаем автоматически
        return paddle, ball, bricks, score, lives_left, True, False, game_start_time
    
    # Рассчитываем время игры
    game_time_seconds = int(time.time() - game_start_time)
    
    # В режиме обучения считаем кубики за весь матч
    total_bricks_destroyed = (BRICK_ROWS * BRICK_COLS) - len(bricks)
    lives_lost = MAX_LIVES - lives_left if not is_victory else MAX_LIVES - lives_left
    
    # Обновляем финальную статистику обучения
    ai_player.update_training_stats(
        total_bricks_destroyed,
        game_time_seconds,
        MAX_LIVES if not is_victory else lives_lost,
    )
    
    # Обучаем AI на результате игры
    ai_result = {
        "action_type": "game_end",
        "success": is_victory,
        "final_score": score,
        "game_duration": game_time_seconds,
        "bricks_remaining": len(bricks) if not is_victory else 0,
        "bricks_destroyed": total_bricks_destroyed,
        "lives_lost": MAX_LIVES if not is_victory else lives_lost,
    }
    
    try:
        ai_player.learn_from_result(ai_result)
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[GAME RESTART ERROR] Ошибка в learn_from_result: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        if hasattr(ai_player, 'on_game_end'):
            ai_player.on_game_end(is_victory, score, training_mode=training_mode)
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[GAME RESTART ERROR] Ошибка в on_game_end: {e}")
            import traceback
            traceback.print_exc()
    
    # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
    ai_player._reset_game_state_trackers()
    
    # Автоматически перезапускаем игру в режиме обучения
    new_paddle = Paddle()
    new_ball = Ball()
    optimal_ball_speed = ai_player.get_optimal_ball_speed()
    if optimal_ball_speed > 10:
        new_ball.current_speed = optimal_ball_speed
    else:
        new_ball.set_speed(optimal_ball_speed, settings_manager)
    new_ball.reset(new_paddle.rect)
    new_ball.vel_y = 0
    new_bricks = build_bricks()
    new_score = 0
    new_lives_left = MAX_LIVES  # Восстанавливаем жизни для нового матча
    game_over = False
    game_started = True  # Автоматически запускаем
    new_ball.vel_x = new_ball.get_speed()
    new_ball.vel_y = -new_ball.get_speed()
    new_game_start_time = time.time()
    
    # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
    ai_player.update_game_state(
        new_ball, new_paddle, new_bricks, new_score, int(new_game_start_time)
    )
    
    # КРИТИЧНО: Логируем перезапуск игры
    if not getattr(sys, "frozen", False):
        restart_type = "ПОБЕДА" if is_victory else "ПОРАЖЕНИЕ"
        print(f"[GAME RESTART] Игра перезапущена после {restart_type}!")
        print(f"[GAME RESTART] lives_left={new_lives_left}, game_over={game_over}, game_started={game_started}")
        print(f"[GAME RESTART] ball.vel_x={new_ball.vel_x}, ball.vel_y={new_ball.vel_y}, paddle.x={new_paddle.rect.x}, bricks={len(new_bricks)}")
    
    ai_player.performance_logger.log_ball_paddle_positions(
        new_ball.rect.centerx,
        new_ball.rect.centery,
        new_ball.vel_x,
        new_ball.vel_y,
        new_paddle.rect.x,
        new_paddle.rect.y,
        new_paddle.rect.width,
        new_paddle.rect.height,
        "GAME_RESTART_AFTER_WIN" if is_victory else "GAME_RESTART_AFTER_LOSS"
    )
    
    # Логируем начало новой игры
    if ai_player.current_game_state:
        ai_player.performance_logger.log_game_start(ai_player.current_game_state)
    
    return new_paddle, new_ball, new_bricks, new_score, new_lives_left, game_over, game_started, new_game_start_time


def handle_paddle_side_collision(
    ball: Ball,
    paddle: Paddle,
    lives_left: int,
    game_over: bool,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    bricks: list,
    score: int,
    game_start_time: float,
    settings_manager: Any,
) -> Tuple[bool, int, bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[AIPlayer], Optional[float]]:
    """
    Обрабатывает боковое столкновение мяча с платформой (потеря мяча).
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        lives_left: Текущее количество жизней
        game_over: Флаг окончания игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        bricks: Список кирпичей
        score: Текущий счет
        game_start_time: Время начала игры
        settings_manager: Менеджер настроек
        
    Returns:
        Tuple: (should_continue, new_lives_left, new_game_over, new_paddle, new_ball, new_bricks, new_score, new_ai_player, new_game_start_time)
        should_continue: Продолжить обработку кадра (False если нужно пропустить)
        new_lives_left: Новое количество жизней
        new_game_over: Новый флаг окончания игры
        new_paddle: Новая платформа (если перезапуск)
        new_ball: Новый мяч (если перезапуск)
        new_bricks: Новые кирпичи (если перезапуск)
        new_score: Новый счет (если перезапуск)
        new_ai_player: Новый AI игрок (если перезапуск)
        new_game_start_time: Новое время начала игры (если перезапуск)
    """
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] ball_hits_paddle_side=True, обрабатываем боковое столкновение")
    # Мяч попал на боковую сторону платформы - это потеря мяча
    new_lives_left = lives_left - 1
    if new_lives_left > 0:
        # КРИТИЧНО: Правильно сбрасываем мяч после бокового удара
        ball.reset(paddle.rect)
        # КРИТИЧНО: Принудительно устанавливаем мяч ВЫШЕ платформы, чтобы избежать прилипания
        ball_radius = BALL_SIZE // 2
        ball.rect.centery = paddle.rect.top - ball_radius - 5
        # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
        if ball.rect.colliderect(paddle.rect):
            ball.rect.centery = paddle.rect.top - ball_radius - 15
        # КРИТИЧНО: Сбрасываем все трекеры после бокового удара
        if training_mode and ai_player is not None:
            ai_player._reset_game_state_trackers()
        
        # Логируем потерю мяча из-за бокового удара
        if training_mode and ai_player is not None:
            ai_result = {
                "action_type": "paddle_side_hit",
                "success": False,
                "confidence": 0.0,
                "ball_speed": ball.get_speed(),
                "remaining_bricks": len(bricks),
            }
            ai_player.learn_from_result(ai_result)
            ai_player._log_paddle_movement(
                paddle.rect.centerx,
                paddle.rect.centerx,
                f"ПОТЕРЯ МЯЧА: боковой удар о платформу. Мяч X={ball.rect.centerx}, Платформа X={paddle.rect.centerx}, Платформа left={paddle.rect.left}, right={paddle.rect.right}",
                0.0
            )
        
        return True, new_lives_left, False, None, None, None, None, None, None
    else:
        # Все жизни потрачены - перезапускаем в режиме обучения
        new_game_over = True
        if training_mode and ai_player is not None:
            # Перезапускаем игру в режиме обучения
            new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, game_started, new_game_start_time = handle_game_restart_training(
                ball,
                paddle,
                bricks,
                score,
                new_lives_left,
                game_start_time,
                training_mode,
                ai_player,
                settings_manager,
                logger,
                is_victory=False,
            )
            return False, new_lives_left, new_game_over, new_paddle, new_ball, new_bricks, new_score, ai_player, new_game_start_time
        else:
            return True, new_lives_left, new_game_over, None, None, None, None, None, None


def handle_game_restart_manual(
    paddle: Paddle,
    ball: Ball,
    bricks: list,
    score: int,
    lives_left: int,
    game_over: bool,
    game_started: bool,
    settings_manager: Any,
    screen_width: int,
    screen_height: int,
    create_ai_player_func: Any,
) -> Tuple[Paddle, Ball, list, int, int, bool, bool, float, Optional[AIPlayer]]:
    """
    Обрабатывает перезапуск игры в обычном (ручном) режиме.
    
    Args:
        paddle: Объект платформы
        ball: Объект мяча
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Количество жизней
        game_over: Флаг окончания игры
        game_started: Флаг запуска игры
        settings_manager: Менеджер настроек
        screen_width: Ширина экрана
        screen_height: Высота экрана
        create_ai_player_func: Функция для создания AI игрока
        
    Returns:
        Tuple: (new_paddle, new_ball, new_bricks, new_score, new_lives_left, game_over, game_started, new_game_start_time, new_ai_player)
    """
    # Перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
    new_paddle = Paddle()
    new_ball = Ball()
    ball_speed = settings_manager.get_ball_speed()
    new_ball.set_speed(ball_speed)
    new_ball.reset(new_paddle.rect)
    new_ball.vel_y = 0
    new_bricks = build_bricks()
    new_score = 0
    new_lives_left = MAX_LIVES
    new_game_over = False
    new_game_started = False
    # Пересоздаем AI для новой игры
    new_ai_player = create_ai_player_func(
        screen_width,
        screen_height,
        debug_mode=True
    )
    new_ai_player.activate()
    # Перезапускаем отсчет времени игры
    new_game_start_time = time.time()
    
    return new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player


def handle_victory_manual(
    screen: Any,
    font: Any,
    big_font: Any,
    score: int,
    player_name: str,
    lives_left: int,
    game_start_time: float,
    highscore_manager: Any,
    settings_manager: Any,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    game_over: bool,
    game_started: bool,
    show_victory_splash_func: Any,
    show_game_results_func: Any,
    create_ai_player_func: Any,
    screen_width: int,
    screen_height: int,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer]]:
    """
    Обрабатывает победу в обычном (ручном) режиме.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        score: Текущий счет
        player_name: Имя игрока
        lives_left: Количество жизней
        game_start_time: Время начала игры
        highscore_manager: Менеджер рекордов
        settings_manager: Менеджер настроек
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        game_over: Флаг окончания игры
        game_started: Флаг запуска игры
        show_victory_splash_func: Функция показа заставки победы
        show_game_results_func: Функция показа экрана результатов
        create_ai_player_func: Функция создания AI игрока
        screen_width: Ширина экрана
        screen_height: Высота экрана
        
    Returns:
        Tuple: (should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player)
        should_exit: Выход из игры (True если нужно выйти)
        new_paddle: Новая платформа (если перезапуск)
        new_ball: Новый мяч (если перезапуск)
        new_bricks: Новые кирпичи (если перезапуск)
        new_score: Новый счет (если перезапуск)
        new_lives_left: Новое количество жизней (если перезапуск)
        new_game_over: Новый флаг окончания игры (если перезапуск)
        new_game_started: Новый флаг запуска игры (если перезапуск)
        new_game_start_time: Новое время начала игры (если перезапуск)
        new_ai_player: Новый AI игрок (если перезапуск)
    """
    new_game_over = True
    # Рассчитываем время игры и сохраняем результат
    game_time_seconds = int(time.time() - game_start_time)

    # Показываем заставку победы только в обычном режиме (с вводом имени)
    # и если у игрока остались жизни (победа)
    if lives_left > 0:
        show_victory_splash_func(screen, duration_seconds=5.0)

    # В любом режиме показываем экран результатов
    sound_enabled, restart_game, exit_game = show_game_results_func(
        screen,
        font,
        big_font,
        score,
        player_name,
        game_time_seconds,
        highscore_manager,
        settings_manager,
        ball,
    )

    # Если игрок хочет выйти из игры
    if exit_game:
        return True, None, None, None, None, None, None, None, None, None

    # Обработка перезапуска
    if restart_game:
        # Перезапускаем игру используя модуль game_loop_physics
        new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_restart_manual(
            paddle,
            ball,
            bricks,
            score,
            lives_left,
            game_over,
            game_started,
            settings_manager,
            screen_width,
            screen_height,
            create_ai_player_func,
        )
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player
    
    return False, None, None, None, None, None, new_game_over, None, None, None


def handle_all_lives_lost_after_ball_loss(
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_start_time: float,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    settings_manager: Any,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer]]:
    """
    Обрабатывает потерю всех жизней после потери мяча (ball.rect.bottom > paddle.rect.top).
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Текущее количество жизней (должно быть 0)
        game_start_time: Время начала игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        settings_manager: Менеджер настроек
        
    Returns:
        Tuple: (should_continue, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player)
        should_continue: Продолжить обработку кадра (False если нужно пропустить)
        new_paddle: Новая платформа (если перезапуск)
        new_ball: Новый мяч (если перезапуск)
        new_bricks: Новые кирпичи (если перезапуск)
        new_score: Новый счет (если перезапуск)
        new_lives_left: Новое количество жизней (если перезапуск)
        new_game_over: Новый флаг окончания игры (если перезапуск)
        new_game_started: Новый флаг запуска игры (если перезапуск)
        new_game_start_time: Новое время начала игры (если перезапуск)
        new_ai_player: Новый AI игрок (если перезапуск)
    """
    if lives_left > 0:
        return True, None, None, None, None, None, None, None, None, None
    
    # КРИТИЧНО: Логируем окончание жизней
    if training_mode:
        if not getattr(sys, "frozen", False):
            print(f"[GAME END] Все жизни потрачены (ball.rect.bottom > paddle.rect.top)! lives_left={lives_left}, training_mode={training_mode}")
    new_game_over = True
    # Рассчитываем время игры и сохраняем результат
    game_time_seconds = int(time.time() - game_start_time)

    # Обучаем AI на результате игры (проигрыш)
    if training_mode and ai_player is not None:
        # В режиме обучения считаем кубики за весь матч (пока не потратятся все жизни)
        total_bricks_destroyed = (
            BRICK_ROWS * BRICK_COLS
        ) - len(bricks)

        # Обновляем финальную статистику обучения
        ai_player.update_training_stats(
            total_bricks_destroyed,
            game_time_seconds,
            MAX_LIVES,  # Все жизни потрачены
        )

        ai_result = {
            "action_type": "game_end",
            "success": False,  # Игра проиграна
            "final_score": score,
            "game_duration": game_time_seconds,
            "bricks_remaining": len(bricks),
            "bricks_destroyed": total_bricks_destroyed,
            "lives_lost": MAX_LIVES,  # Все жизни потрачены
        }
        try:
            ai_player.learn_from_result(ai_result)
        except Exception as e:
            if not getattr(sys, "frozen", False):
                print(f"[GAME RESTART ERROR] Ошибка в learn_from_result: {e}")
                import traceback
                traceback.print_exc()
        
        try:
            if hasattr(ai_player, 'on_game_end'):
                ai_player.on_game_end(
                    False, score, training_mode=training_mode
                )
        except Exception as e:
            if not getattr(sys, "frozen", False):
                print(f"[GAME RESTART ERROR] Ошибка в on_game_end: {e}")
                import traceback
                traceback.print_exc()

    # В режиме обучения не показываем экран результатов, сразу перезапускаем
    if training_mode and ai_player is not None:
        # Перезапускаем игру в режиме обучения используя модуль game_loop_physics
        new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time = handle_game_restart_training(
            ball,
            paddle,
            bricks,
            score,
            lives_left,
            game_start_time,
            training_mode,
            ai_player,
            settings_manager,
            logger,
            is_victory=False,
        )
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, ai_player
    else:
        # В обычном режиме возвращаем флаг для показа экрана результатов
        return True, None, None, None, None, None, new_game_over, None, None, None


def apply_restart_result(
    new_paddle: Optional[Paddle],
    new_ball: Optional[Ball],
    new_bricks: Optional[list],
    new_score: Optional[int],
    new_lives_left: Optional[int],
    new_game_over: Optional[bool],
    new_game_started: Optional[bool],
    new_game_start_time: Optional[float],
    new_ai_player: Optional[AIPlayer],
    paddle: Paddle,
    ball: Ball,
    bricks: list,
    score: int,
    lives_left: int,
    game_over: bool,
    game_started: bool,
    game_start_time: float,
    ai_player: Optional[AIPlayer],
) -> Tuple[Paddle, Ball, list, int, int, bool, bool, float, Optional[AIPlayer]]:
    """
    Применяет результаты перезапуска игры.
    
    Args:
        new_paddle: Новая платформа (если перезапуск)
        new_ball: Новый мяч (если перезапуск)
        new_bricks: Новые кирпичи (если перезапуск)
        new_score: Новый счет (если перезапуск)
        new_lives_left: Новое количество жизней (если перезапуск)
        new_game_over: Новый флаг окончания игры (если перезапуск)
        new_game_started: Новый флаг запуска игры (если перезапуск)
        new_game_start_time: Новое время начала игры (если перезапуск)
        new_ai_player: Новый AI игрок (если перезапуск)
        paddle: Текущая платформа
        ball: Текущий мяч
        bricks: Текущие кирпичи
        score: Текущий счет
        lives_left: Текущее количество жизней
        game_over: Текущий флаг окончания игры
        game_started: Текущий флаг запуска игры
        game_start_time: Текущее время начала игры
        ai_player: Текущий AI игрок
        
    Returns:
        Tuple: (paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player)
    """
    if new_paddle is not None:
        return (
            new_paddle,
            new_ball,
            new_bricks,
            new_score,
            new_lives_left,
            new_game_over,
            new_game_started,
            new_game_start_time,
            new_ai_player,
        )
    return paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player


def handle_game_over_manual(
    screen: Any,
    font: Any,
    big_font: Any,
    score: int,
    player_name: str,
    game_start_time: float,
    highscore_manager: Any,
    settings_manager: Any,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    game_over: bool,
    game_started: bool,
    show_game_results_func: Any,
    create_ai_player_func: Any,
    screen_width: int,
    screen_height: int,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer]]:
    """
    Обрабатывает окончание игры в обычном (ручном) режиме.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        score: Текущий счет
        player_name: Имя игрока
        game_start_time: Время начала игры
        highscore_manager: Менеджер рекордов
        settings_manager: Менеджер настроек
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        game_over: Флаг окончания игры
        game_started: Флаг запуска игры
        show_game_results_func: Функция показа экрана результатов
        create_ai_player_func: Функция создания AI игрока
        screen_width: Ширина экрана
        screen_height: Высота экрана
        
    Returns:
        Tuple: (should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player)
        should_exit: Выход из игры (True если нужно выйти)
        new_paddle: Новая платформа (если перезапуск)
        new_ball: Новый мяч (если перезапуск)
        new_bricks: Новые кирпичи (если перезапуск)
        new_score: Новый счет (если перезапуск)
        new_lives_left: Новое количество жизней (если перезапуск)
        new_game_over: Новый флаг окончания игры (если перезапуск)
        new_game_started: Новый флаг запуска игры (если перезапуск)
        new_game_start_time: Новое время начала игры (если перезапуск)
        new_ai_player: Новый AI игрок (если перезапуск)
    """
    if not game_over:
        return False, None, None, None, None, None, None, None, None, None
    
    # Рассчитываем время игры и сохраняем результат
    game_time_seconds = int(time.time() - game_start_time)
    
    # В любом режиме показываем экран результатов
    sound_enabled, restart_game, exit_game = show_game_results_func(
        screen,
        font,
        big_font,
        score,
        player_name,
        game_time_seconds,
        highscore_manager,
        settings_manager,
        ball,
    )

    # Если игрок хочет выйти из игры
    if exit_game:
        return True, None, None, None, None, None, None, None, None, None

    # Обработка перезапуска
    if restart_game:
        # Перезапускаем игру используя модуль game_loop_physics
        new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_restart_manual(
            paddle,
            ball,
            bricks,
            score,
            MAX_LIVES,
            game_over,
            game_started,
            settings_manager,
            screen_width,
            screen_height,
            create_ai_player_func,
        )
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player
    
    return False, None, None, None, None, None, game_over, None, None, None


def position_ball_on_paddle(
    ball: Ball,
    paddle: Paddle,
    game_started: bool,
) -> None:
    """
    Позиционирует мяч на платформе, если игра не запущена.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        game_started: Флаг запуска игры
    """
    if not game_started:
        ball.rect.center = paddle.rect.midtop
        ball.rect.y -= BALL_SIZE


def handle_victory_check(
    bricks: list,
    ball: Ball,
    paddle: Paddle,
    score: int,
    lives_left: int,
    game_start_time: float,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    settings_manager: Any,
    screen: Any,
    font: Any,
    big_font: Any,
    player_name: str,
    highscore_manager: Any,
    show_victory_splash_func: Any,
    show_game_results_func: Any,
    create_ai_player_func: Any,
    screen_width: int,
    screen_height: int,
    training_rounds: int,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer], Optional[int]]:
    """
    Обрабатывает проверку победы (все кирпичи сбиты).
    
    Args:
        bricks: Список кирпичей
        ball: Объект мяча
        paddle: Объект платформы
        score: Текущий счет
        lives_left: Количество жизней
        game_start_time: Время начала игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        settings_manager: Менеджер настроек
        screen: Поверхность pygame
        font: Шрифт
        big_font: Большой шрифт
        player_name: Имя игрока
        highscore_manager: Менеджер рекордов
        show_victory_splash_func: Функция показа заставки победы
        show_game_results_func: Функция показа экрана результатов
        create_ai_player_func: Функция создания AI игрока
        screen_width: Ширина экрана
        screen_height: Высота экрана
        training_rounds: Количество раундов обучения
        
    Returns:
        Tuple: (should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds)
    """
    if bricks:
        return False, None, None, None, None, None, None, None, None, None, None
    
    game_over = True
    game_time_seconds = int(time.time() - game_start_time)
    
    # В режиме обучения не показываем экран результатов, сразу перезапускаем
    if training_mode:
        # Перезапускаем игру в режиме обучения используя модуль game_loop_physics
        new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time = handle_game_restart_training(
            ball,
            paddle,
            bricks,
            score,
            lives_left,
            game_start_time,
            training_mode,
            ai_player,
            settings_manager,
            logger,
            is_victory=True,
        )
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, ai_player, training_rounds + 1
    else:
        # Обычный режим - обрабатываем победу используя модуль game_loop_physics
        should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_victory_manual(
            screen,
            font,
            big_font,
            score,
            player_name,
            lives_left,
            game_start_time,
            highscore_manager,
            settings_manager,
            ball,
            paddle,
            bricks,
            game_over,
            True,  # game_started
            show_victory_splash_func,
            show_game_results_func,
            create_ai_player_func,
            screen_width,
            screen_height,
        )
        if should_exit:
            return True, None, None, None, None, None, None, None, None, None, None
        if new_paddle is not None:
            return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None
    
    return False, None, None, None, None, None, game_over, None, None, None, None


def process_ball_physics_and_collisions(
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_over: bool,
    game_started: bool,
    game_start_time: float,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    settings_manager: Any,
    screen: Any,
    font: Any,
    big_font: Any,
    player_name: str,
    highscore_manager: Any,
    show_victory_splash_func: Any,
    show_game_results_func: Any,
    create_ai_player_func: Any,
    screen_width: int,
    screen_height: int,
    training_rounds: int,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer], Optional[int]]:
    """
    Обрабатывает физику мяча и столкновения для одного кадра.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Количество жизней
        game_over: Флаг окончания игры
        game_started: Флаг запуска игры
        game_start_time: Время начала игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        settings_manager: Менеджер настроек
        screen: Поверхность pygame
        font: Шрифт
        big_font: Большой шрифт
        player_name: Имя игрока
        highscore_manager: Менеджер рекордов
        show_victory_splash_func: Функция показа заставки победы
        show_game_results_func: Функция показа экрана результатов
        create_ai_player_func: Функция создания AI игрока
        screen_width: Ширина экрана
        screen_height: Высота экрана
        training_rounds: Количество раундов обучения
        
    Returns:
        Tuple: (should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds)
    """
    if not game_started:
        return False, None, None, None, None, None, None, None, None, None, None
    
    # Обновляем физику мяча используя модуль game_loop_physics
    ball_was_at_top, should_continue = update_ball_physics(
        ball,
        paddle,
        frame_counter,
        game_started,
        training_mode,
        ai_player,
        logger,
    )
    if not should_continue:
        return False, None, None, None, None, None, None, None, None, None, None

    # Проверяем столкновения с платформой используя модуль game_loop_physics
    ball_hits_paddle_top, ball_hits_paddle_side, ball_stuck = check_paddle_collisions(
        ball,
        paddle,
        frame_counter,
        game_started,
        training_mode,
        ai_player,
        logger,
    )
    
    # Обрабатываем боковое столкновение используя модуль game_loop_physics
    if ball_hits_paddle_side:
        should_continue, lives_left, game_over, new_paddle, new_ball, new_bricks, new_score, new_ai_player, new_game_start_time = handle_paddle_side_collision(
            ball,
            paddle,
            lives_left,
            game_over,
            frame_counter,
            training_mode,
            ai_player,
            logger,
            bricks,
            score,
            game_start_time,
            settings_manager,
        )
        if new_paddle is not None:
            return False, new_paddle, new_ball, new_bricks, new_score, lives_left, game_over, None, new_game_start_time, new_ai_player, None
        if not should_continue:
            return False, None, None, None, None, lives_left, game_over, None, None, None, None
    
    # Обрабатываем прилипание мяча
    if ball_stuck:
        handle_ball_stuck(
            ball,
            paddle,
            frame_counter,
            game_started,
            training_mode,
            ai_player,
            logger,
        )
        return False, None, None, None, None, None, None, None, None, None, None
    
    # Обрабатываем отскок от верхней поверхности платформы
    if ball_hits_paddle_top:
        handle_paddle_top_bounce(
            ball,
            paddle,
            frame_counter,
            training_mode,
            ai_player,
            logger,
            bricks,
        )
    
    # Проверяем потерю мяча используя модуль game_loop_physics
    ball_lost, should_reset_ball = handle_ball_loss(
        ball,
        paddle,
        ball_hits_paddle_top,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        bricks,
    )
    
    if ball_lost:
        # Мяч потерян - уменьшаем жизни
        lives_left -= 1
        # КРИТИЧНО: Логируем после уменьшения жизней (только в файл, не в консоль)
        if training_mode:
            logger.info(f"[LIFE LOSS] Жизни уменьшены! lives_left={lives_left}, game_over={game_over}")
        if should_reset_ball and lives_left > 0:
            ball.reset(paddle.rect)
            ball.vel_y = 0
            return False, None, None, None, None, lives_left, False, None, None, None, None
        else:
            # Обрабатываем потерю всех жизней используя модуль game_loop_physics
            should_continue, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_all_lives_lost_after_ball_loss(
                ball,
                paddle,
                bricks,
                score,
                lives_left,
                game_start_time,
                frame_counter,
                training_mode,
                ai_player,
                logger,
                settings_manager,
            )
            if new_paddle is not None:
                return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None
            if not should_continue:
                return False, None, None, None, None, new_lives_left, new_game_over, None, None, None, None
            
            # В обычном режиме обрабатываем окончание игры используя модуль game_loop_physics
            if new_game_over and not training_mode:
                should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_over_manual(
                    screen,
                    font,
                    big_font,
                    score,
                    player_name,
                    game_start_time,
                    highscore_manager,
                    settings_manager,
                    ball,
                    paddle,
                    bricks,
                    new_game_over,
                    game_started,
                    show_game_results_func,
                    create_ai_player_func,
                    screen_width,
                    screen_height,
                )
                if should_exit:
                    return True, None, None, None, None, None, None, None, None, None, None
                if new_paddle is not None:
                    return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None
            return False, None, None, None, None, new_lives_left, new_game_over, None, None, None, None

    # Проверяем столкновения с кирпичами используя модуль game_loop_physics
    score_increase, destroyed_brick = check_brick_collisions(
        ball,
        bricks,
        frame_counter,
        training_mode,
        ai_player,
        logger,
    )
    score += score_increase
    
    # Проверяем победу используя модуль game_loop_physics
    should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds = handle_victory_check(
        bricks,
        ball,
        paddle,
        score,
        lives_left,
        game_start_time,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        settings_manager,
        screen,
        font,
        big_font,
        player_name,
        highscore_manager,
        show_victory_splash_func,
        show_game_results_func,
        create_ai_player_func,
        screen_width,
        screen_height,
        training_rounds,
    )
    if should_exit:
        return True, None, None, None, None, None, None, None, None, None, None
    if new_paddle is not None:
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds

    # Обрабатываем потерю мяча за границей экрана используя модуль game_loop_physics
    should_continue, lives_left, game_over, new_paddle, new_ball, new_bricks, new_score, new_ai_player, new_game_start_time, game_started = handle_ball_out_of_bounds(
        ball,
        paddle,
        lives_left,
        game_over,
        bricks,
        score,
        game_start_time,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        settings_manager,
    )
    if new_paddle is not None:
        return False, new_paddle, new_ball, new_bricks, new_score, lives_left, game_over, game_started, new_game_start_time, new_ai_player, None
    if not should_continue:
        return False, None, None, None, None, lives_left, game_over, game_started, None, None, None
    
    # В обычном режиме обрабатываем окончание игры используя модуль game_loop_physics
    if game_over and not training_mode:
        should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_over_manual(
            screen,
            font,
            big_font,
            score,
            player_name,
            game_start_time,
            highscore_manager,
            settings_manager,
            ball,
            paddle,
            bricks,
            game_over,
            game_started,
            show_game_results_func,
            create_ai_player_func,
            screen_width,
            screen_height,
        )
        if should_exit:
            return True, None, None, None, None, None, None, None, None, None, None
        if new_paddle is not None:
            return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None

    # Проверяем победу используя модуль game_loop_physics
    should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds = handle_victory_check(
        bricks,
        ball,
        paddle,
        score,
        lives_left,
        game_start_time,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        settings_manager,
        screen,
        font,
        big_font,
        player_name,
        highscore_manager,
        show_victory_splash_func,
        show_game_results_func,
        create_ai_player_func,
        screen_width,
        screen_height,
        training_rounds,
    )
    if should_exit:
        return True, None, None, None, None, None, None, None, None, None, None
    if new_paddle is not None:
        return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_training_rounds
    
    return False, None, None, None, score, lives_left, game_over, game_started, None, None, None


def _process_game_logic_frame_unused(
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_over: bool,
    game_started: bool,
    game_start_time: float,
    frame_counter: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    logger: Any,
    settings_manager: Any,
    keys: Any,
    screen: Any,
    font: Any,
    big_font: Any,
    player_name: str,
    highscore_manager: Any,
    show_victory_splash_func: Any,
    show_game_results_func: Any,
    create_ai_player_func: Any,
    screen_width: int,
    screen_height: int,
) -> Tuple[bool, Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[float], Optional[AIPlayer], Optional[int], Optional[int]]:
    """
    Обрабатывает игровую логику для одного кадра.
    
    Args:
        ball: Объект мяча
        paddle: Объект платформы
        bricks: Список кирпичей
        score: Текущий счет
        lives_left: Количество жизней
        game_over: Флаг окончания игры
        game_started: Флаг запуска игры
        game_start_time: Время начала игры
        frame_counter: Счетчик кадров
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        logger: Логгер
        settings_manager: Менеджер настроек
        keys: Нажатые клавиши
        screen: Поверхность pygame
        font: Шрифт
        big_font: Большой шрифт
        player_name: Имя игрока
        highscore_manager: Менеджер рекордов
        show_victory_splash_func: Функция показа заставки победы
        show_game_results_func: Функция показа экрана результатов
        create_ai_player_func: Функция создания AI игрока
        screen_width: Ширина экрана
        screen_height: Высота экрана
        
    Returns:
        Tuple: (should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, new_score, new_training_rounds)
    """
    if game_over:
        return False, None, None, None, None, None, None, None, None, None, None, None
    
    # Отладочное сообщение только в первых 3 кадрах
    if frame_counter <= 3:
        logger.debug(f"[AI DEBUG] В блоке if not game_over, обновляем состояние игры")
    
    # Обновляем логику AI используя модуль game_loop_ai
    if training_mode:
        assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
        from .game_loop_ai import (
            update_ai_logic,
            calculate_paddle_speed_with_bricks,
            update_ai_paddle_movement,
            apply_paddle_movement,
        )
        
        update_ai_logic(
            ai_player,
            ball,
            paddle,
            bricks,
            score,
            lives_left,
            game_start_time,
            frame_counter,
            training_mode,
            settings_manager,
            logger,
        )
        
        # Вычисляем скорость платформы с учетом количества блоков используя модуль game_loop_ai
        base_speed = calculate_paddle_speed_with_bricks(
            ball,
            bricks,
            ai_player,
        )
        
        # Обновляем движение платформы используя модуль game_loop_ai
        movement, adjusted_speed = update_ai_paddle_movement(
            ai_player,
            ball,
            paddle,
            frame_counter,
            logger,
        )
        
        # Применяем движение платформы используя модуль game_loop_ai
        apply_paddle_movement(paddle, movement, adjusted_speed)
        
        # Отладочная информация (выводим периодически)
        if pygame.time.get_ticks() % 1000 < 16:
            optimal_x = ai_player.get_optimal_paddle_position()
    else:
        # Ручное управление платформой
        if keys[pygame.K_LEFT]:
            paddle.move(-1)
        if keys[pygame.K_RIGHT]:
            paddle.move(1)

    if not game_started:
        return False, None, None, None, None, None, None, None, None, None, None, None
    
    # Обновляем физику мяча используя модуль game_loop_physics
    ball_was_at_top, should_continue = update_ball_physics(
        ball,
        paddle,
        frame_counter,
        game_started,
        training_mode,
        ai_player,
        logger,
    )
    if not should_continue:
        return False, None, None, None, None, None, None, None, None, None, None, None

    # Проверяем столкновения с платформой используя модуль game_loop_physics
    ball_hits_paddle_top, ball_hits_paddle_side, ball_stuck = check_paddle_collisions(
        ball,
        paddle,
        frame_counter,
        game_started,
        training_mode,
        ai_player,
        logger,
    )
    
    # Обрабатываем боковое столкновение используя модуль game_loop_physics
    if ball_hits_paddle_side:
        should_continue, lives_left, game_over, new_paddle, new_ball, new_bricks, new_score, new_ai_player, new_game_start_time = handle_paddle_side_collision(
            ball,
            paddle,
            lives_left,
            game_over,
            frame_counter,
            training_mode,
            ai_player,
            logger,
            bricks,
            score,
            game_start_time,
            settings_manager,
        )
        if new_paddle is not None:
            return False, new_paddle, new_ball, new_bricks, new_score, lives_left, game_over, None, new_game_start_time, new_ai_player, None, None
        if not should_continue:
            return False, None, None, None, None, lives_left, game_over, None, None, None, None, None
    
    # Обрабатываем прилипание мяча
    if ball_stuck:
        handle_ball_stuck(
            ball,
            paddle,
            frame_counter,
            game_started,
            training_mode,
            ai_player,
            logger,
        )
        return False, None, None, None, None, None, None, None, None, None, None, None
    
    # Обрабатываем отскок от верхней поверхности платформы
    if ball_hits_paddle_top:
        handle_paddle_top_bounce(
            ball,
            paddle,
            frame_counter,
            training_mode,
            ai_player,
            logger,
            bricks,
        )
    
    # Проверяем потерю мяча используя модуль game_loop_physics
    ball_lost, should_reset_ball = handle_ball_loss(
        ball,
        paddle,
        ball_hits_paddle_top,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        bricks,
    )
    
    if ball_lost:
        # Мяч потерян - уменьшаем жизни
        lives_left -= 1
        # КРИТИЧНО: Логируем после уменьшения жизней (только в файл, не в консоль)
        if training_mode:
            logger.info(f"[LIFE LOSS] Жизни уменьшены! lives_left={lives_left}, game_over={game_over}")
        if should_reset_ball and lives_left > 0:
            ball.reset(paddle.rect)
            ball.vel_y = 0
            return False, None, None, None, None, lives_left, False, None, None, None, None, None
        else:
            # Обрабатываем потерю всех жизней используя модуль game_loop_physics
            should_continue, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_all_lives_lost_after_ball_loss(
                ball,
                paddle,
                bricks,
                score,
                lives_left,
                game_start_time,
                frame_counter,
                training_mode,
                ai_player,
                logger,
                settings_manager,
            )
            if new_paddle is not None:
                return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None, None
            if not should_continue:
                return False, None, None, None, None, new_lives_left, new_game_over, None, None, None, None, None
            
            # В обычном режиме обрабатываем окончание игры используя модуль game_loop_physics
            if new_game_over and not training_mode:
                should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_over_manual(
                    screen,
                    font,
                    big_font,
                    score,
                    player_name,
                    game_start_time,
                    highscore_manager,
                    settings_manager,
                    ball,
                    paddle,
                    bricks,
                    new_game_over,
                    game_started,
                    show_game_results_func,
                    create_ai_player_func,
                    screen_width,
                    screen_height,
                )
                if should_exit:
                    return True, None, None, None, None, None, None, None, None, None, None, None
                if new_paddle is not None:
                    return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None, None
            return False, None, None, None, None, new_lives_left, new_game_over, None, None, None, None, None

    # Проверяем столкновения с кирпичами используя модуль game_loop_physics
    score_increase, destroyed_brick = check_brick_collisions(
        ball,
        bricks,
        frame_counter,
        training_mode,
        ai_player,
        logger,
    )
    score += score_increase
    
    # КРИТИЧНО: Проверяем победу (все кубики сбиты) и перезапускаем в режиме обучения
    if not bricks:
        game_over = True
        game_time_seconds = int(time.time() - game_start_time)
        
        # В режиме обучения не показываем экран результатов, сразу перезапускаем
        if training_mode:
            # Перезапускаем игру в режиме обучения используя модуль game_loop_physics
            new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time = handle_game_restart_training(
                ball,
                paddle,
                bricks,
                score,
                lives_left,
                game_start_time,
                training_mode,
                ai_player,
                settings_manager,
                logger,
                is_victory=True,
            )
            return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, ai_player, None, None

    # Обрабатываем потерю мяча за границей экрана используя модуль game_loop_physics
    should_continue, lives_left, game_over, new_paddle, new_ball, new_bricks, new_score, new_ai_player, new_game_start_time, game_started = handle_ball_out_of_bounds(
        ball,
        paddle,
        lives_left,
        game_over,
        bricks,
        score,
        game_start_time,
        frame_counter,
        training_mode,
        ai_player,
        logger,
        settings_manager,
    )
    if new_paddle is not None:
        return False, new_paddle, new_ball, new_bricks, new_score, lives_left, game_over, game_started, new_game_start_time, new_ai_player, None, None
    if not should_continue:
        return False, None, None, None, None, lives_left, game_over, game_started, None, None, None, None
    
    # В обычном режиме обрабатываем окончание игры используя модуль game_loop_physics
    if game_over and not training_mode:
        should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_game_over_manual(
            screen,
            font,
            big_font,
            score,
            player_name,
            game_start_time,
            highscore_manager,
            settings_manager,
            ball,
            paddle,
            bricks,
            game_over,
            game_started,
            show_game_results_func,
            create_ai_player_func,
            screen_width,
            screen_height,
        )
        if should_exit:
            return True, None, None, None, None, None, None, None, None, None, None, None
        if new_paddle is not None:
            return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None, None

    if not bricks:
        # В режиме обучения автоматически перезапускаем игру
        if training_mode:
            # Увеличиваем счетчик раундов
            training_rounds = 1  # Будет обновлен в main()
            
            # Перезапускаем игру в режиме обучения используя модуль game_loop_physics
            new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time = handle_game_restart_training(
                ball,
                paddle,
                bricks,
                score,
                lives_left,
                game_start_time,
                training_mode,
                ai_player,
                settings_manager,
                logger,
                is_victory=True,
            )
            return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, ai_player, None, training_rounds
        else:
            # Обычный режим - обрабатываем победу используя модуль game_loop_physics
            should_exit, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player = handle_victory_manual(
                screen,
                font,
                big_font,
                score,
                player_name,
                lives_left,
                game_start_time,
                highscore_manager,
                settings_manager,
                ball,
                paddle,
                bricks,
                game_over,
                game_started,
                show_victory_splash_func,
                show_game_results_func,
                create_ai_player_func,
                screen_width,
                screen_height,
            )
            if should_exit:
                return True, None, None, None, None, None, None, None, None, None, None, None
            if new_paddle is not None:
                return False, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player, None, None
    
    return False, None, None, None, score, lives_left, game_over, game_started, None, None, None, None
