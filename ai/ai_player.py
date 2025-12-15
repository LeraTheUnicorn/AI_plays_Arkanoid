"""
Основной класс AIPlayer для управления авторежимом игры Арканоид.
"""

import time
import math
import random
import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .game_state import GameState, Point
from .trajectory_predictor import TrajectoryPredictor
from .async_trajectory_predictor import AsyncTrajectoryPredictor
from .position_optimizer import PositionOptimizer
from .learning_system import LearningSystem
from .lazy_learning_system import LazyLearningSystem, get_lazy_learning_system
from .performance_logger import PerformanceLogger
from .performance_monitor import PerformanceMonitor, get_performance_monitor
from .config import AIConfig
from .exceptions import (
    InvalidStateError,
    PredictionError,
    LearningError,
    DataError,
)
from .debug_logger import DebugLogger
from .platform_utils import is_frozen
from .targeting import TargetSelector, PositionCalculator
from .strategy import PaddleMovementStrategy, ZoneHandler, TargetTracker
from .logging_config import get_log_level, setup_root_logger

# КРИТИЧНО: Настраиваем root logger для всех модулей проекта при импорте AIPlayer
# Это гарантирует, что ВСЕ модули используют централизованную конфигурацию логирования
setup_root_logger()

import pygame

from .ai_player_models import BrickInfo, TargetingSystem, SeparationZoneTracker
from .ai_player_state import AIPlayerStateMixin
from .ai_player_targeting import AIPlayerTargetingMixin
from .ai_player_target_selection_part1 import AIPlayerTargetSelectionPart1Mixin
from .ai_player_target_selection_part2 import AIPlayerTargetSelectionPart2Mixin
from .ai_player_positioning import AIPlayerPositioningMixin
from .ai_player_movement import AIPlayerMovementMixin
from .ai_player_learning import AIPlayerLearningMixin
from .ai_player_init import AIPlayerInitMixin
from .ai_player_utils import AIPlayerUtilsMixin
from .ai_player_cache import AIPlayerCacheMixin
from .ai_player_zones import AIPlayerZonesMixin
from .ai_player_target_calculation import AIPlayerTargetCalculationMixin
from .ai_player_position_optimization_part1 import AIPlayerPositionOptimizationPart1Mixin
from .ai_player_position_optimization_part2 import AIPlayerPositionOptimizationPart2Mixin
from .ai_player_loop_prevention import AIPlayerLoopPreventionMixin
from .ai_player_ball_tracking import AIPlayerBallTrackingMixin
from .ai_player_fallback import AIPlayerFallbackMixin
from .ai_player_movement_helpers import AIPlayerMovementHelpersMixin
from .ai_player_movement_core_part1 import AIPlayerMovementCorePart1Mixin
from .ai_player_movement_core_part2 import AIPlayerMovementCorePart2Mixin
from .ai_player_movement_core_part3 import AIPlayerMovementCorePart3Mixin
from .ai_player_match_processing import AIPlayerMatchProcessingMixin
from .ai_player_debug_visualization import AIPlayerDebugVisualizationMixin
from .ai_player_reset import AIPlayerResetMixin
from .ai_player_metrics import AIPlayerMetricsMixin


