"""
Модуль инициализации игры для PyGameBall.py.

Содержит функции для инициализации pygame, создания объектов игры и настройки начального состояния.
"""

import os
import sys
import time
import pygame
from typing import Tuple, Optional, Any

try:
    from .game_config import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        MAX_LIVES,
        FPS,
    )
    from .game_models import Paddle, Ball
    from .game_utils import build_bricks, create_ai_player, resource_path
    from .highscores import HighScoreManager
    from .settings import SettingsManager
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        MAX_LIVES,
        FPS,
    )
    from game.game_models import Paddle, Ball
    from game.game_utils import build_bricks, create_ai_player, resource_path
    from game.highscores import HighScoreManager
    from game.settings import SettingsManager
    from ai.ai_player import AIPlayer


def initialize_pygame() -> Tuple[pygame.Surface, pygame.time.Clock, pygame.font.Font, pygame.font.Font]:
    """
    Инициализирует pygame и создает основные объекты.
    
    Returns:
        Tuple: (screen, clock, font, big_font)
    """
    startup_start_time = time.time()
    if not getattr(sys, "frozen", False):
        print(f"[STARTUP] Начало инициализации игры...")
    
    pygame.init()
    pygame.mixer.init()  # Инициализация аудио микшера
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Арканоид")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    big_font = pygame.font.SysFont("arial", 42, bold=True)
    
    if not getattr(sys, "frozen", False):
        pygame_init_time = time.time() - startup_start_time
        print(f"[STARTUP] pygame инициализирован за {pygame_init_time:.3f} сек")
    
    return screen, clock, font, big_font


def initialize_managers() -> Tuple[HighScoreManager, SettingsManager]:
    """
    Инициализирует менеджеры игры.
    
    Returns:
        Tuple: (highscore_manager, settings_manager)
    """
    highscore_manager = HighScoreManager()
    settings_manager = SettingsManager()
    return highscore_manager, settings_manager


def load_background_music() -> None:
    """
    Загружает фоновую музыку для игры.
    """
    try:
        music_path = resource_path("audio/FVCK_AI.mp3")
        # Нормализуем путь для корректной работы на Windows
        music_path = os.path.normpath(music_path)
        
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.3)
        else:
            # Файл не найден - выводим отладочную информацию только в режиме разработки
            if not getattr(sys, "frozen", False):
                print(f"[DEBUG] Файл музыки не найден по пути: {music_path}")
                # Пробуем альтернативный путь относительно текущей директории
                alt_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "resources",
                    "audio",
                    "FVCK_AI.mp3"
                )
                alt_path = os.path.normpath(alt_path)
                if os.path.exists(alt_path):
                    print(f"[DEBUG] Найден альтернативный путь: {alt_path}")
                    pygame.mixer.music.load(alt_path)
                    pygame.mixer.music.set_volume(0.3)
    except (pygame.error, FileNotFoundError, OSError) as e:
        # Музыка не загружена - выводим информацию только в режиме разработки
        if not getattr(sys, "frozen", False):
            print(f"[DEBUG] Не удалось загрузить фоновую музыку: {e}")


def initialize_game_objects(
    settings_manager: SettingsManager
) -> Tuple[Paddle, Ball, list, int]:
    """
    Создает начальные объекты игры.
    
    Args:
        settings_manager: Менеджер настроек игры.
        
    Returns:
        Tuple: (paddle, ball, bricks, score)
    """
    # ПОЛНЫЙ СБРОС СОСТОЯНИЯ ИГРЫ
    paddle = Paddle()
    ball = Ball()
    ball_speed = settings_manager.get_ball_speed()
    ball.set_speed(ball_speed)
    ball.reset(paddle.rect)
    ball.vel_y = 0
    bricks = build_bricks()
    score = 0
    
    return paddle, ball, bricks, score


def initialize_game_variables() -> dict:
    """
    Инициализирует переменные состояния игры.
    
    Returns:
        dict: Словарь с начальными значениями переменных игры.
    """
    return {
        "score": 0,
        "lives_left": MAX_LIVES,
        "game_over": False,
        "game_started": False,
        "running": True,
        "sound_enabled": True,
        "training_mode": True,  # Всегда режим обучения (режим 8)
        "training_rounds": 0,  # Счетчик раундов в режиме обучения
        "ai_player": None,  # Инициализация AI-игрока
        "player_name": "training",  # Имя для режима обучения
        "key_1_press_count": 0,
        "key_1_last_press_time": 0.0,
        "KEY_1_RESET_TIME": 2.0,  # Время в секундах для сброса счетчика
    }


