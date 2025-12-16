"""
Тесты для модуля game_config.py
"""

import pytest
from game.game_config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    PADDLE_WIDTH,
    PADDLE_HEIGHT,
    PADDLE_SPEED,
    BALL_SIZE,
    BALL_SPEED_DEFAULT,
    BRICK_ROWS,
    BRICK_COLS,
    BRICK_WIDTH,
    BRICK_HEIGHT,
    BRICK_PADDING,
    BRICK_OFFSET_TOP,
    MAX_LIVES,
    SEPARATION_ZONE_TOP,
    SEPARATION_ZONE_BOTTOM,
    BRICK_COLORS,
    BACKGROUND_COLOR,
    BRICK_BORDER_COLOR,
    TEXT_COLOR,
    FONT_NAME,
    FONT_SIZE,
    BIG_FONT_SIZE,
    MONO_FONT_SIZE,
    MONO_FONT_NAMES,
    SOUND_DEFAULT_VOLUME,
    MUSIC_DEFAULT_VOLUME,
    PADDLE_SOUND_FREQUENCY,
    PADDLE_SOUND_DURATION,
    PADDLE_SOUND_VOLUME,
    USE_DIRTY_RECTS,
    DIRTY_RECT_BUFFER,
)


class TestGameConfig:
    """Тесты для конфигурации игры."""

    def test_screen_dimensions(self):
        """Тест размеров экрана."""
        assert SCREEN_WIDTH == 800
        assert SCREEN_HEIGHT == 600
        assert FPS == 60

    def test_paddle_config(self):
        """Тест конфигурации платформы."""
        assert PADDLE_WIDTH == 120
        assert PADDLE_HEIGHT == 15
        assert PADDLE_SPEED == 45

    def test_ball_config(self):
        """Тест конфигурации мяча."""
        assert BALL_SIZE == 16
        assert BALL_SPEED_DEFAULT == 5

    def test_brick_config(self):
        """Тест конфигурации кирпичей."""
        assert BRICK_ROWS == 5
        assert BRICK_COLS == 10
        assert BRICK_WIDTH == 60
        assert BRICK_HEIGHT == 20
        assert isinstance(BRICK_PADDING, int)
        assert isinstance(BRICK_OFFSET_TOP, int)

    def test_game_constants(self):
        """Тест игровых констант."""
        assert MAX_LIVES == 3
        assert SEPARATION_ZONE_TOP == 226
        assert SEPARATION_ZONE_BOTTOM == 540

    def test_colors(self):
        """Тест цветов."""
        assert len(BRICK_COLORS) == 5
        assert all(
            isinstance(color, tuple) and len(color) == 3 for color in BRICK_COLORS
        )
        assert isinstance(BACKGROUND_COLOR, tuple)
        assert len(BACKGROUND_COLOR) == 3
        assert isinstance(BRICK_BORDER_COLOR, tuple)
        assert len(BRICK_BORDER_COLOR) == 3
        assert isinstance(TEXT_COLOR, tuple)
        assert len(TEXT_COLOR) == 3

    def test_font_config(self):
        """Тест конфигурации шрифтов."""
        assert isinstance(FONT_NAME, str)
        assert FONT_SIZE == 20
        assert BIG_FONT_SIZE == 42
        assert MONO_FONT_SIZE == 18
        assert isinstance(MONO_FONT_NAMES, list)
        assert len(MONO_FONT_NAMES) > 0

    def test_sound_config(self):
        """Тест конфигурации звука."""
        assert 0.0 <= SOUND_DEFAULT_VOLUME <= 1.0
        assert 0.0 <= MUSIC_DEFAULT_VOLUME <= 1.0
        assert isinstance(PADDLE_SOUND_FREQUENCY, int)
        assert PADDLE_SOUND_FREQUENCY > 0
        assert PADDLE_SOUND_DURATION > 0
        assert 0.0 <= PADDLE_SOUND_VOLUME <= 1.0

    def test_optimization_config(self):
        """Тест конфигурации оптимизации."""
        assert isinstance(USE_DIRTY_RECTS, bool)
        assert isinstance(DIRTY_RECT_BUFFER, int)
        assert DIRTY_RECT_BUFFER >= 0
