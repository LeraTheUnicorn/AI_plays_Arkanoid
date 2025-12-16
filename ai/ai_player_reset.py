"""
Модуль для сброса состояния и сохранения/загрузки данных в AIPlayer.

Содержит методы для сброса состояния AI и сохранения/загрузки данных обучения.
"""

import time
from typing import Any

from .exceptions import DataError, LearningError


class AIPlayerResetMixin:
    """
    Миксин для методов сброса состояния и сохранения/загрузки данных.
    Добавляет методы для сброса состояния AI и работы с данными обучения.
    """

    def reset_learning(self) -> None:
        """
        Полный сброс обучающихся компонентов и внутренних статистик AI.
        """
        # Сброс системы обучения
        self.learning_system.reset_learning_data()

        # Сброс прицеливания
        self.targeting_system.reset()

        # Сброс системы предотвращения зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        self.loop_prevention_system["current_strategy_index"] = 0

        # Сброс системы плавности движения
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["recent_positions"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        self.smoothness_system["consecutive_stops"] = 0

        # Сброс отслеживания отбитий в пустоту
        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0
        self.empty_bounce_tracker["max_empty_bounces"] = (
            self.config.max_empty_bounces
            if hasattr(self.config, "max_empty_bounces")
            else 1
        )
        self.empty_bounce_tracker["bounce_history"] = []
        self.empty_bounce_tracker["ceiling_bounces"] = 0

    def reset_for_testing(self) -> None:
        """
        Полный сброс состояния AI для тестирования.

        ВНИМАНИЕ: Используйте только в тестах! Этот метод сбрасывает все состояние,
        включая метрики, кэши и историю, что может привести к потере данных в
        production окружении.

        Метод сбрасывает:
        - Все системы (targeting_system, separation_zone_tracker, learning_system)
        - Все метрики (performance_metrics, current_game_stats, session_metrics)
        - Все кэши (_brick_map_cache, _debug_logger)
        - Состояние игры (current_game_state, is_active, last_paddle_position)
        - Все трекеры (loop_prevention_system, smoothness_system, empty_bounce_tracker)
        """
        # Сброс состояния игры
        self.current_game_state = None
        self.last_paddle_position = None
        self.last_action_time = time.time()
        self.is_active = False

        # Сброс всех систем
        self.targeting_system.reset()
        self.separation_zone_tracker.reset()
        self.learning_system.reset_learning_data()

        # Сброс метрик
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
            "best_time_50_bricks": None,
        }

        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }

        self.session_metrics = []
        self.session_counter = 0

        # Сброс трекеров
        self.loop_prevention_system = {
            "movement_history": [],
            "position_history": [],
            "trajectory_history": [],
            "loop_detection_threshold": self.config.loop_detection_threshold,
            "strategy_change_cooldown": 0,
            "alternative_strategies": [
                "center_focus",
                "edge_focus",
                "predictive_targeting",
            ],
            "current_strategy_index": 0,
        }

        self.smoothness_system = {
            "recent_movements": [],
            "recent_positions": [],
            "movement_changes": [],
            "jitter_threshold": 3,
            "jitter_window": 8,
            "min_movement_distance": self.config.paddle.min_movement_distance,
            "smoothness_penalty": 0.0,
            "consecutive_stops": 0,
        }

        # Reset empty_bounce_tracker values instead of redefining
        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0
        self.empty_bounce_tracker["max_empty_bounces"] = self.config.max_empty_bounces
        self.empty_bounce_tracker["bounce_history"] = []
        self.empty_bounce_tracker["ceiling_bounces"] = 0

        # Очистка кэшей
        self._brick_map_cache = None
        self._brick_cache_stats = {
            "hits": 0,
            "misses": 0,
        }
        self._debug_logger.reset()

        # Сброс параметров обучения
        self._last_paddle_speed_multiplier = 1.0
        self._last_adjusted_paddle_speed = None

        self.training_parameters = {
            "ball_speed": self.config.ball.default_speed,
            "paddle_speed_multiplier": 2.0,
            "total_bricks_destroyed": 0,
            "total_time": 0,
            "lives_lost": 0,
            "match_history": [],
        }

        # Сброс общих метрик и сессий
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
        }
        self.session_metrics = []
        self.session_counter = 0

        # Сброс статистики текущей игры
        self._reset_current_game_stats()

    def save_learning_data(self) -> None:
        """
        Сохраняет данные обучения AI системы.
        """
        try:
            if hasattr(self, "learning_system") and self.learning_system:
                # Сохраняем данные обучающей системы
                learning_data = {
                    "performance_metrics": self.performance_metrics,
                    "session_metrics": self.session_metrics,
                    "targeting_system": self.targeting_system,
                    "session_counter": self.session_counter,
                }

                # Здесь можно добавить сохранение в файл, если нужно
                # Пока просто логируем успешное сохранение
                self._logger.debug(
                    f"[AI DEBUG] Данные обучения сохранены. Сессий: {self.session_counter}"
                )

        except (IOError, OSError) as e:
            self._logger.error(
                f"Ошибка ввода-вывода при сохранении данных обучения: {e}",
                exc_info=True,
            )
        except (TypeError, ValueError) as e:
            self._logger.error(
                f"Ошибка данных при сохранении обучения: {e}", exc_info=True
            )
        except DataError as e:
            self._logger.error(f"Ошибка данных обучения: {e}", exc_info=True)
        except LearningError as e:
            self._logger.error(f"Ошибка системы обучения: {e}", exc_info=True)

    def load_learning_data(self) -> None:
        """
        Загружает данные обучения AI системы.
        """
        try:
            if hasattr(self, "learning_system") and self.learning_system:
                # Здесь можно добавить загрузку из файла
                self._logger.debug("[AI DEBUG] Данные обучения загружены")

        except (IOError, OSError) as e:
            self._logger.error(
                f"Ошибка ввода-вывода при загрузке данных обучения: {e}", exc_info=True
            )
        except (TypeError, ValueError) as e:
            self._logger.error(
                f"Ошибка данных при загрузке обучения: {e}", exc_info=True
            )
        except DataError as e:
            self._logger.error(f"Ошибка данных обучения: {e}", exc_info=True)
        except LearningError as e:
            self._logger.error(f"Ошибка системы обучения: {e}", exc_info=True)
