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
    from .settings import SettingsManager
    from .game_models import Ball
except ImportError:
    from game.game_config import SCREEN_WIDTH, SCREEN_HEIGHT
    from game.game_rendering import render_colored_hint
    from game.settings import SettingsManager
    from game.game_models import Ball


def show_game_results(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
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
