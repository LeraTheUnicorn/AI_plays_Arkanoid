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
        use_async_trajectory: bool = False,
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
        # Максимальная скорость мяча: 8 (с учетом времени движения платформы в зоне разделения)
        self.training_parameters: Dict[str, Any] = {
            "ball_speed": 8,  # Текущая скорость мяча (начальная скорость для обучения, ограничена временем движения платформы)
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

    def _update_visible_targets(self) -> None:
        """
        Обновляет список видимых целей (кубиков), в которые можно прицельно ударить
        с учётом текущей траектории мяча и возможных смещений по платформе.
        """
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            self.targeting_system.visible_targets = []
            return

        try:
            # Точка приземления мяча при текущей траектории
            landing_x = self._predict_exact_landing_position()

            visible_targets: List[Dict[str, Any]] = []

            # Несколько тестовых смещений платформы относительно точки приземления
            test_offsets = [-40, -20, 0, 20, 40]

            for offset in test_offsets:
                test_x = landing_x + offset

                # Строго ограничиваем позицию возможного центра платформы
                paddle_half_width = self.paddle_width / 2
                test_x = max(
                    paddle_half_width,
                    min(self.screen_width - paddle_half_width, test_x),
                )

                # Временное состояние игры с тестовой позицией платформы
                temp_game_state = self.current_game_state.clone()
                temp_game_state.paddle_position.x = test_x

                # Точка пересечения мяча с платформой
                intersection_point = (
                    self.trajectory_predictor.predict_paddle_intersection(
                        temp_game_state,
                        self.current_game_state.paddle_position.y,
                    )
                )
                if intersection_point is None:
                    continue

                # Траектория после отскока с данной позиции
                after_bounce_trajectory = (
                    self.trajectory_predictor.predict_after_bounce_trajectory(
                        temp_game_state,
                        intersection_point,
                        test_x,
                    )
                )

                # Проверяем, какие кубики пересекает эта траектория
                # Используем точную проверку пересечения с границами кубиков
                for coord in self.targeting_system.brick_coordinates:
                    brick = coord["brick"]
                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", self.config.brick.default_width)
                    brick_height = getattr(brick, "height", 20)
                    
                    # Точные границы кубика
                    brick_left = brick_x
                    brick_right = brick_x + brick_width
                    brick_top = brick_y
                    brick_bottom = brick_y + brick_height
                    
                    # Радиус мяча для проверки пересечения
                    ball_radius = self.config.ball.radius
                    
                    # Проверяем пересечение траектории с кубиком
                    # Используем более частую проверку для точности
                    for point in after_bounce_trajectory:
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue
                            
                        # Проверяем пересечение мяча (с учетом радиуса) с границами кубика
                        if (
                            brick_left - ball_radius
                            <= point.x
                            <= brick_right + ball_radius
                            and brick_top - ball_radius
                            <= point.y
                            <= brick_bottom + ball_radius
                        ):
                            # Дополнительная проверка: мяч действительно попадает в кубик
                            # Проверяем, что центр мяча находится в расширенной области кубика
                            if (
                                brick_left <= point.x <= brick_right
                                or brick_top <= point.y <= brick_bottom
                                or math.sqrt(
                                    (point.x - (brick_left + brick_right) / 2) ** 2
                                    + (point.y - (brick_top + brick_bottom) / 2) ** 2
                                )
                                < (brick_width / 2 + ball_radius)
                            ):
                                if coord not in visible_targets:
                                    visible_targets.append(coord)
                                break

            self.targeting_system.visible_targets = visible_targets
        except (AttributeError, TypeError, ValueError) as e:
            self._logger.warning(f"Ошибка при обновлении видимых целей: {e}", exc_info=True)
            self.targeting_system.visible_targets = []
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при обновлении видимых целей: {e}", exc_info=True)
            self.targeting_system.visible_targets = []

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

    # ==========================
    # Обучение по результату действия
    # ==========================

    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI-систему на основе результата последнего действия.

        Args:
            action_result: Словарь с информацией о результате (hit/miss, счёт и т.д.).

        Raises:
            ValueError: Если action_result не является словарем или пуст.
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

        # Запись результата для системы прицеливания
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
            # Отслеживаем отбития в пустоту
            bricks_before = enhanced_result.get("game_state_before", {}).get("bricks_remaining", 0)
            bricks_after = len(self.current_game_state.remaining_bricks) if self.current_game_state else 0
            
            # Если количество блоков не изменилось после отскока - это отбитие в пустоту
            if bricks_before == bricks_after and bricks_before > 0:
                self.empty_bounce_tracker["consecutive_empty_bounces"] += 1
                self.empty_bounce_tracker["last_bounce_position"] = self.current_game_state.paddle_position.x if self.current_game_state else None
                self.empty_bounce_tracker["last_bounce_time"] = time.time()
                self.empty_bounce_tracker["bounce_history"].append({
                    "position": self.current_game_state.paddle_position.x if self.current_game_state else 0,
                    "bricks_remaining": bricks_after,
                    "time": time.time(),
                })
                # Ограничиваем историю
                if len(self.empty_bounce_tracker["bounce_history"]) > 10:
                    self.empty_bounce_tracker["bounce_history"] = self.empty_bounce_tracker["bounce_history"][-5:]
            else:
                # Блок был сбит - сбрасываем счетчик
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

                # После отскока переоцениваем ситуацию
                self._reevaluate_after_bounce()

        # Обновляем стратегию обучения
        self.learning_system.update_strategy(enhanced_result)

        # Обратная связь по скорости платформы
        if hasattr(self, "_last_paddle_speed_multiplier") and self.current_game_state:
            success_flag = action_result.get("success", False)
            ball_speed = self.current_game_state.ball_speed
            self.learning_system.update_paddle_speed_feedback(
                ball_speed,
                self._last_paddle_speed_multiplier,
                success_flag,
            )

        # Логирование действия
        self.performance_logger.log_action(enhanced_result)

        # Обновление метрик
        self._update_performance_metrics(action_result)

    # Методы _should_skip_heavy_calculations, _should_skip_calculation, 
    # _get_current_trajectory_prediction теперь в ai_player_state.py

    # ==========================
    # Метрики и окончание игры
    # ==========================

    def _update_performance_metrics(self, action_result: Dict[str, Any]) -> None:
        """Обновляет метрики производительности на основе результата действия."""
        success = action_result.get("success", False)

        if success:
            self.current_game_stats["successful_predictions"] += 1

        if "bricks_destroyed" in action_result:
            bricks_value = action_result["bricks_destroyed"]
            # КРИТИЧНО: Если это окончание игры (game_end), устанавливаем значение напрямую, а не накапливаем
            # Это предотвращает неправильный подсчет при повторных вызовах
            if action_result.get("action_type") == "game_end":
                # При окончании игры bricks_destroyed - это общее количество за всю игру
                if isinstance(bricks_value, int):
                    # КРИТИЧНО: Ограничиваем значение максимумом кубиков в игре (50)
                    # Это предотвращает отображение неправильных значений (например, 70 вместо 50)
                    max_bricks = 50  # Максимальное количество кубиков в игре
                    self.current_game_stats["bricks_destroyed"] = min(bricks_value, max_bricks)
                elif isinstance(bricks_value, list):
                    max_bricks = 50
                    self.current_game_stats["bricks_destroyed"] = min(len(bricks_value), max_bricks)
            else:
                # Для других событий накапливаем значение
                if isinstance(bricks_value, int):
                    self.current_game_stats["bricks_destroyed"] += bricks_value
                elif isinstance(bricks_value, list):
                    self.current_game_stats["bricks_destroyed"] += len(bricks_value)
                
                # КРИТИЧНО: Ограничиваем накопленное значение максимумом кубиков в игре
                max_bricks = 50
                if self.current_game_stats["bricks_destroyed"] > max_bricks:
                    self.current_game_stats["bricks_destroyed"] = max_bricks

        self.current_game_stats["total_predictions"] += 1

        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]

    def on_game_end(
        self, success: bool, final_score: int, training_mode: bool = False
    ) -> None:
        """
        Обрабатывает окончание игры.

        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
            training_mode: True, если это режим обучения.

        Raises:
            ValueError: Если final_score отрицательный.
        """
        if final_score < 0:
            raise ValueError("Final_score не может быть отрицательным")

        self.performance_metrics["games_played"] += 1
        if success:
            self.performance_metrics["games_won"] += 1

        # Точность предсказаний
        if self.current_game_stats["total_predictions"] > 0:
            accuracy = (
                self.current_game_stats["successful_predictions"]
                / self.current_game_stats["total_predictions"]
            )
            self.performance_metrics["average_accuracy"] = (
                self.performance_metrics["average_accuracy"] * 0.9 + accuracy * 0.1
            )

        # Прогресс обучения
        learning_progress = self.learning_system.get_learning_progress()
        if isinstance(learning_progress, dict):
            # Если learning_progress - словарь, вычисляем прогресс на основе метрик
            if "message" in learning_progress:
                # Обучение еще не начато
                learning_progress_value = 0.0
            else:
                # Используем success_rate как основной показатель прогресса
                success_rate = learning_progress.get("success_rate", 0.0)
                # Учитываем также количество итераций и улучшения
                total_iterations = learning_progress.get("total_iterations", 0)
                avg_improvement = learning_progress.get("average_improvement", 0.0)
                # Прогресс = успешность * (1 - exp(-итерации/10)) + улучшение
                iteration_factor = 1.0 - (2.71828 ** (-total_iterations / 10.0))
                learning_progress_value = success_rate * iteration_factor + min(
                    avg_improvement, 0.3
                )
                learning_progress_value = max(0.0, min(1.0, learning_progress_value))
        else:
            # Если learning_progress не словарь, преобразуем в float
            learning_progress_value = (
                float(learning_progress) if learning_progress else 0.0
            )

        self.performance_metrics["learning_progress"] = (
            self.performance_metrics["learning_progress"] * 0.9
            + learning_progress_value * 0.1
        )

        # Логирование окончания игры
        # Создаем минимальное состояние игры, если его нет
        if self.current_game_state is None:
            # Создаем пустое состояние для логирования
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

        # В режиме обучения обрабатываем результаты матча
        if training_mode:
            self._process_training_match(success, final_score)

        # Сохраняем данные по сессии и подготавливаемся к новой игре
        self._save_session_metrics(success, final_score)
        
        # Выводим метрики оценки работы системы scikit-learn (в файл)
        self._print_ml_system_metrics(success, final_score)
        
        # В режиме обучения выводим средние значения параметров (в файл)
        if training_mode:
            self._print_training_parameters()
        
        # Выводим краткую сводку в консоль
        self._print_console_summary(success, final_score)

        self._reset_current_game_stats()
        
        # КРИТИЧНО: Сбрасываем все трекеры состояния для новой игры
        self._reset_game_state_trackers()

    def _reset_game_state_trackers(self) -> None:
        """Сбрасывает все трекеры состояния игры для новой игры."""
        # Сбрасываем отслеживание зоны разделения
        self.separation_zone_tracker.ball_entered_separation_zone = False
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        self.separation_zone_tracker.last_movement_frame = 0
        
        # Сбрасываем отслеживание отбитий в пустоту
        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["ceiling_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0
        
        # Сбрасываем историю зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        
        # Сбрасываем историю плавности движения
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        self.smoothness_system["consecutive_stops"] = 0
        
        # КРИТИЧНО: НЕ сбрасываем current_game_state в None, так как это блокирует движение
        # Вместо этого состояние будет обновлено при следующем вызове update_game_state
        # Если сбросить в None, move_paddle_towards вернет _fallback_movement и платформа не будет двигаться
        # self.current_game_state = None  # ЗАКОММЕНТИРОВАНО - не сбрасываем!

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

    def _print_ml_system_metrics(self, success: bool, final_score: int) -> None:
        """
        Выводит метрики оценки работы системы scikit-learn в лог.
        
        Args:
            success: True, если игра выиграна.
            final_score: Итоговый счёт игры.
        """
        try:
            self._logger.info("\n" + "=" * 70)
            self._logger.info("МЕТРИКИ ОЦЕНКИ РАБОТЫ СИСТЕМЫ AI (scikit-learn)")
            self._logger.info("=" * 70)
            
            # Базовые метрики игры
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
            
            # Метрики текущей игры
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
            self._logger.info(f"   Всего ходов: {self.current_game_stats['total_moves']}")
            if self.current_game_stats["total_moves"] > 0:
                optimal_move_rate = (
                    self.current_game_stats["optimal_moves"]
                    / self.current_game_stats["total_moves"]
                ) * 100
                self._logger.info(f"   Оптимальных ходов: {optimal_move_rate:.1f}%")
            
            # Метрики обучения и scikit-learn
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
                self._logger.info(
                    f"   Средний прогресс: {learning_progress.get('average_improvement', 0.0):.2%}"
                )
                
                # Кластеризация траекторий (KMeans)
                self._logger.info(f"\n[КЛАСТЕРИЗАЦИЯ] Кластеризация траекторий (KMeans):")
                trajectory_clusters = self.learning_system.cluster_trajectories()
                unique_clusters = learning_progress.get("trajectory_clusters_count", 0)
                cluster_diversity = learning_progress.get("cluster_diversity", 0.0)
                trajectory_patterns = learning_progress.get("trajectory_patterns", 0)
                
                self._logger.info(f"   Найдено паттернов траекторий: {trajectory_patterns}")
                self._logger.info(f"   Количество кластеров: {unique_clusters}")
                self._logger.info(f"   Разнообразие кластеров: {cluster_diversity:.3f}")
                
                if trajectory_clusters:
                    # Анализ распределения по кластерам
                    cluster_counts: Dict[int, int] = {}
                    for item in trajectory_clusters:
                        cluster_id = item.get("cluster", -1)
                        cluster_counts[cluster_id] = (
                            cluster_counts.get(cluster_id, 0) + 1
                        )
                    
                    self._logger.info(f"   Распределение по кластерам:")
                    for cluster_id, count in sorted(cluster_counts.items()):
                        percentage = (count / len(trajectory_clusters)) * 100
                        self._logger.info(
                            f"      Кластер {cluster_id}: {count} паттернов ({percentage:.1f}%)"
                        )
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для кластеризации")
                
                # Модель предсказания успеха (RandomForestClassifier)
                self._logger.info(f"\n[МОДЕЛЬ] Модель предсказания успеха (RandomForestClassifier):")
                model = self.learning_system.learning_data.get(
                    "success_prediction_model"
                )
                model_metrics = self.learning_system.learning_data.get(
                    "model_metrics", {}
                )
                
                if model is not None:
                    self._logger.info(f"   [+] Модель обучена и готова к использованию")
                    
                    # Показываем метрики модели
                    model_accuracy = model_metrics.get("last_accuracy")
                    if model_accuracy is not None:
                        self._logger.info(f"   Точность модели (accuracy): {model_accuracy:.2%}")
                    
                    training_samples = model_metrics.get("training_samples", 0)
                    test_samples = model_metrics.get("test_samples", 0)
                    features_count = model_metrics.get("features_count", 0)
                    
                    if training_samples > 0:
                        self._logger.info(f"   Образцов для обучения: {training_samples}")
                        self._logger.info(f"   Образцов для тестирования: {test_samples}")
                        self._logger.info(f"   Количество признаков: {features_count}")
                    
                    # Получаем информацию о факторах успеха
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        self._logger.info(f"   Факторы успеха:")
                        for factor_name, factor_data in success_factors.items():
                            total = factor_data.get("total_cases", 0)
                            successful = factor_data.get("successful_cases", 0)
                            if total > 0:
                                success_rate = (successful / total) * 100
                                self._logger.info(
                                    f"      {factor_name}: {successful}/{total} успешных ({success_rate:.1f}%)"
                                )
                else:
                    self._logger.info(
                        f"   [ВНИМАНИЕ]  Модель ещё не обучена (требуется минимум 100 итераций)"
                    )
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        total_cases = sum(
                            f.get("total_cases", 0) for f in success_factors.values()
                        )
                        self._logger.info(f"   Накоплено данных: {total_cases} случаев")
                        iterations_needed = max(
                            0,
                            100 - (learning_progress.get("total_iterations", 0) % 100),
                        )
                        self._logger.info(
                            f"   До следующего обучения: {iterations_needed} итераций"
                        )
                
                # Веса стратегий
                strategy_weights = learning_progress.get("strategy_weights", {})
                if strategy_weights:
                    self._logger.info(f"\n[ВЕСА]  Веса стратегий:")
                    for strategy, weight in strategy_weights.items():
                        bar_length = int(weight * 20)
                        bar = "█" * bar_length + "░" * (20 - bar_length)
                        self._logger.info(f"   {strategy:12s}: {bar} {weight:.3f}")
                
                # Предпочтения позиций (убрано по запросу пользователя)
                # learned_positions = learning_progress.get('learned_positions', 0)
                # self._logger.info(f"\n📍 Изученные позиции: {learned_positions}")
                
            else:
                self._logger.info(f"\n[ВНИМАНИЕ]  Система обучения ещё не накопила достаточно данных")
                self._logger.info(
                    f"   Продолжайте играть для активации кластеризации и предсказания"
                )
            
            # Общая оценка системы
            self._logger.info(f"\n[ОЦЕНКА] Общая оценка системы:")
            if isinstance(learning_progress, dict):
                avg_accuracy = self.performance_metrics.get("average_accuracy", 0.0)
                learning_prog = self.performance_metrics.get("learning_progress", 0.0)
                
                # Комплексная оценка
                if learning_progress.get("total_iterations", 0) > 0:
                    # Базовые компоненты оценки
                    prediction_accuracy_weight = 0.3
                    learning_progress_weight = 0.25
                    success_rate_weight = 0.25
                    model_accuracy_weight = 0.2
                    
                    system_score = (
                        avg_accuracy * prediction_accuracy_weight
                        + learning_prog * learning_progress_weight
                        + (learning_progress.get("success_rate", 0.0))
                        * success_rate_weight
                    ) * 100
                    
                    # Добавляем оценку модели предсказания, если она обучена
                    model_accuracy = learning_progress.get("prediction_model_accuracy")
                    if model_accuracy is not None:
                        system_score += model_accuracy * model_accuracy_weight * 100
                        self._logger.info(f"   Точность ML модели: {model_accuracy:.2%}")
                    else:
                        # Если модель не обучена, перераспределяем веса
                        adjusted_weight = (
                            prediction_accuracy_weight
                            + learning_progress_weight
                            + success_rate_weight
                        )
                        system_score = (
                            system_score / (1 - model_accuracy_weight) * adjusted_weight
                        )
                    
                    self._logger.info(f"   Средняя точность предсказаний: {avg_accuracy:.2%}")
                    self._logger.info(f"   Прогресс обучения: {learning_prog:.2%}")
                    self._logger.info(
                        f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                    )
                    self._logger.info(f"   Комплексная оценка системы: {system_score:.1f}/100")
                    
                    if system_score >= 80:
                        self._logger.info(f"   [ОТЛИЧНО] Система работает эффективно")
                    elif system_score >= 60:
                        self._logger.info(f"   [ХОРОШО] Система работает стабильно")
                    elif system_score >= 40:
                        self._logger.info(f"   [УДОВЛЕТВОРИТЕЛЬНО] Система обучается")
                    else:
                        self._logger.info(f"   [ТРЕБУЕТ УЛУЧШЕНИЯ] Недостаточно данных")
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для комплексной оценки")
            
            self._logger.info("=" * 70 + "\n")
        except (AttributeError, TypeError, KeyError) as e:
            # В случае ошибки выводим минимальную информацию
            # КРИТИЧНО: Не используем эмодзи в сообщении об ошибке, чтобы избежать UnicodeError
            try:
                self._logger.error(f"\n[ОШИБКА] Ошибка типов при выводе метрик: {e}\n", exc_info=True)
            except (UnicodeError, ValueError) as e2:
                # Если даже это не работает, выводим без форматирования
                self._logger.error(f"\n[ОШИБКА] Ошибка при выводе метрик: {e}\n", exc_info=True)
                self._logger.error(f"[ОШИБКА] Дополнительная ошибка: {e2}\n", exc_info=True)
        except (UnicodeError, ValueError) as e:
            # Ошибка форматирования/кодировки
            self._logger.error(f"\n[ОШИБКА] Ошибка форматирования при выводе метрик: {e}\n", exc_info=True)

    # ==========================
    # Сессии и анализ обучения
    # ==========================

    def _save_session_metrics(self, success: bool, final_score: int) -> None:
        """
        Сохраняет агрегированные метрики по завершённой игре в список сессий.
        """
        session_data = {
            "session_id": self.session_counter,
            "success": success,
            "final_score": final_score,
            "average_accuracy": self.performance_metrics["average_accuracy"],
            "learning_progress": self.performance_metrics["learning_progress"],
            "bricks_destroyed": self.current_game_stats["bricks_destroyed"],
            "total_moves": self.current_game_stats["total_moves"],
            "optimal_moves": self.current_game_stats["optimal_moves"],
        }

        self.session_metrics.append(session_data)
        self.session_counter += 1

        # Опционально: можно печатать прогресс каждые N игр
        if self.session_counter % 10 == 0:
            self._print_learning_progress_comparison()

    def _print_learning_progress_comparison(self) -> None:
        """
        Печатает краткий обзор прогресса обучения по последним сессиям.
        Никакой логики игры не меняет, только вывод/анализ.
        """
        if not self.session_metrics:
            return

        last_sessions = self.session_metrics[-10:]
        avg_score = sum(s["final_score"] for s in last_sessions) / len(last_sessions)
        avg_accuracy = sum(s["average_accuracy"] for s in last_sessions) / len(
            last_sessions
        )
        avg_learning = sum(s["learning_progress"] for s in last_sessions) / len(
            last_sessions
        )

        # Логируем статистику последних игр
        self._logger.info(
            f"[AI] Последние {len(last_sessions)} игр: "
            f"средний счёт={avg_score:.1f}, "
            f"точность={avg_accuracy:.2f}, "
            f"прогресс обучения={avg_learning:.2f}"
        )

    # Методы reset_learning, reset_for_testing, save_learning_data, load_learning_data
    # теперь в ai_player_reset.py
    # Методы visualize_debug_info, _draw_predicted_trajectory теперь в ai_player_debug_visualization.py
    # Методы _process_training_match, _learn_from_match_results, _get_average_efficiency,
    # get_optimal_ball_speed, get_optimal_paddle_speed_multiplier, get_adjusted_paddle_speed,
    # update_training_stats, _print_training_parameters, _print_console_summary теперь в ai_player_match_processing.py
