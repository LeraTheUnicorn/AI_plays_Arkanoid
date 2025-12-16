# Игра Арканоид
# Версия импортируется из централизованного файла version.py


import os
import sys

# Исправление для запуска файла напрямую: добавляем корневую директорию проекта в sys.path
# Это должно быть ПЕРЕД всеми относительными импортами
if __name__ == "__main__":
    # Получаем путь к директории, содержащей этот файл
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    # Поднимаемся на один уровень вверх: game -> project_root
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Импортируем утилиты из модуля (с поддержкой как относительных, так и абсолютных импортов)
try:
    from .game_utils import suppress_pkg_resources_warnings
except ImportError:
    from game.game_utils import suppress_pkg_resources_warnings


# Примечание: функции из game_main_helpers больше не используются,
# так как они заменены на модули game_loop_*

# Импортируем функции инициализации игры
try:
    from .game_loop_initialization import (
        initialize_pygame,
        initialize_managers,
        load_background_music,
        initialize_game_objects,
        initialize_game_variables,
        create_ai_player_system,
        start_background_music,
        save_training_data_on_exit,
        finalize_game_setup,
    )
except ImportError:
    from game.game_loop_initialization import (
        initialize_pygame,
        initialize_managers,
        load_background_music,
        initialize_game_objects,
        initialize_game_variables,
        create_ai_player_system,
        start_background_music,
        save_training_data_on_exit,
        finalize_game_setup,
    )

# Импортируем функции обработки событий
try:
    from .game_loop_events import process_keyboard_events
except ImportError:
    from game.game_loop_events import process_keyboard_events

# Импортируем функции физики и столкновений
try:
    from .game_loop_physics import (
        position_ball_on_paddle,
        process_ball_physics_and_collisions,
        apply_restart_result,
    )
except ImportError:
    from game.game_loop_physics import (
        position_ball_on_paddle,
        process_ball_physics_and_collisions,
        apply_restart_result,
    )

# Импортируем функции отрисовки
try:
    from .game_loop_rendering import (
        render_game_frame,
    )
except ImportError:
    from game.game_loop_rendering import (
        render_game_frame,
    )

# Импортируем функции логики AI
try:
    from .game_loop_ai import (
        update_ai_logic,
        initialize_ai_before_game_loop,
        process_paddle_control,
    )
except ImportError:
    from game.game_loop_ai import (
        update_ai_logic,
        initialize_ai_before_game_loop,
        process_paddle_control,
    )

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Скрыть сообщение поддержки pygame

import time

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
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handlers_to_remove.append(handler)
    for handler in handlers_to_remove:
        logger.removeHandler(handler)
        handler.close()
except (ImportError, ModuleNotFoundError):
    # Если модуль недоступен, настраиваем базовое логирование
    import logging

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.propagate = False
    # Удаляем все консольные handlers (StreamHandler), если они есть
    handlers_to_remove = []
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handlers_to_remove.append(handler)
    for handler in handlers_to_remove:
        logger.removeHandler(handler)
        handler.close()

# Импортируем pygame с ограниченным подавлением предупреждений
with suppress_pkg_resources_warnings():
    import pygame  # type: ignore[reportMissingImports]

# Note: SettingsManager, Ball, Paddle, and AIPlayer are not directly imported
# as they are created by factory functions (initialize_managers, initialize_game_objects, etc.)


# Импортируем конфигурацию из централизованного файла
try:
    from .game_config import (
        MAX_LIVES,
        SCREEN_HEIGHT,  # pyright: ignore[reportUnusedImport]
        SCREEN_WIDTH,  # pyright: ignore[reportUnusedImport]
    )
except ImportError:
    from game.game_config import (
        MAX_LIVES,
        SCREEN_HEIGHT,  # pyright: ignore[reportUnusedImport]
        SCREEN_WIDTH,  # pyright: ignore[reportUnusedImport]
    )


# Note: Rendering functions (draw_bricks, draw_hud, etc.) are not directly imported
# as they are called through render_game_frame from game_loop_rendering