class AIPlayer(
    AIPlayerInitMixin,
    AIPlayerUtilsMixin,
    AIPlayerCacheMixin,
    AIPlayerZonesMixin,
    AIPlayerTargetCalculationMixin,
    AIPlayerPositionOptimizationPart1Mixin,
    AIPlayerPositionOptimizationPart2Mixin,
    AIPlayerLoopPreventionMixin,
    AIPlayerBallTrackingMixin,
    AIPlayerFallbackMixin,
    AIPlayerMovementHelpersMixin,
    AIPlayerMovementCorePart1Mixin,
    AIPlayerMovementCorePart2Mixin,
    AIPlayerMovementCorePart3Mixin,
    AIPlayerStateMixin,
    AIPlayerTargetingMixin,
    AIPlayerTargetSelectionPart1Mixin,
    AIPlayerTargetSelectionPart2Mixin,
    AIPlayerPositioningMixin,
    AIPlayerMovementMixin,
    AIPlayerLearningMixin,
    AIPlayerMatchProcessingMixin,
    AIPlayerDebugVisualizationMixin,
    AIPlayerResetMixin,
    AIPlayerMetricsMixin,
):
    """
    Основной класс AIPlayer для управления авторежимом.

    Координирует работу всех компонентов AI системы:
    - TrajectoryPredictor для предсказания траектории мяча
    - PositionOptimizer для поиска оптимальной позиции платформы
    - LearningSystem для обучения на основе опыта
    - PerformanceLogger для логирования и аналитики
    """

    def __init__(
        self,
        screen_width: int = 800,
        screen_height: int = 600,
        debug_mode: bool = False,
        # Опциональные зависимости для инъекции (используются в тестах)
        trajectory_predictor: Optional[TrajectoryPredictor] = None,
        position_optimizer: Optional[PositionOptimizer] = None,
        learning_system: Optional[LearningSystem] = None,
        performance_logger: Optional[PerformanceLogger] = None,
        use_async_trajectory: bool = True,  # ✅ ИЗМЕНЕНО: Многопоточность включена по умолчанию
        async_max_workers: int = 2,
        use_lazy_learning: bool = True,
        enable_performance_monitoring: bool = True,
    ):
        """
        Инициализация AIPlayer.

        Args:
            screen_width: Ширина игрового экрана.
            screen_height: Высота игрового экрана.
            debug_mode: Режим отладки с визуализацией.
            trajectory_predictor: Опциональный предиктор траектории для инъекции зависимостей.
                Если не указан, создается новый экземпляр TrajectoryPredictor или AsyncTrajectoryPredictor.
            position_optimizer: Опциональный оптимизатор позиции для инъекции зависимостей.
                Если не указан, создается новый экземпляр PositionOptimizer.
            learning_system: Опциональная система обучения для инъекции зависимостей.
                Если не указана, создается новый экземпляр LearningSystem.
            performance_logger: Опциональный логгер производительности для инъекции зависимостей.
                Если не указан, создается новый экземпляр PerformanceLogger.
            use_async_trajectory: Если True, использует AsyncTrajectoryPredictor для асинхронных расчетов.
            async_max_workers: Количество потоков для асинхронного предиктора (по умолчанию 2).
            use_lazy_learning: Если True, использует ленивую загрузку LearningSystem (по умолчанию True).
            enable_performance_monitoring: Если True, включает мониторинг производительности (по умолчанию True).

        Raises:
            TypeError: Если типы параметров некорректны.
            ValueError: Если значения параметров некорректны.
        """
        # Валидация входных данных
        self._validate_dimensions(screen_width, screen_height)
        
        # Конфигурация
        self.config: AIConfig = AIConfig()
        
        # Компоненты системы
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = bool(debug_mode)
        
        # Настройка логирования для этого экземпляра
        # ВАЖНО: логирование настраивается ТОЛЬКО в logging_config.py, не зависит от debug_mode
        self._logger = self._setup_logging()

        # Инъекция зависимостей с fallback на значения по умолчанию
        if trajectory_predictor is None:
            if use_async_trajectory:
                self.trajectory_predictor = AsyncTrajectoryPredictor(
                    screen_width, screen_height, max_workers=async_max_workers
                )
            else:
                self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        else:
            self.trajectory_predictor = trajectory_predictor
        self.position_optimizer = (
            position_optimizer
            or PositionOptimizer(screen_width, screen_height)
        )
        
        # Ленивая загрузка LearningSystem для оптимизации старта
        if learning_system is not None:
            self.learning_system = learning_system
        elif use_lazy_learning:
            # Используем ленивую загрузку - LearningSystem создастся только при первом использовании
            self.learning_system = get_lazy_learning_system()
        else:
            # Прямое создание (для обратной совместимости)
            self.learning_system = LearningSystem()
        
        # Мониторинг производительности
        if enable_performance_monitoring:
            self.performance_monitor = get_performance_monitor()
        else:
            self.performance_monitor = None

        # Логирование производительности (включено по умолчанию для диагностики)
        enable_session_logging = self._get_env_bool("AI_ENABLE_SESSION_LOGGING", default=True)
        self.performance_logger = (
            performance_logger
            or PerformanceLogger(enable_session_logging=enable_session_logging)
        )
        # КРИТИЧНО: НЕ создаем файл лога сразу при старте - это может блокировать выполнение
        # Файл лога будет создан автоматически при первом вызове save_session_log()
        # Это предотвращает блокировку при создании AIPlayer

        # Состояние AI
        self.current_game_state: Optional[GameState] = None
        self.last_paddle_position: Optional[float] = None
        self.last_action_time = time.time()
        
        # Адаптивная частота расчетов
        self._last_calculation_time = 0.0
        self._calculation_skip_counter = 0
        self._adaptive_calculation_enabled = True
        self._trajectory_stability_counter = 0  # Счетчик стабильности траектории

        # Общие метрики
        self.performance_metrics: Dict[str, Any] = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
            "best_time_50_bricks": None,  # Лучшее время для матча с 50 блоками (в секундах)
        }

        # Статистика текущей игры
        self.current_game_stats: Dict[str, Any] = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }

        # Флаг активности
        self.is_active = False

        # Система прицельного отбивания
        self.targeting_system: TargetingSystem = TargetingSystem()

        # Система предотвращения зацикливания
        self.loop_prevention_system: Dict[str, Any] = {
            "movement_history": [],  # История последних движений
            "position_history": [],  # История позиций платформы
            "trajectory_history": [],  # История траекторий мяча
            "loop_detection_threshold": self.config.loop_detection_threshold,  # Порог повторений
            "strategy_change_cooldown": 0,  # Кулдаун смены стратегии
            "alternative_strategies": [
                "center_focus",
                "edge_focus",
                "predictive_targeting",
            ],
            "current_strategy_index": 0,
        }

        # Система отслеживания плавности движения
        self.smoothness_system: Dict[str, Any] = {
            "recent_movements": [],  # История последних движений (значения: -1, 0, 1)
            "recent_positions": [],  # История последних позиций
            "movement_changes": [],  # История смен направления движения
            "jitter_threshold": 3,  # Порог дрожания (количество смен направления)
            "jitter_window": 8,  # Окно анализа для дрожания
            "min_movement_distance": self.config.paddle.min_movement_distance,  # Минимальное расстояние для движения (пиксели)
            "smoothness_penalty": 0.0,  # Текущий штраф за дрожание (0.0 - 1.0)
            "consecutive_stops": 0,  # Количество последовательных остановок (поощряется)
        }

        # Параметры платформы
        self.paddle_width = self.config.paddle.width
        
        # Оптимизированное логирование (счетчик кадров вместо random)
        self._debug_logger = DebugLogger(log_interval=self.config.debug_log_interval)

        # Кэш карты кирпичей для оптимизации производительности
        self._brick_map_cache: Optional[tuple] = None  # (cache_key, brick_map, brick_coordinates)
        self._brick_cache_stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
        }

        # Последний множитель скорости платформы (для обучения)
        self._last_paddle_speed_multiplier = 1.0
        # Последняя скорректированная скорость платформы
        self._last_adjusted_paddle_speed: Optional[int] = None

        # Метрики по сессиям (серии игр)
        self.session_metrics: List[Dict[str, Any]] = []
        self.session_counter: int = 0

        # Параметры для обучения в режиме обучения
        # Параметры режима обучения
        # Начальная скорость мяча: 30 (из централизованных констант)
        try:
            from game.game_config import BALL_SPEED_DEFAULT
            initial_ball_speed = BALL_SPEED_DEFAULT
        except ImportError:
            initial_ball_speed = 30  # Fallback значение
        
        self.training_parameters: Dict[str, Any] = {
            "ball_speed": initial_ball_speed,  # Текущая скорость мяча (начальная скорость для обучения)
            "paddle_speed_multiplier": 2.0,  # Множитель скорости платформы (высокий для быстрой игры)
            "total_bricks_destroyed": 0,  # Всего кубиков сбито за матч
            "total_time": 0,  # Общее время матча
            "lives_lost": 0,  # Потерянные жизни
            "match_history": [],  # История матчей
        }
        
        # Отслеживание отбитий в пустоту
        self.empty_bounce_tracker: Dict[str, Any] = {
            "consecutive_empty_bounces": 0,  # Количество последовательных отбитий в пустоту
            "last_bounce_position": None,  # Последняя позиция платформы при отбитии
            "last_bounce_time": 0,  # Время последнего отбития
            "max_empty_bounces": 1,  # Максимум отбитий в пустоту подряд (уменьшено с 2 до 1)
            "bounce_history": [],  # История отбитий (для анализа)
            "ceiling_bounces": 0,  # Количество отскоков от потолка без попадания в кубики
        }
        
        # КРИТИЧНО: Отслеживание входа в зону разделения для одноразового движения платформы
        self.separation_zone_tracker: SeparationZoneTracker = SeparationZoneTracker()
        
        # Отслеживание предыдущей позиции и скорости мяча для обнаружения отскоков от кирпичей
        self._last_ball_position: Optional[Point] = None
        self._last_ball_velocity: Optional[Point] = None
        # КРИТИЧНО: Отслеживание позиции мяча при последнем расчете целевой позиции
        self._last_target_ball_x: Optional[float] = None
        
        # Инициализация модульных классов
        # TargetSelector для выбора целевых кирпичей
        self.target_selector = TargetSelector(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            config=self.config,
            trajectory_predictor=self.trajectory_predictor,
            targeting_system=self.targeting_system,
        )
        
        # PositionCalculator для расчета позиций
        self.position_calculator = PositionCalculator(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            paddle_width=self.paddle_width,
            config=self.config,
            trajectory_predictor=self.trajectory_predictor,
            targeting_system=self.targeting_system,
        )
        
        # ZoneHandler для обработки зон
        self.zone_handler = ZoneHandler(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            config=self.config,
            separation_zone_tracker=self.separation_zone_tracker,
        )
        
        # TargetTracker для отслеживания целевой позиции
        self.target_tracker = TargetTracker(
            config=self.config,
            separation_zone_tracker=self.separation_zone_tracker,
        )
        
        # PaddleMovementStrategy для стратегии движения (инициализируется позже, так как требует функции)
        self.paddle_movement_strategy: Optional[PaddleMovementStrategy] = None

    # Методы _validate_dimensions, _get_env_bool, _cleanup_old_logs, _setup_logging
    # теперь в ai_player_init.py
    
    # Методы activate, deactivate, _should_log_debug, is_ball_moving_towards_paddle
    # теперь в ai_player_utils.py

    # ==========================
    # Обновление состояния игры
    # ==========================
    # Методы _invalidate_trajectory_cache, update_game_state, _should_skip_heavy_calculations,
    # _should_skip_calculation, _get_current_trajectory_prediction теперь в ai_player_state.py

    # ==========================
    # Работа с кубиками/целями
    # ==========================
    # Методы _generate_brick_cache_key, _update_brick_map, get_brick_cache_stats,
    # _update_visible_targets, _find_best_target_brick, _find_optimal_angle_for_max_destruction,
    # _count_bricks_in_trajectory, _find_first_brick_in_trajectory, _find_best_target_for_few_bricks,
    # _calculate_optimal_offset, _adjust_offset_from_history, record_hit_result
    # теперь в ai_player_targeting.py

    # Методы _generate_brick_cache_key, _update_brick_map, get_brick_cache_stats,
    # _update_visible_targets теперь в ai_player_targeting.py

    # Метод get_brick_cache_stats теперь в ai_player_cache.py
    # Метод _update_visible_targets теперь в ai_player_targeting.py

    # Методы _calculate_zones, _handle_bricks_zone, _handle_separation_zone, _handle_upward_movement
    # теперь в ai_player_zones.py

    # Методы _calculate_target_position, _calculate_precision_position, _calculate_position_with_target_brick,
    # _ensure_safe_paddle_position, _calculate_fallback_position, _set_target_position_if_needed
    # теперь в ai_player_target_calculation.py

    # ==========================
    # Выбор целевого кирпича
    # ==========================
    # Метод _find_best_target_brick теперь в ai_player_targeting.py
    # Метод _calculate_precise_position_for_few_bricks теперь в ai_player_positioning.py
    # Метод get_optimal_paddle_position теперь в ai_player_position_optimization_part1.py
    # Методы _force_target_brick_from_coordinates, _calculate_position_for_max_destruction
    # теперь в ai_player_position_optimization_part1.py
    # Методы _find_optimal_angle_for_max_destruction, _count_bricks_in_trajectory,
    # _find_first_brick_in_trajectory, _find_best_target_for_few_bricks, _calculate_optimal_offset
    # теперь в ai_player_position_optimization_part2.py

    def _log_paddle_movement(self, from_x: float, to_x: float, reason: str, confidence: float = 1.0) -> None:
        """
        Логирует передвижение платформы для анализа.
        
        Args:
            from_x: Текущая X-координата платформы (float, будет преобразован в int)
            to_x: Целевая X-координата платформы (float, будет преобразован в int)
            reason: Причина передвижения
            confidence: Уверенность в решении (0.0-1.0)
        """
        if hasattr(self, 'performance_logger'):
            self.performance_logger.log_paddle_movement(int(from_x), int(to_x), reason, confidence)

    # Методы _calculate_position_for_max_destruction, _find_optimal_angle_for_max_destruction,
    # _count_bricks_in_trajectory, _find_first_brick_in_trajectory, _find_best_target_for_few_bricks,
    # _calculate_optimal_offset теперь в ai_player_position_optimization.py

    # ==========================
    # Расчёт смещения по платформе
    # ==========================
    # Метод _calculate_optimal_offset теперь в ai_player_position_optimization.py

    # Методы _calculate_optimal_offset, _adjust_offset_from_history теперь в ai_player_target_selection_part2.py

    # ==========================
    # Предотвращение зацикливания
    # ==========================
    # Методы _detect_loop_pattern, _change_strategy_if_looping, _apply_alternative_strategy,
    # _find_most_distant_brick, _update_loop_tracking, _update_smoothness_tracking,
    # _detect_jitter, _calculate_smooth_movement теперь в ai_player_loop_prevention.py

    # ==========================
    # Запись результатов ударов
    # ==========================
    # Метод record_hit_result теперь в ai_player_targeting.py

    # ==========================
    # Предсказание траектории и позиционирование
    # ==========================
    # Методы _predict_exact_landing_position, _calculate_precise_position_for_few_bricks
    # теперь в ai_player_positioning.py
    # Методы _reevaluate_after_bounce, _handle_ceiling_bounce_positioning, _track_ball_position,
    # calculate_adaptive_paddle_speed теперь в ai_player_ball_tracking.py

    # ==========================
    # Движение платформы
    # ==========================

    # Методы _execute_movement_strategy, _validate_movement_conditions, _calculate_optimal_position
    # теперь в ai_player_movement_helpers.py

    def _apply_movement_strategy(self, current_x: int, optimal_x: int, paddle_speed: int) -> int:
        """
        Применяет стратегию движения к платформе.
        
        Args:
            current_x: Текущая X-координата платформы.
            optimal_x: Оптимальная X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        import time
        start_time_monitor = time.time() if self.performance_monitor else None
        
        try:
            # Вызываем первую часть метода (начальная валидация и ПРАВИЛО 3)
            result = self._apply_movement_strategy_part1(current_x, optimal_x, paddle_speed)
            if result is not None:
                return result
            
            # Если первая часть вернула None, продолжаем обработку
            # Определяем переменные для следующих частей
            if not self.current_game_state:
                return self._fallback_movement(current_x)
            
            ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity"))
                else 0
            )
            separation_zone_start = self.separation_zone_tracker.separation_zone_start
            paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
            paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
            ball_lost = ball_y > paddle_y
            in_separation_zone = separation_zone_start <= ball_y < paddle_y and ball_vel_y > 0
            
            # Вызываем вторую часть метода (ПРАВИЛО 4)
            result = self._apply_movement_strategy_part2(
                current_x, optimal_x, paddle_speed,
                ball_y, ball_vel_y, separation_zone_start, paddle_zone_start,
                paddle_y, ball_lost, in_separation_zone, start_time_monitor
            )
            if result is not None:
                return result
            
            # Если вторая часть вернула None, вызываем третью часть (ПРАВИЛО 5)
            return self._apply_movement_strategy_part3(
                current_x, optimal_x, paddle_speed, ball_lost, start_time_monitor
            )
        
        except (AttributeError, TypeError) as e:
            self._logger.error(f"Ошибка типов при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)
        except InvalidStateError as e:
            self._logger.error(f"Недопустимое состояние при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)

    # Методы _fallback_movement, _is_time_pressure, _calculate_decision_confidence
    # теперь в ai_player_fallback.py

    # Методы learn_from_result, _update_performance_metrics теперь в ai_player_learning_core_part1.py
    # Методы on_game_end, _reset_game_state_trackers, _reset_current_game_stats теперь в ai_player_learning_core_part2.py
    # Методы _print_ml_system_metrics, _save_session_metrics, _print_learning_progress_comparison теперь в ai_player_metrics.py

    # Методы reset_learning, reset_for_testing, save_learning_data, load_learning_data
    # теперь в ai_player_reset.py
    # Методы visualize_debug_info, _draw_predicted_trajectory теперь в ai_player_debug_visualization.py
    # Методы _process_training_match, _learn_from_match_results, _get_average_efficiency,
    # get_optimal_ball_speed, get_optimal_paddle_speed_multiplier, get_adjusted_paddle_speed,
    # update_training_stats, _print_training_parameters, _print_console_summary теперь в ai_player_match_processing.py