def create_ai_player_system(logger: Any) -> Optional[AIPlayer]:
    """
    Создает AI-систему для режима обучения.
    
    Args:
        logger: Логгер для записи сообщений.
        
    Returns:
        Optional[AIPlayer]: Созданный AI-игрок или None в случае ошибки.
    """
    # Логируем создание AIPlayer (только в файл, не в консоль)
    logger.debug(f"[AI DEBUG] Создание AIPlayer... training_mode=True")
    try:
        # КРИТИЧНО: Создаем AIPlayer БЕЗ блокирующего сообщения на экране
        # Сообщение может остаться на экране, если создание занимает время
        ai_player = create_ai_player(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
        # Логируем создание AIPlayer (только в файл, не в консоль)
        logger.debug(f"[AI DEBUG] Новый AIPlayer создан. Обучение будет продолжено...")
        return ai_player
    except Exception as e:
        # Логируем ошибку (только в файл, не в консоль)
        logger.error(f"[ERROR] Ошибка при создании AIPlayer: {e}")
        import traceback
        traceback.print_exc()
        # Создаем базовый AI без логирования в случае ошибки
        try:
            ai_player = create_ai_player(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
            return ai_player
        except:
            # Если и это не работает, создаем минимальный AI
            if not getattr(sys, "frozen", False):
                print(f"[ERROR] Критическая ошибка: не удалось создать AIPlayer")
            raise


def setup_ai_player_for_training(
    ai_player: Optional[AIPlayer],
    ball: Ball,
    settings_manager: SettingsManager,
    logger: Any
) -> None:
    """
    Настраивает AI-игрока для режима обучения.
    
    Args:
        ai_player: AI-игрок для настройки.
        ball: Объект мяча для настройки скорости.
        settings_manager: Менеджер настроек игры.
        logger: Логгер для записи сообщений.
    """
    if ai_player is None:
        raise RuntimeError("ai_player должен быть создан в режиме обучения")
    
    # Активируем AI систему для режима обучения
    ai_player.activate()  # ВАЖНО: активируем AI систему
    
    # В режиме обучения используем оптимальную скорость из обучения
    try:
        optimal_speed = ai_player.get_optimal_ball_speed()
        if optimal_speed > 10:
            ball.current_speed = optimal_speed
            # Устанавливаем начальные скорости движения
            ball.vel_x = optimal_speed
            ball.vel_y = -optimal_speed
        else:
            ball.set_speed(optimal_speed, settings_manager)
        # Не выводим в exe файле
        if not getattr(sys, "frozen", False):
            print(
                f"Режим обучения: Игра запущена. AI активен: {ai_player.is_active}, "
                f"Скорость мяча: {optimal_speed}, Множитель платформы: {ai_player.get_optimal_paddle_speed_multiplier():.2f}"
            )
    except Exception as e:
        # Не выводим в exe файле
        if not getattr(sys, "frozen", False):
            print(f"[ERROR] Ошибка при настройке скорости в режиме обучения: {e}")
            import traceback
            traceback.print_exc()
        # Используем скорость по умолчанию
        ball.set_speed(8, settings_manager)


def start_background_music(sound_enabled: bool) -> None:
    """
    Запускает фоновую музыку, если звук включен.
    
    Args:
        sound_enabled: Флаг включения звука.
    """
    if sound_enabled:
        try:
            pygame.mixer.music.play(-1)  # Цикличное воспроизведение фоновой музыки
        except pygame.error:
            # Не выводим в exe файле
            if not getattr(sys, "frozen", False):
                print("Не удалось запустить фоновую музыку")


def save_training_data_on_exit(
    training_mode: bool,
    ai_player: Optional[Any],
    training_rounds: int,
    logger: Any,
) -> None:
    """
    Сохраняет данные обучения перед выходом из игры.
    
    Args:
        training_mode: Режим обучения
        ai_player: Объект AI игрока
        training_rounds: Количество раундов обучения
        logger: Логгер
    """
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
