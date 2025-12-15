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
    save_training_data_on_exit,
    finalize_game_setup,
)

# Импортируем функции обработки событий
from .game_loop_events import (
    process_keyboard_events,
    process_restart_key,
    apply_game_restart,
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
    handle_victory_manual,
    handle_all_lives_lost_after_ball_loss,
    apply_restart_result,
)

# Импортируем функции отрисовки
from .game_loop_rendering import (
    render_game_frame,
)

# Импортируем функции логики AI
from .game_loop_ai import (
    update_ai_logic,
    update_ai_paddle_movement,
    calculate_paddle_speed_with_bricks,
    initialize_ai_before_game_loop,
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
    
    # Отсчет времени игры
    game_start_time = time.time()
    
    # Завершаем настройку игры перед входом в основной цикл используя модуль game_loop_initialization
    game_started = True  # Игра начинается сразу
    finalize_game_setup(
        ball,
        paddle,
        training_mode,
        ai_player,
        settings_manager,
        logger,
        game_start_time,
    )

    # Счетчик кадров для обновления скорости в режиме обучения
    frame_counter = 0

    # Инициализируем AI перед входом в основной цикл используя модуль game_loop_ai
    if training_mode and ai_player is not None:
        initialize_ai_before_game_loop(
            ai_player,
            ball,
            paddle,
            bricks,
            score,
            game_start_time,
            logger,
        )
    
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

            # Обработка перезапуска после окончания игры используя модуль game_loop_events
            restart_result = process_restart_key(
                keys,
                game_over,
                settings_manager,
                logger
            )
            should_restart, new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_ai_player, new_game_start_time = apply_game_restart(restart_result)
            if should_restart:
                paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = apply_restart_result(
                    new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player,
                    paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player,
                )

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
                            paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = apply_restart_result(
                                new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player,
                                paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player,
                            )
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
                                paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = apply_restart_result(
                                    new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player,
                                    paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player,
                                )
                            if not should_continue:
                                continue  # Пропускаем остальную обработку кадра
                            
                            # В обычном режиме показываем экран результатов после потери всех жизней
                            if new_game_over and not training_mode:
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
                        paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = apply_restart_result(
                            new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player,
                            paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player,
                        )
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
                                show_victory_splash,
                                show_game_results,
                                create_ai_player,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT,
                            )
                            if should_exit:
                                pygame.quit()
                                return
                            if new_paddle is not None:
                                paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player = apply_restart_result(
                                    new_paddle, new_ball, new_bricks, new_score, new_lives_left, new_game_over, new_game_started, new_game_start_time, new_ai_player,
                                    paddle, ball, bricks, score, lives_left, game_over, game_started, game_start_time, ai_player,
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
            

    # Сохраняем данные обучения перед выходом используя модуль game_loop_initialization
    save_training_data_on_exit(
        training_mode,
        ai_player,
        training_rounds,
        logger,
    )
    
    # Закрываем игру
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
