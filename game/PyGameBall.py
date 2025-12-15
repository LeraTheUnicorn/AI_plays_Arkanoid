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

# Импортируем вспомогательные функции для main()
from .game_main_helpers import (
    handle_game_events,
    update_game_state,
    update_ball_physics,
    render_game_frame,
)

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




# show_highscores, trigger_instant_victory, show_victory_splash, show_settings_window теперь в game_ui.py

def show_game_results(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
    highscore_manager: HighScoreManager,
    settings_manager: SettingsManager,
    ball: "Ball",
) -> tuple[bool, bool, bool]:
    """
    Отображает экран с результатами игры и таблицей рекордов.
    
    Показывает финальный счет, время игры, таблицу рекордов и позволяет
    игроку перезапустить игру или выйти.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        score: Финальный счет игрока
        player_name: Имя игрока
        game_time_seconds: Время игры в секундах
        highscore_manager: Менеджер рекордов для сохранения и отображения
        settings_manager: Менеджер настроек игры
        ball: Объект мяча для доступа к настройкам
        
    Returns:
        Кортеж из 3 элементов:
        - Состояние звука (bool)
        - Флаг перезапуска игры (bool)
        - Флаг выхода из игры (bool)
    """
    game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"

    # Добавляем результат в рекорды и проверяем, попал ли он в топ-10
    score_saved = highscore_manager.add_score(player_name, score, game_time_seconds)

    # Состояние звука
    sound_enabled = True
    restart_game = False
    exit_game = False

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game = True
                return sound_enabled, False, exit_game  # Выход из игры по крестику
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # ESC выходит из игры
                    exit_game = True
                    return sound_enabled, False, exit_game
                elif event.key == pygame.K_RETURN:
                    waiting = False
                    restart_game = True
                elif event.key == pygame.K_h:
                    # Показываем таблицу рекордов (ESC выходит из игры)
                    sound_enabled, exit_game = show_highscores(
                        screen, font, highscore_manager, exit_on_esc=True
                    )
                    if exit_game:
                        exit_game = True
                        return sound_enabled, False, exit_game  # Выход из игры
                elif event.key == pygame.K_m:
                    # Переключение всех звуков
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True
                elif event.key == pygame.K_UP:
                    # Открытие окна настроек
                    sound_enabled = show_settings_window(
                        screen,
                        font,
                        big_font,
                        settings_manager,
                        ball,
                        sound_enabled,
                    )

        # Отрисовка экрана результатов
        screen.fill((10, 10, 30))

        # Заголовок
        if score > 0:
            title = big_font.render("Игра окончена!", True, (255, 255, 255))
        else:
            title = big_font.render("Игра окончена", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        # Результаты игрока
        result_text = f"Игрок: {player_name}"
        score_text = f"Очки: {score}"
        time_text = f"Время игры: {game_time_formatted}"

        surf1 = font.render(result_text, True, (255, 255, 255))
        surf2 = font.render(score_text, True, (255, 255, 255))
        surf3 = font.render(time_text, True, (255, 255, 255))

        screen.blit(surf1, (SCREEN_WIDTH // 2 - 100, 200))
        screen.blit(surf2, (SCREEN_WIDTH // 2 - 100, 250))
        screen.blit(surf3, (SCREEN_WIDTH // 2 - 100, 300))

        # Сообщение о топ-10
        if not score_saved:
            warning_text = "Результат не попал в топ-10, таблица рекордов не обновлена"
            warning_surface = font.render(warning_text, True, (255, 200, 100))
            warning_rect = warning_surface.get_rect(center=(SCREEN_WIDTH // 2, 360))
            screen.blit(warning_surface, warning_rect)

        # Подсказки
        render_colored_hint(
            screen,
            font,
            "Enter - новая игра, H - рекорды",
            (SCREEN_WIDTH // 2 - 150, 400),
        )
        render_colored_hint(
            screen, font, "ESC - выход из игры", (SCREEN_WIDTH // 2 - 150, 430)
        )

        pygame.display.flip()

    return sound_enabled, restart_game, exit_game


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


# draw_hud, render_colored_hint, draw_start_hint импортируются из game_rendering


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
                
                # Обновляем состояние игры для AI системы
                if training_mode:
                    assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
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
                        if not getattr(sys, "frozen", False):
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
                        assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
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

                # Движение платформы
                if training_mode:
                    assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
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
                    try:
                        bricks_remaining = len(bricks) if bricks is not None else 50
                    except (NameError, TypeError):
                        bricks_remaining = 50
                    if bricks_remaining <= 5:
                        # Увеличиваем скорость в критических ситуациях, но не превышаем максимум
                        base_speed = min(int(base_speed * 1.2), 60)  # Увеличиваем на 20%, максимум 60
                    if bricks_remaining == 1:
                        # При 1 кубике используем максимальную скорость для гарантированного попадания
                        base_speed = 60  # Максимальная скорость

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
                        
                        # КРИТИЧНО: Используем centerx для движения, чтобы избежать конфликта с x
                        # Применяем движение с адаптивной скоростью
                        new_center_x = paddle.rect.centerx + movement * adjusted_speed
                        
                        # Строгие границы для центра платформы: половина ширины платформы = 60 пикселей
                        paddle_half_width = PADDLE_WIDTH // 2  # 60 пикселей
                        min_center_x = paddle_half_width
                        max_center_x = SCREEN_WIDTH - paddle_half_width
                        paddle.rect.centerx = max(
                            min_center_x, min(max_center_x, new_center_x)
                        )
                    # Если мяч не в зоне разделения - платформа остается на месте (movement = 0)

                    # Отладочная информация (выводим периодически)
                    if pygame.time.get_ticks() % 1000 < 16:  # Каждые ~1 секунду
                        optimal_x = ai_player.get_optimal_paddle_position()
                        # print(
                        #     f"AI Debug: Платформа X={paddle.rect.centerx}, Оптимальная X={optimal_x}, Движение={movement}, AI активен={ai_player.is_active}"
                        # )
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
                    
                    # Обрабатываем боковое столкновение - это потеря мяча
                    if ball_hits_paddle_side:
                        if frame_counter <= 3:
                            logger.debug(f"[AI DEBUG] ball_hits_paddle_side=True, обрабатываем боковое столкновение")
                        if frame_counter <= 3:
                            logger.debug(f"[AI DEBUG] Боковое столкновение! Обрабатываем...")
                        # Мяч попал на боковую сторону платформы - это потеря мяча
                        lives_left -= 1
                        if lives_left > 0:
                            # КРИТИЧНО: Правильно сбрасываем мяч после бокового удара
                            # Сначала сбрасываем позицию и скорость
                            ball.reset(paddle.rect)
                            # КРИТИЧНО: Принудительно устанавливаем мяч ВЫШЕ платформы, чтобы избежать прилипания
                            ball_radius = BALL_SIZE // 2
                            ball.rect.centery = paddle.rect.top - ball_radius - 5  # Мяч должен быть минимум на 5 пикселей выше платформы
                            # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
                            if ball.rect.colliderect(paddle.rect):
                                # Если мяч все еще внутри платформы, перемещаем его еще выше
                                ball.rect.centery = paddle.rect.top - ball_radius - 15
                            # КРИТИЧНО: После бокового удара мяч потерян, но не устанавливаем vel_y = 0
                            # Вместо этого мяч будет обработан в логике потери жизни ниже
                            # КРИТИЧНО: Сбрасываем все трекеры после бокового удара
                            if training_mode:
                                assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
                                ai_player._reset_game_state_trackers()
                        else:
                            game_over = True
                            # КРИТИЧНО: В режиме обучения перезапускаем игру после потери всех жизней
                            if training_mode and lives_left <= 0:
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
                                    is_victory=False,
                                )
                                
                                if frame_counter <= 3:
                                    logger.debug(f"[AI DEBUG] Игра перезапущена после бокового удара, lives_left={lives_left}")
                                
                                continue  # Пропускаем остальную обработку кадра
                        
                        # Логируем потерю мяча из-за бокового удара
                        if training_mode:
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
                        if frame_counter <= 3:
                            logger.debug(f"[AI DEBUG] Боковое столкновение обработано, continue")
                        continue  # Пропускаем проверку верхней поверхности после бокового удара
                    
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
                                    # Перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                        paddle = Paddle()
                                        ball = Ball()
                                        ball_speed = settings_manager.get_ball_speed()
                                        ball.set_speed(ball_speed)
                                        ball.reset(paddle.rect)
                                        ball.vel_y = 0
                                        bricks = build_bricks()
                                        score = 0
                                        lives_left = MAX_LIVES
                                        game_over = False
                                        game_started = False
                                        # Пересоздаем AI для новой игры
                                        ai_player = create_ai_player(
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT,
                                            debug_mode=True
                                        )
                                        ai_player.activate()
                                        # Перезапускаем отсчет времени игры
                                        game_start_time = time.time()
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

                    if ball.rect.bottom >= SCREEN_HEIGHT:
                        # КРИТИЧНО: Логируем потерю мяча (мяч за границей экрана)
                        if training_mode:
                            logger.info(f"[LIFE LOSS] Мяч за границей экрана (ball.rect.bottom={ball.rect.bottom} >= SCREEN_HEIGHT={SCREEN_HEIGHT})! lives_left={lives_left}")
                        # Уменьшаем жизни (в режиме обучения тоже)
                        lives_left -= 1
                        # КРИТИЧНО: Логируем потерю жизни для диагностики (только в файл, не в консоль)
                        if training_mode:
                            logger.info(f"[LIFE LOSS] Жизни уменьшены! lives_left={lives_left}, training_mode={training_mode}, game_over={game_over}")
                        
                        # КРИТИЧНО: Проверяем, не закончились ли жизни
                        if lives_left <= 0:
                            # КРИТИЧНО: Логируем окончание жизней
                            if training_mode:
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME END] Все жизни потрачены! lives_left={lives_left}, training_mode={training_mode}, game_over={game_over}")
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
                                    is_victory=False,
                                )
                            else:
                                # В обычном режиме показываем экран результатов
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
                                    # Перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                        paddle = Paddle()
                                        ball = Ball()
                                        ball_speed = settings_manager.get_ball_speed()
                                        ball.set_speed(ball_speed)
                                        ball.reset(paddle.rect)
                                        ball.vel_y = 0
                                        bricks = build_bricks()
                                        score = 0
                                        lives_left = MAX_LIVES
                                        game_over = False
                                        game_started = False
                                        # Пересоздаем AI для новой игры
                                        ai_player = create_ai_player(
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT,
                                            debug_mode=True
                                        )
                                        ai_player.activate()
                                        # Перезапускаем отсчет времени игры
                                        game_start_time = time.time()
                        else:
                            ball.reset(paddle.rect)
                            ball.vel_y = 0
                            game_started = False

                            # В режиме обучения автоматически запускаем игру заново (если есть жизни)
                            if training_mode and lives_left > 0:
                                game_started = True
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()

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
                                # Перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                    paddle = Paddle()
                                    ball = Ball()
                                    ball_speed = settings_manager.get_ball_speed()
                                    ball.set_speed(ball_speed)
                                    ball.reset(paddle.rect)
                                    ball.vel_y = 0
                                    bricks = build_bricks()
                                    score = 0
                                    lives_left = MAX_LIVES
                                    game_over = False
                                    game_started = False
                                    # Пересоздаем AI для новой игры
                                    ai_player = create_ai_player(
                                        SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True
                                    )
                                    ai_player.activate()
                                    # Перезапускаем отсчет времени игры
                                    game_start_time = time.time()

            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3:
                logger.debug(f"[AI DEBUG] Конец блока if not game_over, переходим к отрисовке")
                logger.debug(f"[AI DEBUG] Начинаем отрисовку, game_over={game_over}, bricks={len(bricks) if 'bricks' in locals() else 'N/A'}")
            
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
            if training_mode:
                assert ai_player is not None, "ai_player должен быть создан в режиме обучения"
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
