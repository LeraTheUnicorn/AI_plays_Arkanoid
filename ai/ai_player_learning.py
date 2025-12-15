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


class AIPlayerLearningMixin(AIPlayerLearningCorePart1Mixin):
    """
    Миксин для методов обучения и метрик.
    Добавляет методы обучения, обновления метрик и обработки результатов игры.
    """
    
    # Методы learn_from_result и _update_performance_metrics теперь в ai_player_learning_core_part1.py

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

    def get_optimal_ball_speed(self) -> int:
        """Возвращает оптимальную скорость мяча на основе обучения."""
        return int(self.training_parameters["ball_speed"])

    def get_optimal_paddle_speed_multiplier(self) -> float:
        """Возвращает оптимальный множитель скорости платформы на основе обучения."""
        return float(self.training_parameters["paddle_speed_multiplier"])

    def get_adjusted_paddle_speed(self, base_speed: int) -> int:
        """Возвращает скорректированную скорость платформы с учетом адаптации AI."""
        if self._last_adjusted_paddle_speed is not None:
            return self._last_adjusted_paddle_speed
        return base_speed

    def update_training_stats(
        self, bricks_destroyed: int, time_elapsed: float, lives_lost: int
    ) -> None:
        """Обновляет статистику обучения во время игры."""
        self.training_parameters["total_bricks_destroyed"] = bricks_destroyed
        self.training_parameters["total_time"] = time_elapsed
        self.training_parameters["lives_lost"] = lives_lost

    def _get_average_efficiency(self) -> float:
        """Вычисляет среднюю эффективность за последние матчи."""
        if not self.training_parameters["match_history"]:
            return 0.0

        total_efficiency = 0.0
        for match in self.training_parameters["match_history"]:
            bricks = match["bricks_destroyed"]
            time_taken = max(match["time"], 1)
            lives_lost = match["lives_lost"]
            time_penalty = 1.0 + (lives_lost * 0.2)
            efficiency = bricks / (time_taken * time_penalty)
            total_efficiency += efficiency

        return float(total_efficiency / len(self.training_parameters["match_history"]))

    def _process_training_match(self, success: bool, final_score: int) -> None:
        """Обрабатывает результаты матча в режиме обучения."""
        bricks_destroyed = self.current_game_stats.get("bricks_destroyed", 0)
        time_taken = (
            time.time() - self.current_game_stats["start_time"]
            if self.current_game_stats["start_time"]
            else 0
        )
        lives_lost = 3 - self.current_game_stats.get("lives_left", 3)

        match_data = {
            "bricks_destroyed": bricks_destroyed,
            "time": time_taken,
            "lives_lost": lives_lost,
            "ball_speed": self.training_parameters["ball_speed"],
            "paddle_speed_multiplier": self.training_parameters["paddle_speed_multiplier"],
        }

        self.training_parameters["match_history"].append(match_data)
        if len(self.training_parameters["match_history"]) > 10:
            self.training_parameters["match_history"] = self.training_parameters["match_history"][-10:]

        all_bricks_destroyed = bricks_destroyed >= 50
        time_penalty = 1.0 + (lives_lost * 0.2)
        efficiency = bricks_destroyed / (time_taken * time_penalty)

        current_ball_speed = self.training_parameters["ball_speed"]
        current_paddle_mult = self.training_parameters["paddle_speed_multiplier"]
        
        if not hasattr(self, '_best_performance_params'):
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult
            }
        
        if bricks_destroyed > self._best_performance_params['bricks_destroyed']:
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult
            }
        
        if len(self.training_parameters["match_history"]) >= 2:
            recent_games = self.training_parameters["match_history"][-2:]
            recent_avg_bricks = sum(g["bricks_destroyed"] for g in recent_games) / len(recent_games)
            best_bricks = self._best_performance_params['bricks_destroyed']
            
            if best_bricks > 0 and recent_avg_bricks < best_bricks * 0.5:
                self._logger.warning(f"[PERFORMANCE PROTECTION] Обнаружена деградация производительности!")
                self.training_parameters["ball_speed"] = self._best_performance_params['ball_speed']
                self.training_parameters["paddle_speed_multiplier"] = self._best_performance_params['paddle_speed_multiplier']
                current_ball_speed = self.training_parameters["ball_speed"]
                current_paddle_mult = self.training_parameters["paddle_speed_multiplier"]

        target_time = 5.0
        time_ratio = time_taken / target_time if target_time > 0 else 1.0

        if not all_bricks_destroyed:
            bricks_remaining = 50 - bricks_destroyed
            
            if bricks_destroyed < 20 or (lives_lost >= 3 and bricks_destroyed < 30):
                speed_reduction = min(3, bricks_remaining // 10)
                if current_ball_speed > 15:
                    min_speed = 15
                    if hasattr(self, '_best_performance_params') and self._best_performance_params['bricks_destroyed'] >= 40:
                        min_speed = max(15, self._best_performance_params['ball_speed'] - 5)
                    
                    self.training_parameters["ball_speed"] = max(
                        min_speed, current_ball_speed - speed_reduction
                    )
                
                if lives_lost >= 3 and bricks_destroyed < 20:
                    min_paddle_mult = 1.5
                    if hasattr(self, '_best_performance_params') and self._best_performance_params['bricks_destroyed'] >= 40:
                        min_paddle_mult = max(1.5, self._best_performance_params['paddle_speed_multiplier'] - 0.5)
                    
                    if current_paddle_mult > min_paddle_mult:
                        self.training_parameters["paddle_speed_multiplier"] = max(
                            min_paddle_mult, current_paddle_mult - 0.2
                        )
        elif all_bricks_destroyed and lives_lost <= 1:
            if time_ratio > 1.2:
                if current_ball_speed < 25:
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.1
                    )
            elif time_ratio < 0.8 and efficiency > 8.0:
                if current_ball_speed < 25:
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )

        if len(self.training_parameters["match_history"]) <= 2:
            if bricks_destroyed >= 45 and lives_lost <= 1:
                if current_ball_speed < 25:
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 2
                    )
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.2
                    )
        else:
            avg_efficiency = self._get_average_efficiency()

            if avg_efficiency > 0 and all_bricks_destroyed:
                if time_ratio > 1.2:
                    if current_ball_speed < 25:
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    if current_paddle_mult < 3.0:
                        self.training_parameters["paddle_speed_multiplier"] = min(
                            3.0, current_paddle_mult + 0.1
                        )
                elif efficiency > avg_efficiency * 1.1:
                    if current_ball_speed < 25:
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    if current_paddle_mult < 3.0:
                        self.training_parameters["paddle_speed_multiplier"] = min(
                            3.0, current_paddle_mult + 0.1
                        )

    def _print_ml_system_metrics(self, success: bool, final_score: int) -> None:
        """Выводит метрики оценки работы системы scikit-learn в лог."""
        try:
            self._logger.info("\n" + "=" * 70)
            self._logger.info("МЕТРИКИ ОЦЕНКИ РАБОТЫ СИСТЕМЫ AI (scikit-learn)")
            self._logger.info("=" * 70)
            
            self._logger.info(f"\n[РЕЗУЛЬТАТЫ] Результаты игры:")
            result_text = "[+] ПОБЕДА" if success else "[-] ПОРАЖЕНИЕ"
            self._logger.info(f"   Результат: {result_text}")
            self._logger.info(f"   Финальный счёт: {final_score}")
            self._logger.info(f"   Всего игр: {self.performance_metrics['games_played']}")
            self._logger.info(f"   Побед: {self.performance_metrics['games_won']}")
            if self.performance_metrics["games_played"] > 0:
                win_rate = (
                    self.performance_metrics["games_won"]
                    / self.performance_metrics["games_played"]
                ) * 100
                self._logger.info(f"   Процент побед: {win_rate:.1f}%")
            
            self._logger.info(f"\n[МЕТРИКИ] Метрики текущей игры:")
            self._logger.info(
                f"   Уничтожено кубиков: {self.current_game_stats['bricks_destroyed']}"
            )
            self._logger.info(
                f"   Всего предсказаний: {self.current_game_stats['total_predictions']}"
            )
            if self.current_game_stats["total_predictions"] > 0:
                prediction_accuracy = (
                    self.current_game_stats["successful_predictions"]
                    / self.current_game_stats["total_predictions"]
                ) * 100
                self._logger.info(f"   Точность предсказаний: {prediction_accuracy:.1f}%")
            
            learning_progress = self.learning_system.get_learning_progress()
            
            if (
                isinstance(learning_progress, dict)
                and learning_progress.get("total_iterations", 0) > 0
            ):
                self._logger.info(f"\n[ОБУЧЕНИЕ] Система обучения (scikit-learn):")
                self._logger.info(
                    f"   Всего итераций обучения: {learning_progress.get('total_iterations', 0)}"
                )
                self._logger.info(
                    f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                )
            
            self._logger.info("=" * 70 + "\n")
        except Exception as e:
            self._logger.error(f"\n[ОШИБКА] Ошибка при выводе метрик: {e}\n", exc_info=True)

    def _save_session_metrics(self, success: bool, final_score: int) -> None:
        """Сохраняет агрегированные метрики по завершённой игре в список сессий."""
        session_data = {
            "session_id": self.session_counter,
            "success": success,
            "final_score": final_score,
            "bricks_destroyed": self.current_game_stats.get("bricks_destroyed", 0),
            "accuracy": (
                self.current_game_stats["successful_predictions"]
                / self.current_game_stats["total_predictions"]
                if self.current_game_stats["total_predictions"] > 0
                else 0.0
            ),
        }
        self.session_metrics.append(session_data)
        self.session_counter += 1

    def _print_training_parameters(self) -> None:
        """Выводит средние значения параметров обучения в лог."""
        if not self.training_parameters["match_history"]:
            return

        self._logger.info("\n" + "=" * 70)
        self._logger.info("ПАРАМЕТРЫ ОБУЧЕНИЯ ИИ")
        self._logger.info("=" * 70)

        avg_ball_speed = sum(
            m["ball_speed"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_paddle_mult = sum(
            m["paddle_speed_multiplier"]
            for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_bricks = sum(
            m["bricks_destroyed"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_time = sum(
            m["time"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_lives_lost = sum(
            m["lives_lost"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_efficiency = self._get_average_efficiency()

        self._logger.info(
            f"\nСредние значения за последние {len(self.training_parameters['match_history'])} матчей:"
        )
        self._logger.info(f"   Скорость мяча: {avg_ball_speed:.1f}")
        self._logger.info(f"   Множитель скорости платформы: {avg_paddle_mult:.2f}")
        self._logger.info(f"   Кубиков за матч: {int(round(avg_bricks))}")
        self._logger.info(f"   Время матча: {avg_time:.1f} сек")
        self._logger.info(f"   Потерянных жизней: {int(round(avg_lives_lost))}")
        self._logger.info(
            f"   Эффективность: {avg_efficiency:.3f} (кубики/(время * штраф_за_жизни))"
        )

        self._logger.info(f"\nТекущие параметры:")
        self._logger.info(f"   Скорость мяча: {self.training_parameters['ball_speed']}")
        self._logger.info(
            f"   Множитель скорости платформы: {self.training_parameters['paddle_speed_multiplier']:.2f}"
        )
    
    def _print_console_summary(self, success: bool, final_score: int) -> None:
        """Выводит краткую сводку после матча в консоль."""
        try:
            win_rate = 0.0
            if self.performance_metrics["games_played"] > 0:
                win_rate = (
                    self.performance_metrics["games_won"]
                    / self.performance_metrics["games_played"]
                ) * 100
            
            result_icon = "[OK]" if success else "[FAIL]"
            result_text = "ПОБЕДА" if success else "ПОРАЖЕНИЕ"
            
            print("\n" + "=" * 60)
            print(f"{result_icon} {result_text} | Счет: {final_score}/50")
            print(f"   Игр: {self.performance_metrics['games_played']} | Побед: {self.performance_metrics['games_won']} | Винрейт: {win_rate:.1f}%")
            print("=" * 60)
            
            if hasattr(self._logger, 'handlers') and self._logger.handlers:
                for handler in self._logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        log_file = handler.baseFilename
                        print(f"   Подробные логи: {log_file}")
                        break
            print()
        except Exception:
            pass
