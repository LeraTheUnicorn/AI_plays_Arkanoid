# Игра Арканоид
# Версия импортируется из централизованного файла version.py


import os
import warnings
from contextlib import contextmanager
from typing import Generator

# Импортируем утилиты из модуля
from .game_utils import (
    suppress_pkg_resources_warnings,
    resource_path,
    is_valid_player_name_char,
    build_bricks,
    create_ai_player,
)

# Импортируем UI функции из модуля
from .game_ui import (
    show_highscores,
    trigger_instant_victory,
    show_victory_splash,
    show_game_results,
    show_settings_window,
)

# Примечание: функции из game_main_helpers больше не используются,
# так как они заменены на модули game_loop_*

# Импортируем функции инициализации игры
from .game_loop_initialization import (
    initialize_pygame,
    initialize_managers,
    load_background_music,
    initialize_game_objects,
    initialize_game_variables,
    create_ai_player_system,
    setup_ai_player_for_training,
    start_background_music,
)

# Импортируем функции обработки событий
from .game_loop_events import (
    process_keyboard_events,
    process_restart_key,
)

# Импортируем функции физики и столкновений
from .game_loop_physics import (
    update_ball_physics,
    check_paddle_collisions,
    handle_paddle_top_bounce,
    handle_ball_stuck,
    check_brick_collisions,
    handle_ball_loss,
    handle_game_restart_training,
    handle_paddle_side_collision,
    handle_ball_out_of_bounds,
    handle_game_restart_manual,
)

# Импортируем функции отрисовки
from .game_loop_rendering import (
    render_game_frame,
)

# Импортируем функции логики AI
from .game_loop_ai import (
    update_ai_logic,
    update_ai_paddle_movement,
)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Скрыть сообщение поддержки pygame

import random
import time
import numpy as np
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any

# Исправление для запуска файла напрямую: добавляем корневую директорию проекта в sys.path
if __name__ == "__main__":
    # Получаем путь к директории, содержащей этот файл
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    # Поднимаемся на два уровня вверх: src/game -> src -> project_root
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# КРИТИЧНО: Настраиваем логирование ПЕРЕД импортом всех модулей
# Это гарантирует, что ВСЕ модули используют централизованную конфигурацию
try:
    import logging
    from ai.logging_config import setup_root_logger, get_logger
    setup_root_logger()
    # Создаем logger для PyGameBall
    logger = get_logger(__name__)
    # КРИТИЧНО: Отключаем распространение в root logger, чтобы сообщения не попадали в консоль
    # Все логи должны идти только в файлы через handlers, созданные в ai_player.py
    logger.propagate = False
    # Удаляем все консольные handlers (StreamHandler), если они есть
    handlers_to_remove = []
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handlers_to_remove.append(handler)
    for handler in handlers_to_remove:
        logger.removeHandler(handler)
        handler.close()
except (ImportError, ModuleNotFoundError):
    # Если модуль недоступен, настраиваем базовое логирование
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.propagate = False
    # Удаляем все консольные handlers (StreamHandler), если они есть
    handlers_to_remove = []
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handlers_to_remove.append(handler)
    for handler in handlers_to_remove:
        logger.removeHandler(handler)
        handler.close()

# Импортируем pygame с ограниченным подавлением предупреждений
with suppress_pkg_resources_warnings():
    import pygame

# Импорты с поддержкой как относительных, так и абсолютных путей
try:
    # Пытаемся использовать относительные импорты (когда запускается как модуль)
    from highscores import HighScoreManager
    from settings import SettingsManager
    from game_models import Ball, Paddle
except ImportError:
    # Если относительные импорты не работают (когда запускается напрямую), используем абсолютные
    from game.highscores import HighScoreManager  # type: ignore[assignment]
    from game.settings import SettingsManager  # type: ignore[assignment]
    from game.game_models import Ball, Paddle  # type: ignore[assignment]

from ai.ai_player import AIPlayer


