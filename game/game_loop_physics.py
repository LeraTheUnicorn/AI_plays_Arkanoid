"""
Модуль физики и столкновений для PyGameBall.py.

Содержит функции для обновления физики мяча, обработки столкновений и логики игры.
"""

import random
import sys
import time
from typing import Tuple, Optional, Any

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
