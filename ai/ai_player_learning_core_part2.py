"""
Модуль второй части методов обучения для AIPlayer.

Содержит методы обработки окончания игры, сброса состояния и вспомогательные методы.
"""

import time
import logging
from typing import Dict, Optional, Any

from .game_state import GameState, Point


class AIPlayerLearningCorePart2Mixin:
    """
    Миксин для второй части методов обучения.
    Добавляет методы обработки окончания игры и сброса состояния.
    """

    def on_game_end(
        self, success: bool, final_score: int, training_mode: bool = False
    ) -> None:
        """
        Обрабатывает окончание игры.
        """
        if final_score < 0:
            raise ValueError("Final_score не может быть отрицательным")

        self.performance_metrics["games_played"] += 1
        if success:
            self.performance_metrics["games_won"] += 1

        if self.current_game_stats["total_predictions"] > 0:
            accuracy = (
                self.current_game_stats["successful_predictions"]
                / self.current_game_stats["total_predictions"]
            )
            self.performance_metrics["average_accuracy"] = (
                self.performance_metrics["average_accuracy"] * 0.9 + accuracy * 0.1
            )

        learning_progress = self.learning_system.get_learning_progress()
        if isinstance(learning_progress, dict):
            if "message" in learning_progress:
                learning_progress_value = 0.0
            else:
                success_rate = learning_progress.get("success_rate", 0.0)
                total_iterations = learning_progress.get("total_iterations", 0)
                avg_improvement = learning_progress.get("average_improvement", 0.0)
                iteration_factor = 1.0 - (2.71828 ** (-total_iterations / 10.0))
                learning_progress_value = success_rate * iteration_factor + min(
                    avg_improvement, 0.3
                )
                learning_progress_value = max(0.0, min(1.0, learning_progress_value))
        else:
            learning_progress_value = (
                float(learning_progress) if learning_progress else 0.0
            )

        self.performance_metrics["learning_progress"] = (
            self.performance_metrics["learning_progress"] * 0.9
            + learning_progress_value * 0.1
        )

        if self.current_game_state is None:
            empty_state = GameState(
                ball_position=Point(0, 0),
                ball_velocity=Point(0, 0),
                paddle_position=Point(0, 0),
                paddle_width=self.paddle_width,
                remaining_bricks=[],
                game_score=final_score,
                game_time=0,
                ball_speed=0,
            )
            game_state = empty_state
        else:
            game_state = self.current_game_state

        self.performance_logger.log_game_end(game_state, success, final_score)

        if training_mode:
            self._process_training_match(success, final_score)

        self._save_session_metrics(success, final_score)
        self._print_ml_system_metrics(success, final_score)

        if training_mode:
            self._print_training_parameters()

        self._print_console_summary(success, final_score)

        self._reset_current_game_stats()
        self._reset_game_state_trackers()

    def _reset_game_state_trackers(self) -> None:
        """Сбрасывает все трекеры состояния игры для новой игры."""
        self.separation_zone_tracker.ball_entered_separation_zone = False
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        self.separation_zone_tracker.last_movement_frame = 0

        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["ceiling_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0

        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0

        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        self.smoothness_system["consecutive_stops"] = 0

    def _reset_current_game_stats(self) -> None:
        """Сбрасывает статистику текущей игры."""
        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }
