"""
Модуль для обучения и метрик в AIPlayer.
Содержит методы обучения, обновления метрик и обработки результатов игры.
"""

import time
import logging
from typing import Dict, Optional, Any

from .game_state import GameState, Point
from .exceptions import PredictionError
from .ai_player_learning_core_part1 import AIPlayerLearningCorePart1Mixin
from .ai_player_learning_core_part2 import AIPlayerLearningCorePart2Mixin
from .ai_player_match_processing import AIPlayerMatchProcessingMixin


class AIPlayerLearningMixin(
    AIPlayerLearningCorePart1Mixin,
    AIPlayerLearningCorePart2Mixin,
    AIPlayerMatchProcessingMixin,
):
    """
    Миксин для методов обучения и метрик.
    Добавляет методы обучения, обновления метрик и обработки результатов игры.
    """

    # Методы learn_from_result и _update_performance_metrics теперь в ai_player_learning_core_part1.py
    # Методы on_game_end, _reset_game_state_trackers, _reset_current_game_stats теперь в ai_player_learning_core_part2.py

    def _is_time_pressure(self) -> bool:
        """Определяет, есть ли давление по времени/ситуации."""
        if not self.current_game_state:
            return False

        game_time = self.current_game_state.game_time
        if game_time > 300:
            return True

        if len(self.current_game_state.remaining_bricks) <= 5:
            return True

        return False

    def _calculate_decision_confidence(self, target_position: int) -> float:
        """Рассчитывает уверенность в принятом решении."""
        if not self.current_game_state:
            return 0.5

        confidence = 0.7

        bricks_count = len(self.current_game_state.remaining_bricks)
        if bricks_count <= 5:
            confidence += 0.1
        elif bricks_count >= 20:
            confidence -= 0.1

        ball_speed = self.current_game_state.ball_speed
        if ball_speed >= 8:
            confidence -= 0.1
        elif ball_speed <= 3:
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    # Методы get_optimal_ball_speed, get_optimal_paddle_speed_multiplier, get_adjusted_paddle_speed,
    # update_training_stats, _get_average_efficiency, _process_training_match,
    # _print_ml_system_metrics, _save_session_metrics, _print_training_parameters,
    # _print_console_summary теперь в ai_player_match_processing.py
