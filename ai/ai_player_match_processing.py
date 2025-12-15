"""
Модуль для обработки матчей и обучения в AIPlayer.

Содержит методы обработки результатов матчей, расчета эффективности и вывода метрик.
"""

import time
import logging
from typing import Dict, Any


class AIPlayerMatchProcessingMixin:
    """
    Миксин для методов обработки матчей и обучения.
    Добавляет методы обработки результатов матчей, расчета эффективности и вывода метрик.
    """

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