# Импортируем конфигурацию из централизованного файла
try:
    from .game_config import (
        BALL_SIZE,
        BALL_SPEED_DEFAULT,
        BRICK_COLS,
        BRICK_HEIGHT,
        BRICK_OFFSET_TOP,
        BRICK_PADDING,
        BRICK_ROWS,
        BRICK_WIDTH,
        FPS,
        MAX_LIVES,
        PADDLE_HEIGHT,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
except ImportError:
    from game.game_config import (
        BALL_SIZE,
        BALL_SPEED_DEFAULT,
        BRICK_COLS,
        BRICK_HEIGHT,
        BRICK_OFFSET_TOP,
        BRICK_PADDING,
        BRICK_ROWS,
        BRICK_WIDTH,
        FPS,
        MAX_LIVES,
        PADDLE_HEIGHT,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )


# is_valid_player_name_char импортируется из game_utils




# show_game_results импортируется из game_ui.py

# КРИТИЧНО: Классы Paddle и Ball импортируются из game_models.py
# для устранения дубликатов кода (см. docs/DUPLICATE_ANALYSIS.md)

# build_bricks импортируется из game_utils

# Импортируем функции отрисовки из модуля
from .game_rendering import (
    draw_bricks,
    draw_hud,
    render_colored_hint,
    draw_start_hint,
)


# show_settings_window теперь в game_ui.py

def main() -> None:
    # Инициализация pygame и создание основных объектов
    screen, clock, font, big_font = initialize_pygame()
    
    # Инициализация менеджеров
    highscore_manager, settings_manager = initialize_managers()
    
    # Загрузка фоновой музыки
    load_background_music()
    
    # Инициализация переменных состояния игры
    game_vars = initialize_game_variables()
    score = game_vars["score"]
    lives_left = game_vars["lives_left"]
    game_over = game_vars["game_over"]
    game_started = game_vars["game_started"]
    running = game_vars["running"]
    sound_enabled = game_vars["sound_enabled"]
    training_mode = game_vars["training_mode"]
    training_rounds = game_vars["training_rounds"]
    ai_player = game_vars["ai_player"]
    player_name = game_vars["player_name"]
    key_1_press_count = game_vars["key_1_press_count"]
    key_1_last_press_time = game_vars["key_1_last_press_time"]
    KEY_1_RESET_TIME = game_vars["KEY_1_RESET_TIME"]
    
    # Создание объектов игры
    paddle, ball, bricks, score = initialize_game_objects(settings_manager)
    game_over = False
    game_started = False
    
    # Создаем AI-систему для режима обучения
    if training_mode:
        ai_player = create_ai_player_system(logger)
    
    # Устанавливаем жизни для режима обучения
    lives_left = MAX_LIVES  # Всегда 3 жизни в режиме обучения
    
    # Запускаем музыку (если звук включен)
    start_background_music(sound_enabled)
    
    # Настраиваем AI-систему для режима обучения
    if training_mode and ai_player is not None:
        setup_ai_player_for_training(ai_player, ball, settings_manager, logger)
    
    game_started = True  # Игра начинается сразу
    ball.vel_x = ball.get_speed()  # Направление вправо
    ball.vel_y = -ball.get_speed()
    # Логируем настройку игры (только в файл, не в консоль)
    logger.debug(f"[AI DEBUG] Игра настроена, game_started={game_started}, ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}")

    # Отсчет времени игры
    game_start_time = time.time()

    # Счетчик кадров для обновления скорости в режиме обучения
    frame_counter = 0

    # КРИТИЧНО: Обновляем состояние игры для AI перед входом в основной цикл
    assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
    ai_player.update_game_state(
        ball, paddle, bricks, score, int(game_start_time)
    )
    # Логируем обновление состояния (только в файл, не в консоль)
    logger.debug(f"[AI DEBUG] Состояние игры обновлено для AI перед входом в цикл")
    
    # КРИТИЧНО: Логируем вход в основной цикл (только в файл, не в консоль)
    logger.debug(f"[AI DEBUG] Вход в основной цикл игры, running={running}, game_started={game_started}")
    
    # Очистка экрана выполняется в основном цикле для корректной отрисовки

    while running:
            frame_counter += 1
            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3:
                logger.debug(f"[AI DEBUG] Кадр {frame_counter}, running={running}, game_started={game_started}")
            
            # КРИТИЧНО: Обработка событий должна быть первой и всегда выполняться
            events = pygame.event.get()
            running, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over, exit_game = process_keyboard_events(
                events,
                sound_enabled,
                ball,
                settings_manager,
                training_mode,
                key_1_press_count,
                key_1_last_press_time,
                KEY_1_RESET_TIME,
                bricks,
                game_over,
                lives_left,
                game_start_time,
                score,
                player_name,
                highscore_manager,
                screen,
                font,
                big_font,
            )
            
            # Обработка выхода из игры
            if exit_game:
                pygame.quit()
                return

            keys = pygame.key.get_pressed()
            
            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3:
                logger.debug(f"[AI DEBUG] После обработки событий, game_started={game_started}, game_over={game_over}, training_mode={training_mode}")

            # В режиме обучения игра уже запущена, мяч всегда на платформе до старта
            if not game_started:
                ball.rect.center = paddle.rect.midtop
                ball.rect.y -= BALL_SIZE

            # Обработка перезапуска после окончания игры (только для ручного режима)
            should_restart, restart_paddle, restart_ball, restart_bricks, restart_score, restart_lives, restart_game_over, restart_game_started, restart_ai_player, restart_game_start_time = process_restart_key(
                keys,
                game_over,
                settings_manager,
                logger
            )
            if should_restart:
                paddle = restart_paddle
                ball = restart_ball
                bricks = restart_bricks
                score = restart_score
                lives_left = restart_lives
                game_over = restart_game_over
                game_started = restart_game_started
                ai_player = restart_ai_player
                game_start_time = restart_game_start_time

            if not game_over:
                # Отладочное сообщение только в первых 3 кадрах
                if frame_counter <= 3:
                    logger.debug(f"[AI DEBUG] В блоке if not game_over, обновляем состояние игры")
                
                # Обновляем логику AI используя модуль game_loop_ai
                if training_mode:
                    assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
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
                    
                    # Обновляем движение платформы используя модуль game_loop_ai
                    movement, adjusted_speed = update_ai_paddle_movement(
                        ai_player,
                        ball,
                        paddle,
                        frame_counter,
                        logger,
                    )
                    
                    if movement != 0:
                        # Применяем движение с адаптивной скоростью
                        new_center_x = paddle.rect.centerx + movement * adjusted_speed
                        paddle_half_width = PADDLE_WIDTH // 2
                        min_center_x = paddle_half_width
                        max_center_x = SCREEN_WIDTH - paddle_half_width
                        paddle.rect.centerx = max(
                            min_center_x, min(max_center_x, new_center_x)
                        )
                    
                    # Отладочная информация (выводим периодически)
                    if pygame.time.get_ticks() % 1000 < 16:
                        optimal_x = ai_player.get_optimal_paddle_position()
                else:
                    # Ручное управление платформой
                    if keys[pygame.K_LEFT]:
                        paddle.move(-1)
                    if keys[pygame.K_RIGHT]:
                        paddle.move(1)

                if game_started:
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
                        continue

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
                            paddle = new_paddle
                            ball = new_ball
                            bricks = new_bricks
                            score = new_score
                            ai_player = new_ai_player
                            game_start_time = new_game_start_time
                        if not should_continue:
                            continue  # Пропускаем остальную обработку кадра
                    
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
                        continue  # Пропускаем обработку отскока, так как мяч уже перемещен
                    
                    # Обрабатываем отскок от верхней поверхности платформы
                    if ball_hits_paddle_top:
                        # Обрабатываем отскок от верхней поверхности платформы используя модуль game_loop_physics
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
                        else:
                            # КРИТИЧНО: Логируем окончание жизней
                            if training_mode:
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME END] Все жизни потрачены (ball.rect.bottom > paddle.rect.top)! lives_left={lives_left}, training_mode={training_mode}")
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Обучаем AI на результате игры (проигрыш)
                            if training_mode:
                                # В режиме обучения считаем кубики за весь матч (пока не потратятся все жизни)
                                total_bricks_destroyed = (
                                    BRICK_ROWS * BRICK_COLS
                                ) - len(bricks)

                                # Обновляем финальную статистику обучения
                                if training_mode:
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
                            if training_mode:
                                # КРИТИЧНО: Логируем начало перезапуска
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME RESTART] Начинаем перезапуск игры в режиме обучения после потери всех жизней...")
                                
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
                                ai_player._reset_game_state_trackers()
                                
                                # Автоматически перезапускаем игру в режиме обучения
                                paddle = Paddle()
                                ball = Ball()
                                optimal_ball_speed = ai_player.get_optimal_ball_speed()
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                    )
                                ball.reset(paddle.rect)
                                ball.vel_y = 0
                                bricks = build_bricks()
                                score = 0
                                lives_left = (
                                    MAX_LIVES  # Восстанавливаем жизни для нового матча
                                )
                                game_over = False
                                game_started = True  # Автоматически запускаем
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()
                                game_start_time = time.time()
                                
                                # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
                                # Это гарантирует, что current_game_state будет установлен до первого вызова move_paddle_towards
                                ai_player.update_game_state(
                                    ball, paddle, bricks, score, int(game_start_time)
                                )
                                
                                # КРИТИЧНО: Логируем перезапуск игры для диагностики
                                if training_mode:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART] Игра перезапущена после потери всех жизней!")
                                        print(f"[GAME RESTART] lives_left={lives_left}, game_over={game_over}, game_started={game_started}")
                                        print(f"[GAME RESTART] ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}, paddle.x={paddle.rect.x}, bricks={len(bricks)}")
                                    ai_player.performance_logger.log_ball_paddle_positions(
                                        ball.rect.centerx,
                                        ball.rect.centery,
                                        ball.vel_x,
                                        ball.vel_y,
                                        paddle.rect.x,
                                        paddle.rect.y,
                                        paddle.rect.width,
                                        paddle.rect.height,
                                        "GAME_RESTART_AFTER_LOSS"
                                    )
                                    # Логируем начало новой игры
                                    if ai_player.current_game_state:
                                        ai_player.performance_logger.log_game_start(ai_player.current_game_state)
                            else:
                                # В ручном режиме показываем экран результатов
                                sound_enabled, restart_game, exit_game = (
                                    show_game_results(
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
                                )

                                # Если игрок хочет выйти из игры
                                if exit_game:
                                    # Сохраняем данные обучения перед выходом
                                    pygame.quit()
                                    return

                                # Обработка перезапуска
                                if restart_game:
                                    # Перезапускаем игру используя модуль game_loop_physics
                                    paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = handle_game_restart_manual(
                                        paddle,
                                        ball,
                                        bricks,
                                        score,
                                        lives_left,
                                        game_over,
                                        game_started,
                                        settings_manager,
                                        SCREEN_WIDTH,
                                        SCREEN_HEIGHT,
                                        create_ai_player,
                                    )
                        continue  # Пропускаем остальную обработку кадра

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
                            paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time = handle_game_restart_training(
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
                            continue  # Пропускаем остальную обработку кадра

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
                        paddle = new_paddle
                        ball = new_ball
                        bricks = new_bricks
                        score = new_score
                        ai_player = new_ai_player
                        game_start_time = new_game_start_time
                    if not should_continue:
                        continue  # Пропускаем остальную обработку кадра
                    
                    # В обычном режиме показываем экран результатов после потери всех жизней
                    if game_over and not training_mode:
                        game_time_seconds = int(time.time() - game_start_time)
                        sound_enabled, restart_game, exit_game = (
                            show_game_results(
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
                        )

                        # Если игрок хочет выйти из игры
                        if exit_game:
                            pygame.quit()
                            return

                        # Обработка перезапуска
                        if restart_game:
                            # Перезапускаем игру используя модуль game_loop_physics
                            paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = handle_game_restart_manual(
                                paddle,
                                ball,
                                bricks,
                                score,
                                lives_left,
                                game_over,
                                game_started,
                                settings_manager,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT,
                                create_ai_player,
                            )

                    if not bricks:
                        # В режиме обучения автоматически перезапускаем игру
                        if training_mode:
                            # Увеличиваем счетчик раундов
                            training_rounds += 1
                            
                            # Перезапускаем игру в режиме обучения используя модуль game_loop_physics
                            paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time = handle_game_restart_training(
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
                        else:
                            # Обычный режим - показываем экран результатов
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Показываем заставку победы только в обычном режиме (с вводом имени)
                            # и если у игрока остались жизни (победа)
                            if not training_mode and lives_left > 0:
                                show_victory_splash(screen, duration_seconds=5.0)

                            # В любом режиме показываем экран результатов
                            sound_enabled, restart_game, exit_game = show_game_results(
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
                                # Сохраняем данные обучения перед выходом
                                pygame.quit()
                                return

                            # Обработка перезапуска
                            if restart_game:
                                # Перезапускаем игру используя модуль game_loop_physics
                                paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = handle_game_restart_manual(
                                    paddle,
                                    ball,
                                    bricks,
                                    score,
                                    lives_left,
                                    game_over,
                                    game_started,
                                    settings_manager,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT,
                                    create_ai_player,
                                )

            # Отрисовка игры используя модуль game_loop_rendering
            render_game_frame(
                screen,
                ball,
                paddle,
                bricks,
                score,
                lives_left,
                font,
                big_font,
                clock,
                frame_counter,
                game_started,
                training_mode,
                training_rounds,
                ai_player,
                logger,
            )

            # В режиме обучения игра продолжается до завершения
            

    # В режиме обучения выводим статистику перед выходом
    if training_mode:
        # Сохраняем данные обучения
        try:
            if ai_player and ai_player.performance_metrics.get("games_played", 0) > 0:
                ai_player.save_learning_data()
                if not getattr(sys, "frozen", False):
                    print(
                        f"[AI] Режим обучения завершен. Сыграно матчей: {training_rounds}"
                    )
                    print("[AI] Данные обучения сохранены.")
            else:
                # КРИТИЧНО: Не сохраняем данные, если не было сыграно ни одной игры (только в файл, не в консоль)
                logger.debug(f"[AI DEBUG] Данные обучения не сохранены - не было сыграно игр (games_played={ai_player.performance_metrics.get('games_played', 0) if ai_player else 0})")
        except Exception as e:
            if not getattr(sys, "frozen", False):
                print(f"[AI] Предупреждение: не удалось сохранить данные обучения: {e}")
    
    # Закрываем игру
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
