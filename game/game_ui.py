"""
UI функции для игры Арканоид.
Содержит функции для отображения окон, заставок и результатов игры.
"""

import os
import sys
import time
from typing import Tuple, Optional, Any
import pygame  # pyright: ignore[reportMissingImports]

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
    mono_font_names = [
        "consolas",
        "courier new",
        "courier",
        "monospace",
        "liberation mono",
    ]
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

        time_text = font.render(
            f"Время: {game_time_seconds} сек", True, (255, 255, 255)
        )
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
