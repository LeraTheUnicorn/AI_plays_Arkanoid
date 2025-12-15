"""
Модуль обработки событий игры для PyGameBall.py.

Содержит функции для обработки событий клавиатуры, мыши и системных событий.
"""

import time
import pygame
from typing import Tuple, Optional, Any

try:
    from .game_config import SCREEN_WIDTH, SCREEN_HEIGHT, MAX_LIVES
    from .game_models import Ball, Paddle
    from .game_utils import build_bricks, create_ai_player
    from .game_ui import trigger_instant_victory
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import SCREEN_WIDTH, SCREEN_HEIGHT, MAX_LIVES
    from game.game_models import Ball, Paddle
    from game.game_utils import build_bricks, create_ai_player
    from game.game_ui import trigger_instant_victory
    from ai.ai_player import AIPlayer


def process_keyboard_events(
    events: list,
    sound_enabled: bool,
    ball: Ball,
    settings_manager: Any,
    training_mode: bool,
    key_1_press_count: int,
    key_1_last_press_time: float,
    KEY_1_RESET_TIME: float,
    bricks: list,
    game_over: bool,
    lives_left: int,
    game_start_time: float,
    score: int,
    player_name: str,
    highscore_manager: Any,
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
) -> Tuple[bool, bool, int, float, list, bool, bool]:
    """
    Обрабатывает события клавиатуры в игровом цикле.
    
    Args:
        events: Список событий pygame.
        sound_enabled: Текущее состояние звука.
        ball: Объект мяча.
        settings_manager: Менеджер настроек.
        training_mode: Режим обучения.
        key_1_press_count: Счетчик нажатий клавиши "1".
        key_1_last_press_time: Время последнего нажатия "1".
        KEY_1_RESET_TIME: Время сброса счетчика.
        bricks: Список кирпичей.
        game_over: Флаг окончания игры.
        lives_left: Количество жизней.
        game_start_time: Время начала игры.
        score: Текущий счет.
        player_name: Имя игрока.
        highscore_manager: Менеджер рекордов.
        screen: Поверхность pygame.
        font: Шрифт.
        big_font: Большой шрифт.
        
    Returns:
        Tuple: (running, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over, exit_game)
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
            elif event.key == pygame.K_m:
                # Переключение всех звуков
                if sound_enabled:
                    pygame.mixer.music.stop()
                    sound_enabled = False
                else:
                    pygame.mixer.music.play(-1)
                    sound_enabled = True
            elif event.key == pygame.K_UP:
                # Увеличение скорости мяча
                ball.increase_speed(settings_manager)
            elif event.key == pygame.K_DOWN:
                # Уменьшение скорости мяча
                ball.decrease_speed(settings_manager)
            elif event.key == pygame.K_1 or event.key == ord('1'):
                # Обработка тройного нажатия "1" для немедленной победы
                current_time = time.time()
                # Если прошло больше времени сброса, сбрасываем счетчик
                if current_time - key_1_last_press_time > KEY_1_RESET_TIME:
                    key_1_press_count = 0
                
                key_1_press_count += 1
                key_1_last_press_time = current_time
                
                # Если нажали три раза подряд
                if key_1_press_count >= 3:
                    # Очищаем кирпичи для победы
                    bricks = []
                    key_1_press_count = 0  # Сбрасываем счетчик
                    if not getattr(__import__('sys'), 'frozen', False):
                        print(f"[CHEAT] Активирована немедленная победа (тройное нажатие '1')")
                        print(f"[CHEAT] training_mode={training_mode}, lives_left={lives_left}")
                    
                    # В режиме обучения не показываем заставку победы
                    if not training_mode and lives_left > 0:
                        if not getattr(__import__('sys'), 'frozen', False):
                            print("[CHEAT] Условия выполнены, вызываем trigger_instant_victory...")
                        game_over = True
                        game_time_seconds = int(time.time() - game_start_time)
                        
                        # Используем отдельный метод для показа заставки и результатов
                        try:
                            sound_enabled, restart_game, exit_game = trigger_instant_victory(
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
                            if not getattr(__import__('sys'), 'frozen', False):
                                print(f"[CHEAT] trigger_instant_victory завершена: restart_game={restart_game}, exit_game={exit_game}")
                        except Exception as e:
                            if not getattr(__import__('sys'), 'frozen', False):
                                print(f"[CHEAT] ОШИБКА в trigger_instant_victory: {e}")
                                import traceback
                                traceback.print_exc()
                            # Продолжаем выполнение даже при ошибке
                            restart_game = False
                            exit_game = False
                        
                        # Обработка выхода или перезапуска
                        if exit_game:
                            pygame.quit()
                            return False, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over, True
                        
                        if restart_game:
                            # Перезапускаем игру
                            # Возвращаем флаг перезапуска через специальное значение
                            # (это будет обработано в main())
                            pass  # Перезапуск обрабатывается в main()
    
    return running, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over, exit_game


def process_restart_key(
    keys: Any,
    game_over: bool,
    settings_manager: Any,
    logger: Any
) -> Tuple[Optional[Paddle], Optional[Ball], Optional[list], Optional[int], Optional[int], Optional[bool], Optional[bool], Optional[AIPlayer], Optional[float]]:
    """
    Обрабатывает нажатие клавиши R для перезапуска игры.
    
    Args:
        keys: Состояние клавиш pygame.
        game_over: Флаг окончания игры.
        settings_manager: Менеджер настроек.
        logger: Логгер.
        
    Returns:
        Tuple: (paddle, ball, bricks, score, lives_left, game_over, game_started, ai_player, game_start_time) или None для каждого элемента если перезапуск не требуется
    """
    if game_over and keys[pygame.K_r]:
        # В ручном режиме R перезапускает игру
        # Сброс состояния игры
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
        ai_player = create_ai_player(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
        ai_player.activate()
        game_start_time = time.time()
        
        return paddle, ball, bricks, score, lives_left, game_over, game_started, ai_player, game_start_time
    
    return None, None, None, None, None, None, None, None, None
