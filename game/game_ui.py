"""
UI функции для игры Арканоид.
Содержит функции для отображения окон, заставок и результатов игры.
"""

import os
import sys
import time
from typing import Tuple, Optional, Any
import pygame

try:
    from .game_config import SCREEN_WIDTH, SCREEN_HEIGHT
    from .game_rendering import render_colored_hint
    from .game_utils import resource_path
    from .highscores import HighScoreManager
    from .settings import SettingsManager
    from .game_models import Ball
except ImportError:
    from game.game_config import SCREEN_WIDTH, SCREEN_HEIGHT
    from game.game_rendering import render_colored_hint
    from game.game_utils import resource_path
    from game.highscores import HighScoreManager
    from game.settings import SettingsManager
    from game.game_models import Ball


def show_highscores(
    screen: pygame.Surface,
    font: pygame.font.Font,
    highscore_manager: HighScoreManager,
    exit_on_esc: bool = False,
) -> Tuple[bool, bool]:
    """
    Отображает таблицу рекордов.
    Возвращает (состояние_звука, exit_game).
    Если exit_on_esc=True, то ESC выходит из игры полностью, иначе возвращает False.
    """
    # Создаем моноширинный шрифт для правильного отображения таблицы
    mono_font_names = ["consolas", "courier new", "courier", "monospace", "liberation mono"]
    mono_font = None
    
    for font_name in mono_font_names:
        try:
            mono_font = pygame.font.SysFont(font_name, 18)
            break
        except (OSError, ValueError):
            continue
    
    if mono_font is None:
        try:
            mono_font = pygame.font.Font(pygame.font.get_default_font(), 18)
        except:
            mono_font = font

    sound_enabled = True
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return sound_enabled, True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if exit_on_esc:
                        return sound_enabled, True
                    else:
                        waiting = False
                elif event.key == pygame.K_BACKSPACE:
                    waiting = False
                elif event.key == pygame.K_m:
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True

        # Отрисовка экрана рекордов
        screen.fill((10, 10, 30))

        # Заголовок
        title = font.render("ТАБЛИЦА РЕКОРДОВ", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 30))
        screen.blit(title, title_rect)

        highscores = highscore_manager.get_top_scores()

        if not highscores:
            no_scores = font.render("Пока нет рекордов", True, (200, 200, 200))
            no_scores_rect = no_scores.get_rect(center=(SCREEN_WIDTH // 2, 150))
            screen.blit(no_scores, no_scores_rect)
        else:
            separator_line = "=" * 69
            separator_surf = mono_font.render(separator_line, True, (150, 150, 150))
            separator_rect = separator_surf.get_rect(center=(SCREEN_WIDTH // 2, 70))
            screen.blit(separator_surf, separator_rect)

            headers = "   Место | Игрок               | Очки | Время  "
            headers_surf = mono_font.render(headers, True, (255, 255, 255))
            headers_rect = headers_surf.get_rect(center=(SCREEN_WIDTH // 2, 95))
            screen.blit(headers_surf, headers_rect)

            separator_surf2 = mono_font.render(separator_line, True, (150, 150, 150))
            separator_rect2 = separator_surf2.get_rect(center=(SCREEN_WIDTH // 2, 120))
            screen.blit(separator_surf2, separator_rect2)

            y_offset = 145
            for i, score_data in enumerate(highscores, 1):
                if i < 10:
                    place = f"   {i}.  "
                else:
                    place = f"  {i}.  "

                player_name = score_data["player_name"]
                player = f"{player_name[:20]:<20}"
                score = f"{score_data['score']:>3}"
                time = f"{score_data['time_formatted']:>5}"

                row = f"{place}| {player}| {score}  | {time}"
                row_surf = mono_font.render(row, True, (255, 255, 255))
                row_rect = row_surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(row_surf, row_rect)

                y_offset += 25

        if exit_on_esc:
            render_colored_hint(
                screen,
                font,
                "Backspace - возврат, ESC - выход из игры",
                (SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT - 70),
            )
        else:
            render_colored_hint(
                screen,
                font,
                "BackSpace - возврат",
                (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 70),
            )

        pygame.display.flip()

    return sound_enabled, False


def trigger_instant_victory(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
    highscore_manager: "HighScoreManager",
    settings_manager: "SettingsManager",
    ball: "Ball",
) -> Tuple[bool, bool, bool]:
    """
    Показывает заставку победы и экран результатов.
    Используется для немедленной победы (например, при тройном нажатии "1").
    """
    if not getattr(sys, "frozen", False):
        print("[TRIGGER VICTORY] Вызываем show_victory_splash...")
    try:
        show_victory_splash(screen, duration_seconds=5.0)
        if not getattr(sys, "frozen", False):
            print("[TRIGGER VICTORY] show_victory_splash завершена")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[TRIGGER VICTORY] ОШИБКА в show_victory_splash: {e}")
            import traceback
            traceback.print_exc()
    
    return show_game_results(
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


def show_victory_splash(screen: pygame.Surface, duration_seconds: float = 5.0) -> None:
    """
    Показывает заставку победы с анимированным изображением.
    Использует PIL для загрузки анимированного GIF.
    """
    initial_screen_size = screen.get_size()
    if not getattr(sys, "frozen", False):
        print(f"[VICTORY SPLASH] Начальный размер экрана при входе в функцию: {initial_screen_size}")
    
    image_path = resource_path("images/d2.gif")
    
    if not getattr(sys, "frozen", False):
        print(f"[VICTORY SPLASH] Путь к изображению: {image_path}")
    
    try:
        try:
            from PIL import Image, ImageSequence
            
            screen_width, screen_height = screen.get_size()
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Размер экрана: {screen_width}x{screen_height} (НЕ МЕНЯЕМ!)")
            
            if hasattr(Image, 'Resampling'):
                lanczos_filter = Image.Resampling.LANCZOS
            else:
                lanczos_filter: Any = getattr(Image, 'LANCZOS', 1)
            
            with Image.open(image_path) as im:
                default_duration = im.info.get("duration", 100)
                
                frames = []
                frame_durations = []
                
                for i, frame in enumerate(ImageSequence.Iterator(im)):
                    resized_frame = frame.copy().resize((screen_width, screen_height), lanczos_filter)
                    
                    duration = frame.info.get("duration", default_duration)
                    frame_durations.append(duration)
                    
                    if resized_frame.mode != 'RGBA':
                        resized_frame = resized_frame.convert('RGBA')
                    
                    img_data = resized_frame.tobytes()
                    
                    try:
                        frame_surface = pygame.image.fromstring(
                            img_data, (screen_width, screen_height), 'RGBA'
                        )
                    except (AttributeError, TypeError):
                        frame_surface = pygame.image.frombuffer(
                            img_data, (screen_width, screen_height), 'RGBA'
                        )
                    frame_surface = frame_surface.convert_alpha()
                    
                    frames.append(frame_surface)
            
            if len(frames) == 0:
                raise ValueError("Не удалось загрузить кадры анимации")
            
            x = 0
            y = 0
            
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Загружено кадров: {len(frames)}, размер каждого: {screen_width}x{screen_height}")
            
            start_time = time.time()
            clock = pygame.time.Clock()
            frame_index = 0
            frame_accumulator = 0.0
            last_frame_time = time.time()
            
            if len(frames) == 1:
                while time.time() - start_time < duration_seconds:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    screen.fill((0, 0, 0))
                    screen.blit(frames[0], (x, y))
                    pygame.display.flip()
                    clock.tick(30)
            else:
                while time.time() - start_time < duration_seconds:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    
                    current_frame_time = time.time()
                    delta_time = current_frame_time - last_frame_time
                    last_frame_time = current_frame_time
                    frame_accumulator += delta_time
                    
                    frame_duration_sec = frame_durations[frame_index] / 1000.0
                    if frame_duration_sec < 0.033:
                        frame_duration_sec = 0.033
                    
                    if frame_accumulator >= frame_duration_sec:
                        old_index = frame_index
                        frame_index = (frame_index + 1) % len(frames)
                        frame_accumulator -= frame_duration_sec
                        
                        if old_index < 5 and not getattr(sys, "frozen", False):
                            print(f"[VICTORY SPLASH] Кадр изменен: {old_index} -> {frame_index}")
                    
                    screen.fill((0, 0, 0))
                    screen.blit(frames[frame_index], (x, y))
                    pygame.display.flip()
                    clock.tick(30)
                    
        except (ImportError, Exception) as e:
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Ошибка при загрузке через PIL: {e}, используем pygame для статического изображения")
            try:
                image = pygame.image.load(image_path)
                if not getattr(sys, "frozen", False):
                    print(f"[VICTORY SPLASH] Изображение загружено через pygame, размер: {image.get_size()}")
                
                screen_width, screen_height = screen.get_size()
                
                if image.get_bitsize() not in (24, 32):
                    image = image.convert()
                
                try:
                    image = pygame.transform.smoothscale(image, (screen_width, screen_height))
                except ValueError:
                    image = pygame.transform.scale(image, (screen_width, screen_height))
                
                x = 0
                y = 0
                
                start_time = time.time()
                while time.time() - start_time < duration_seconds:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    screen.fill((0, 0, 0))
                    screen.blit(image, (x, y))
                    pygame.display.flip()
                    pygame.time.Clock().tick(30)
            except Exception as e2:
                if not getattr(sys, "frozen", False):
                    print(f"[VICTORY SPLASH] Ошибка при загрузке изображения: {e2}")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[VICTORY SPLASH] Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()


def show_game_results(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
    highscore_manager: "HighScoreManager",
    settings_manager: "SettingsManager",
    ball: "Ball",
) -> Tuple[bool, bool, bool]:
    """
    Отображает экран результатов игры.
    Возвращает (состояние_звука, restart_game, exit_game).
    """
    sound_enabled = True
    restart_game = False
    exit_game = False
    waiting = True
    
    # Проверяем, является ли результат рекордом
    is_new_record = highscore_manager.is_new_record(score, game_time_seconds)
    
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return sound_enabled, False, True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    exit_game = True
                    waiting = False
                elif event.key == pygame.K_r:
                    restart_game = True
                    waiting = False
                elif event.key == pygame.K_m:
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True

        # Отрисовка экрана результатов
        screen.fill((20, 20, 40))

        # Заголовок
        if is_new_record:
            title_text = "НОВЫЙ РЕКОРД!"
            title_color = (255, 215, 0)
        else:
            title_text = "ИГРА ОКОНЧЕНА"
            title_color = (255, 255, 255)
        
        title = big_font.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        # Результаты
        score_text = font.render(f"Очки: {score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(score_text, score_rect)

        time_text = font.render(f"Время: {game_time_seconds} сек", True, (255, 255, 255))
        time_rect = time_text.get_rect(center=(SCREEN_WIDTH // 2, 240))
        screen.blit(time_text, time_rect)

        player_text = font.render(f"Игрок: {player_name}", True, (255, 255, 255))
        player_rect = player_text.get_rect(center=(SCREEN_WIDTH // 2, 280))
        screen.blit(player_text, player_rect)

        # Подсказки
        render_colored_hint(
            screen,
            font,
            "R - новая игра, ESC - выход",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100),
        )

        pygame.display.flip()

    return sound_enabled, restart_game, exit_game