def main() -> None:
    # Настройка кодировки консоли для Windows (исправление отображения русских символов)
    # В exe файле не выполняем os.system, чтобы не открывать консоль
    if getattr(sys, "frozen", False):
        # В exe файле перенаправляем stdout и stderr в никуда, чтобы не открывать консоль
        import io

        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        except (AttributeError, ValueError):
            # Если не удалось, пробуем другой способ
            try:
                import os

                devnull = os.devnull
                sys.stdout = open(devnull, "w")
                sys.stderr = open(devnull, "w")
            except:
                pass
    elif sys.platform == "win32":
        try:
            # Пытаемся установить UTF-8 для консоли
            import io

            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="replace"
            )
        except (AttributeError, ValueError):
            # Если не удалось, пробуем через os (только в режиме разработки)
            try:
                import os

                os.system("chcp 65001 >nul 2>&1")  # Устанавливаем UTF-8 в консоли
            except:
                pass

    # Инициализация pygame и создание основных объектов
    screen, clock, font, big_font = initialize_pygame()

    # Инициализация менеджеров
    settings_manager = initialize_managers()

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
    logger.debug(
        f"[AI DEBUG] Вход в основной цикл игры, running={running}, game_started={game_started}"
    )

    # Очистка экрана выполняется в основном цикле для корректной отрисовки

    while running:
        frame_counter += 1
        # Отладочное сообщение только в первых 3 кадрах
        if frame_counter <= 3:
            logger.debug(
                f"[AI DEBUG] Кадр {frame_counter}, running={running}, game_started={game_started}"
            )

        # КРИТИЧНО: Обработка событий должна быть первой и всегда выполняться
        events = pygame.event.get()
        running, exit_game = process_keyboard_events(events)

        # Обработка выхода из игры
        if exit_game:
            pygame.quit()
            return

        # Отладочное сообщение только в первых 3 кадрах
        if frame_counter <= 3:
            logger.debug(
                f"[AI DEBUG] После обработки событий, game_started={game_started}, game_over={game_over}, training_mode={training_mode}"
            )

        # Позиционируем мяч на платформе используя модуль game_loop_physics
        position_ball_on_paddle(ball, paddle, game_started)

        if not game_over:
            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3:
                logger.debug(
                    f"[AI DEBUG] В блоке if not game_over, обновляем состояние игры"
                )

            # Обновляем логику AI используя модуль game_loop_ai
            if training_mode:
                assert (
                    ai_player is not None
                ), "ai_player должен быть создан в режиме обучения"
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

            # Обрабатываем управление платформой используя модуль game_loop_ai
            process_paddle_control(
                paddle,
                training_mode,
                ai_player,
                ball,
                frame_counter,
                logger,
            )

            # Обрабатываем физику мяча и столкновения используя модуль game_loop_physics
            if game_started:
                (
                    should_exit,
                    new_paddle,
                    new_ball,
                    new_bricks,
                    new_score,
                    new_lives_left,
                    new_game_over,
                    new_game_started,
                    new_game_start_time,
                    new_ai_player,
                    new_training_rounds,
                ) = process_ball_physics_and_collisions(
                    ball,
                    paddle,
                    bricks,
                    score,
                    lives_left,
                    game_over,
                    game_started,
                    game_start_time,
                    frame_counter,
                    training_mode,
                    ai_player,
                    logger,
                    settings_manager,
                    training_rounds,
                )
                if should_exit:
                    pygame.quit()
                    return
                if new_paddle is not None:
                    (
                        paddle,
                        ball,
                        bricks,
                        score,
                        lives_left,
                        game_over,
                        game_started,
                        game_start_time,
                        ai_player,
                    ) = apply_restart_result(
                        new_paddle,
                        new_ball,
                        new_bricks,
                        new_score,
                        new_lives_left,
                        new_game_over,
                        new_game_started,
                        new_game_start_time,
                        new_ai_player,
                        paddle,
                        ball,
                        bricks,
                        score,
                        lives_left,
                        game_over,
                        game_started,
                        game_start_time,
                        ai_player,
                    )
                    if new_training_rounds is not None:
                        training_rounds = new_training_rounds
                    continue  # Пропускаем остальную обработку кадра
                if new_score is not None:
                    score = new_score
                if new_lives_left is not None:
                    lives_left = new_lives_left
                if new_game_over is not None:
                    game_over = new_game_over
                if new_game_started is not None:
                    game_started = new_game_started

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
