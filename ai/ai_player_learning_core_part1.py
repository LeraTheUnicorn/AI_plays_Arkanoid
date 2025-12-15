"""
Модуль первой части методов обучения для AIPlayer.

Содержит методы обучения на основе результатов действий и обновления метрик производительности.
"""

import time
from typing import Dict, Any


class AIPlayerLearningCorePart1Mixin:
    """
    Миксин для первой части методов обучения.
    Добавляет методы обучения на основе результатов действий.
    """

    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI-систему на основе результата последнего действия.
        """
        if not isinstance(action_result, dict):
            raise ValueError("action_result должен быть словарем")

        if not action_result:
            raise ValueError("action_result не может быть пустым")

        if not self.current_game_state:
            return

        enhanced_result = action_result.copy()
        enhanced_result.update(
            {
                "game_state_before": {
                    "ball_position": {
                        "x": self.current_game_state.ball_position.x,
                        "y": self.current_game_state.ball_position.y,
                    },
                    "paddle_position": {
                        "x": self.current_game_state.paddle_position.x,
                        "y": self.current_game_state.paddle_position.y,
                    },
                    "bricks_remaining": len(self.current_game_state.remaining_bricks),
                    "ball_speed": self.current_game_state.ball_speed,
                },
                "trajectory_prediction": self._get_current_trajectory_prediction(),
            }
        )

        action_type = action_result.get("action_type", "")

        if action_type == "brick_hit":
            bricks_destroyed = action_result.get("bricks_destroyed", [])
            for brick in bricks_destroyed:
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))
                self.record_hit_result(brick, paddle_offset, success=True)

        elif action_type == "paddle_bounce":
            bricks_before = enhanced_result.get("game_state_before", {}).get("bricks_remaining", 0)
            bricks_after = len(self.current_game_state.remaining_bricks) if self.current_game_state else 0
            
            if bricks_before == bricks_after and bricks_before > 0:
                self.empty_bounce_tracker["consecutive_empty_bounces"] += 1
                self.empty_bounce_tracker["last_bounce_position"] = self.current_game_state.paddle_position.x if self.current_game_state else None
                self.empty_bounce_tracker["last_bounce_time"] = time.time()
                self.empty_bounce_tracker["bounce_history"].append({
                    "position": self.current_game_state.paddle_position.x if self.current_game_state else 0,
                    "bricks_remaining": bricks_after,
                    "time": time.time(),
                })
                if len(self.empty_bounce_tracker["bounce_history"]) > 10:
                    self.empty_bounce_tracker["bounce_history"] = self.empty_bounce_tracker["bounce_history"][-5:]
            else:
                self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
            
            if self.targeting_system.target_brick:
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))

                enhanced_result["targeting_info"] = {
                    "target_brick": self.targeting_system.target_brick,
                    "optimal_offset": self.targeting_system.optimal_offset,
                    "actual_offset": paddle_offset,
                }

                self._reevaluate_after_bounce()

        self.learning_system.update_strategy(enhanced_result)

        if hasattr(self, "_last_paddle_speed_multiplier") and self.current_game_state:
            success_flag = action_result.get("success", False)
            ball_speed = self.current_game_state.ball_speed
            self.learning_system.update_paddle_speed_feedback(
                ball_speed,
                self._last_paddle_speed_multiplier,
                success_flag,
            )

        self.performance_logger.log_action(enhanced_result)
        self._update_performance_metrics(action_result)

    def _update_performance_metrics(self, action_result: Dict[str, Any]) -> None:
        """Обновляет метрики производительности на основе результата действия."""
        success = action_result.get("success", False)

        if success:
            self.current_game_stats["successful_predictions"] += 1

        if "bricks_destroyed" in action_result:
            bricks_value = action_result["bricks_destroyed"]
            if action_result.get("action_type") == "game_end":
                if isinstance(bricks_value, int):
                    max_bricks = 50
                    self.current_game_stats["bricks_destroyed"] = min(bricks_value, max_bricks)
                elif isinstance(bricks_value, list):
                    max_bricks = 50
                    self.current_game_stats["bricks_destroyed"] = min(len(bricks_value), max_bricks)
            else:
                if isinstance(bricks_value, int):
                    self.current_game_stats["bricks_destroyed"] += bricks_value
                elif isinstance(bricks_value, list):
                    self.current_game_stats["bricks_destroyed"] += len(bricks_value)
                
                max_bricks = 50
                if self.current_game_stats["bricks_destroyed"] > max_bricks:
                    self.current_game_stats["bricks_destroyed"] = max_bricks

        self.current_game_stats["total_predictions"] += 1

        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]
