"""
Модуль утилит AIPlayer.

Содержит вспомогательные методы: активация/деактивация, проверки, утилиты.
"""

import logging
from typing import Dict, Any

from .strategy import PaddleMovementStrategy


class AIPlayerUtilsMixin:
    """Миксин для утилитарных методов AIPlayer."""

    def activate(self) -> None:
        """
        Активирует AIPlayer для управления игрой.
        """
        self.is_active = True
        
        # Инициализируем PaddleMovementStrategy при активации
        if self.paddle_movement_strategy is None:
            self.paddle_movement_strategy = PaddleMovementStrategy(
                screen_width=self.screen_width,
                screen_height=self.screen_height,
                paddle_width=self.paddle_width,
                config=self.config,
                position_optimizer=self.position_optimizer,
                learning_system=self.learning_system,
                zone_handler=self.zone_handler,
                target_tracker=self.target_tracker,
                get_optimal_paddle_position_func=self.get_optimal_paddle_position,
                loop_prevention_system=self.loop_prevention_system,
                smoothness_system=self.smoothness_system,
                separation_zone_tracker=self.separation_zone_tracker,
                logger=self._logger,
                log_paddle_movement_func=self._log_paddle_movement,
                should_log_debug_func=self._should_log_debug,
                trajectory_predictor=self.trajectory_predictor,  # ✅ ДОБАВЛЕНО: Передаем trajectory_predictor
                predict_exact_landing_position_func=self._predict_exact_landing_position,  # ✅ ДОБАВЛЕНО: Передаем функцию предсказания
                current_game_state=self.current_game_state,
            )
        
        self._logger.info("AIPlayer активирован. Начинаем управление игрой...")

    def deactivate(self) -> None:
        """
        Деактивирует AIPlayer.
        """
        self.is_active = False
        self._logger.info("AIPlayer деактивирован.")

    def _should_log_debug(self, interval_multiplier: int = 1) -> bool:
        """
        Проверяет, нужно ли логировать отладочную информацию в текущем кадре.
        
        Проверяет уровень логирования логгера (не зависит от debug_mode).
        Логирование настраивается ТОЛЬКО в logging_config.py.
        
        ВАЖНО: Если уровень логгера DEBUG или ниже, возвращает True всегда 
        (без интервального ограничения), так как пользователь явно установил 
        DEBUG уровень и хочет видеть все сообщения.
        
        Args:
            interval_multiplier: Множитель интервала (для более редкого логирования).
                                Используется только если уровень > DEBUG.
                                Например, 10 означает логирование в 10 раз реже.
        
        Returns:
            True, если нужно логировать, False иначе
        """
        # Получаем эффективный уровень логгера (с учетом родительских логгеров)
        effective_level = self._logger.getEffectiveLevel()
        
        # Проверяем уровень логирования логгера, а не debug_mode
        # Если эффективный уровень выше DEBUG - не логируем DEBUG сообщения
        if effective_level > logging.DEBUG:
            return False
        
        # Если эффективный уровень DEBUG или ниже - логируем ВСЕ сообщения 
        # (без интервального ограничения)
        # Пользователь явно установил DEBUG уровень и хочет видеть все DEBUG сообщения
        return True
    
    def is_ball_moving_towards_paddle(self) -> bool:
        """Проверяет, движется ли мяч к платформе (вниз)."""
        if not self.current_game_state:
            return False
        return self.current_game_state.is_ball_falling()
