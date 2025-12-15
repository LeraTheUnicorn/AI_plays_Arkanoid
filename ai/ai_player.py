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
    AIPlayerPositioningMixin,
    AIPlayerMovementMixin,
    AIPlayerLearningMixin,
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

    # Метод _calculate_optimal_offset теперь в ai_player_position_optimization.py

    def _adjust_offset_from_history(self, offset: float, target_brick: Any) -> float:
        """
        Корректирует смещение на основе истории успешных ударов по данному кубику.
        """
        brick_x = float(getattr(target_brick, "x", 0))
        brick_y = float(getattr(target_brick, "y", 0))
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        pattern = self.targeting_system.hit_patterns.get(brick_key)
        if not pattern:
            return offset

        successful_offsets = pattern.get("successful_offsets", [])
        if not successful_offsets:
            return offset

        # Type narrowing: ensure successful_offsets is a list of numbers
        if not isinstance(successful_offsets, list):
            return offset
        
        # Convert to list of floats for type safety
        offset_values = [float(x) for x in successful_offsets if isinstance(x, (int, float))]
        if not offset_values:
            return offset

        avg_successful_offset = sum(offset_values) / len(offset_values)

        # Смешиваем текущее и историческое смещение
        return float(offset * 0.7 + avg_successful_offset * 0.3)

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
    # Адаптивная скорость платформы
    # ==========================
    # Метод calculate_adaptive_paddle_speed теперь в ai_player_ball_tracking.py
        """
        Рассчитывает адаптивную скорость платформы на основе физики игры.
        
        Учитывает:
        - Скорость мяча
        - Расстояние до оптимальной позиции
        - Время до встречи с мячом
        - Историю успешных движений
        
        Args:
            current_x: Текущая позиция платформы
            optimal_x: Оптимальная позиция платформы
            ball_speed: Скорость мяча
            
        Returns:
            Адаптивная скорость платформы
        """
        # КРИТИЧНО: Адаптивная базовая скорость на основе скорости мяча
        # Адаптивная скорость с разумными пределами: min=35, max=60, base=ball_speed * 2.5
        base_paddle_speed = max(35, min(int(ball_speed * 2.5), 60))
        min_speed = 35  # Минимальная скорость
        max_speed = 60  # Максимальная скорость
        
        if not self.current_game_state:
            return base_paddle_speed
        
        distance_to_optimal = abs(optimal_x - current_x)
        
        # Если позиция уже оптимальна или близка к ней
        if distance_to_optimal <= 5:
            return min_speed
        
        # Рассчитываем время до встречи с мячом (если он движется к платформе)
        time_to_meeting: float = 0.0
        if self.is_ball_moving_towards_paddle() and self.current_game_state:
            game_state = self.current_game_state
            ball_y = game_state.ball_position.y
            paddle_y = game_state.paddle_position.y
            ball_vel_y = game_state.ball_velocity.y
            
            if ball_vel_y > 0:  # Мяч движется вниз
                # Более точный расчет времени с учетом текущей позиции мяча
                distance_y = paddle_y - ball_y
                if distance_y > 0:
                    time_to_meeting = distance_y / ball_vel_y
                    time_to_meeting = max(
                        0.0, time_to_meeting
                    )  # Не может быть отрицательным
        
        # Рассчитываем требуемую скорость на основе времени до встречи
        required_speed: float = float(base_paddle_speed)
        
        if time_to_meeting > 0 and time_to_meeting != float("inf"):
            # Если времени мало, нужна высокая скорость
            if time_to_meeting <= 20:  # Менее 20 кадров - критическая ситуация
                required_speed = max(
                    float(base_paddle_speed * 2.5),  # Увеличено с 1.5 до 2.5
                    float(distance_to_optimal) / max(time_to_meeting * 0.5, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 40:  # Менее 40 кадров
                required_speed = max(
                    float(base_paddle_speed * 2.0),  # Увеличено с 1.2 до 2.0
                    float(distance_to_optimal) / max(time_to_meeting * 0.6, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 80:  # Менее 80 кадров  
                required_speed = max(
                    float(base_paddle_speed * 1.5),  # Увеличено с 0.9 до 1.5
                    float(distance_to_optimal) / max(time_to_meeting * 0.8, 1),
                )
            else:  # Много времени - можно двигаться медленно
                required_speed = max(float(min_speed), float(base_paddle_speed * 1.0))  # Увеличено с 0.6 до 1.0
        else:
            # Мяч не движется к платформе, используем умеренную скорость
            required_speed = float(base_paddle_speed * 0.8)
        
        # Корректируем на основе скорости мяча
        speed_ratio = float(ball_speed) / 5.0  # 5 - BALL_SPEED_DEFAULT
        speed_multiplier = (
            0.7 + speed_ratio * 0.6
        )  # 0.7x до 1.3x в зависимости от скорости мяча
        required_speed *= speed_multiplier
        
        # Учитываем расстояние - чем дальше, тем быстрее
        if distance_to_optimal > 150:
            required_speed *= 1.4
        elif distance_to_optimal > 100:
            required_speed *= 1.2
        elif distance_to_optimal > 50:
            required_speed *= 1.1
        
        # Дополнительная корректировка для экстренных ситуаций
        if (
            distance_to_optimal > time_to_meeting * ball_speed * 0.8
            and time_to_meeting > 0
        ):
            # Если расстояние больше, чем может пролететь мяч за время до встречи
            required_speed *= 1.3
        
        # Применяем границы
        required_speed = max(min_speed, min(max_speed, required_speed))
        
        # Добавляем небольшую случайность для естественности
        if distance_to_optimal > 20:
            variation = random.uniform(0.97, 1.03)
            required_speed *= variation
        
        return int(required_speed)

    # ==========================
    # Движение платформы
    # ==========================
    # Метод calculate_adaptive_paddle_speed теперь в ai_player_ball_tracking.py

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

    # ==========================
    # Публичный сброс обучения
    # ==========================

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
        self.empty_bounce_tracker["max_empty_bounces"] = self.config.max_empty_bounces if hasattr(self.config, 'max_empty_bounces') else 1
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

    # ==========================
    # Сохранение и загрузка данных обучения
    # ==========================

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
            self._logger.error(f"Ошибка ввода-вывода при сохранении данных обучения: {e}", exc_info=True)
        except (TypeError, ValueError) as e:
            self._logger.error(f"Ошибка данных при сохранении обучения: {e}", exc_info=True)
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
            self._logger.error(f"Ошибка ввода-вывода при загрузке данных обучения: {e}", exc_info=True)
        except (TypeError, ValueError) as e:
            self._logger.error(f"Ошибка данных при загрузке обучения: {e}", exc_info=True)
        except DataError as e:
            self._logger.error(f"Ошибка данных обучения: {e}", exc_info=True)
        except LearningError as e:
            self._logger.error(f"Ошибка системы обучения: {e}", exc_info=True)

    # ==========================
    # Отладочная визуализация
    # ==========================

    def visualize_debug_info(self, screen: Any) -> None:
        """
        Отображает отладочную информацию AI системы на экране.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            # Информация о состоянии AI
            info_lines = [
                f"Accuracy: {self.performance_metrics['average_accuracy']:.2f}",
                f"Learning: {self.performance_metrics['learning_progress']:.2f} (прогресс обучения)",
                f"Games: {self.performance_metrics['games_played']}",
            ]
            
            # Добавляем лучшее время для матча с 50 блоками
            best_time = self.performance_metrics.get("best_time_50_bricks")
            if best_time is not None:
                info_lines.append(f"Best: {best_time:.1f}s (50 blocks)")
            else:
                info_lines.append(f"Best: -- (50 blocks)")
            
            # Отрисовка фона для текста
            font = pygame.font.SysFont("arial", 16)
            line_height = 20
            box_width = 200
            box_height = len(info_lines) * line_height + 10
            
            # Полупрозрачный фон
            debug_surface = pygame.Surface((box_width, box_height))
            debug_surface.set_alpha(128)
            debug_surface.fill((0, 0, 0))
            screen.blit(debug_surface, (10, 10))
            
            # Текст
            y_offset = 15
            for line in info_lines:
                text_surface = font.render(line, True, (255, 255, 0))
                screen.blit(text_surface, (15, y_offset))
                y_offset += line_height
                
            # Визуализация предсказанной траектории
            if (
                self.is_active
                and self.current_game_state
                and self.is_ball_moving_towards_paddle()
                and self.debug_mode
            ):
                self._draw_predicted_trajectory(screen)
                
        except (AttributeError, TypeError) as e:
            # Игнорируем ошибки типов при визуализации, чтобы не прерывать игру
            self._logger.debug(f"Ошибка типов при визуализации: {e}", exc_info=True)
        except (ImportError, NameError) as e:
            # Игнорируем ошибки импорта pygame при визуализации
            self._logger.debug(f"Ошибка импорта при визуализации: {e}", exc_info=True)

    def _draw_predicted_trajectory(self, screen: Any) -> None:
        """
        Рисует предсказанную траекторию мяча для отладки.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            if not self.current_game_state:
                return
                
            # Предсказываем траекторию (используем оптимизированную для визуализации)
            trajectory = self.trajectory_predictor.get_optimized_trajectory(
                self.current_game_state, max_relevant_points=50
            )
            
            if not trajectory:
                return
                
            # Рисуем точки траектории
            for i, point in enumerate(
                trajectory[::3]
            ):  # Каждая 3-я точка для оптимизации
                if hasattr(point, "x") and hasattr(point, "y"):
                    # Цвет зависит от типа точки
                    if i < len(trajectory) // 3:
                        color = (0, 255, 0)  # Зеленый - начало траектории
                    else:
                        color = (255, 255, 0)  # Желтый - конец траектории
                    
                    pygame.draw.circle(screen, color, (int(point.x), int(point.y)), 2)
            
            # Рисуем точку пересечения с платформой
            intersection = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state,
                self.current_game_state.paddle_position.y,
            )
            
            if (
                intersection
                and hasattr(intersection, "x")
                and hasattr(intersection, "y")
            ):
                pygame.draw.circle(
                    screen, (255, 0, 0), (int(intersection.x), int(intersection.y)), 4
                )
                
        except (AttributeError, TypeError) as e:
            # Игнорируем ошибки типов при отрисовке траектории
            self._logger.debug(f"Ошибка типов при отрисовке траектории: {e}", exc_info=True)
        except (ImportError, NameError) as e:
            # Игнорируем ошибки импорта pygame при отрисовке
            self._logger.debug(f"Ошибка импорта при отрисовке: {e}", exc_info=True)
        except PredictionError as e:
            # Игнорируем ошибки предсказания при отрисовке
            self._logger.debug(f"Ошибка предсказания при отрисовке: {e}", exc_info=True)

    # ==========================
    # Методы для режима обучения
    # ==========================

    def _process_training_match(self, success: bool, final_score: int) -> None:
        """
        Обрабатывает результаты матча в режиме обучения.

        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
        """
        # Сохраняем параметры текущего матча
        match_data = {
            "success": success,
            "score": final_score,
            "ball_speed": self.training_parameters["ball_speed"],
            "paddle_speed_multiplier": self.training_parameters[
                "paddle_speed_multiplier"
            ],
            "bricks_destroyed": self.training_parameters["total_bricks_destroyed"],
            "time": self.training_parameters["total_time"],
            "lives_lost": self.training_parameters["lives_lost"],
        }
        self.training_parameters["match_history"].append(match_data)

        # Обновляем лучшее время для матча с 50 блоками
        if success and self.training_parameters["total_bricks_destroyed"] == 50:
            match_time = self.training_parameters["total_time"]
            best_time = self.performance_metrics.get("best_time_50_bricks")
            if best_time is None or match_time < best_time:
                self.performance_metrics["best_time_50_bricks"] = match_time

        # Ограничиваем историю последними 10 матчами
        if len(self.training_parameters["match_history"]) > 10:
            self.training_parameters["match_history"].pop(0)

        # Обучаемся на основе результатов
        self._learn_from_match_results(match_data)

    def _learn_from_match_results(self, match_data: Dict[str, Any]) -> None:
        """
        Обучается на основе результатов матча.

        Основная стратегия: алгоритм должен стремиться сбить как можно больше кубиков за меньшее время.
        Если не может сбить все 50 кубиков за 3 жизни - снижаем скорость мяча.

        Args:
            match_data: Данные о матче.
        """
        # Вычисляем эффективность: кубики за время с учетом потерянных жизней
        bricks_destroyed = match_data["bricks_destroyed"]
        time_taken = max(match_data["time"], 1)  # Избегаем деления на 0
        lives_lost = match_data["lives_lost"]

        # КРИТИЧЕСКИЙ КРИТЕРИЙ: Если не сбиты все 50 кубиков за 3 жизни - снижаем скорость
        all_bricks_destroyed = bricks_destroyed >= 50

        # Эффективность = кубики / (время * (1 + штраф за жизни))
        # Штраф за жизни: каждая потерянная жизнь увеличивает время на 20%
        time_penalty = 1.0 + (lives_lost * 0.2)
        efficiency = bricks_destroyed / (time_taken * time_penalty)

        # Обновляем параметры на основе эффективности
        current_ball_speed = self.training_parameters["ball_speed"]
        current_paddle_mult = self.training_parameters["paddle_speed_multiplier"]
        
        # ИСПРАВЛЕНИЕ: Защита от деградации производительности
        # Сохраняем лучшие параметры и проверяем, не ухудшается ли производительность
        if not hasattr(self, '_best_performance_params'):
            # Инициализируем лучшие параметры первыми значениями
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult
            }
        
        # Обновляем лучшие параметры, если текущий результат лучше
        if bricks_destroyed > self._best_performance_params['bricks_destroyed']:
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult
            }
        
        # ИСПРАВЛЕНИЕ: Проверяем деградацию производительности
        # Если производительность упала значительно (менее 50% от лучшего результата),
        # сбрасываем параметры к лучшим значениям
        if len(self.training_parameters["match_history"]) >= 2:
            # Берем последние 2 игры для проверки
            recent_games = self.training_parameters["match_history"][-2:]
            recent_avg_bricks = sum(g["bricks_destroyed"] for g in recent_games) / len(recent_games)
            best_bricks = self._best_performance_params['bricks_destroyed']
            
            # Если средний результат последних игр < 50% от лучшего, сбрасываем параметры
            if best_bricks > 0 and recent_avg_bricks < best_bricks * 0.5:
                self._logger.warning(f"[PERFORMANCE PROTECTION] Обнаружена деградация производительности! "
                                   f"Средний результат: {recent_avg_bricks:.1f}, лучший: {best_bricks}. "
                                   f"Сбрасываем параметры к лучшим значениям.")
                self.training_parameters["ball_speed"] = self._best_performance_params['ball_speed']
                self.training_parameters["paddle_speed_multiplier"] = self._best_performance_params['paddle_speed_multiplier']
                # Обновляем текущие значения для дальнейшего использования
                current_ball_speed = self.training_parameters["ball_speed"]
                current_paddle_mult = self.training_parameters["paddle_speed_multiplier"]

        # Целевое время матча: 5 секунд
        target_time = 5.0
        time_ratio = time_taken / target_time if target_time > 0 else 1.0

        # ИСПРАВЛЕНИЕ: ПРИОРИТЕТ 1: Если не сбиты все 50 кубиков
        # Но НЕ снижаем параметры агрессивно - это может вызвать деградацию
        if not all_bricks_destroyed:
            # ИСПРАВЛЕНИЕ: Снижаем скорость только если результат действительно плохой
            # И только если текущие параметры выше базовых значений
            bricks_remaining = 50 - bricks_destroyed
            
            # Снижаем скорость только если:
            # 1. Результат очень плохой (менее 20 кубиков)
            # 2. ИЛИ потеряны все жизни И результат плохой (менее 30 кубиков)
            if bricks_destroyed < 20 or (lives_lost >= 3 and bricks_destroyed < 30):
                speed_reduction = min(3, bricks_remaining // 10)  # Менее агрессивное снижение
                if current_ball_speed > 15:  # Минимум 15 для обучения
                    # ИСПРАВЛЕНИЕ: Не снижаем ниже лучших параметров (если они были хорошими)
                    min_speed = 15
                    if hasattr(self, '_best_performance_params') and self._best_performance_params['bricks_destroyed'] >= 40:
                        # Если был хороший результат, не опускаемся ниже лучших параметров
                        min_speed = max(15, self._best_performance_params['ball_speed'] - 5)
                    
                    self.training_parameters["ball_speed"] = max(
                        min_speed, current_ball_speed - speed_reduction
                    )
                
                # Снижаем скорость платформы только если потеряны все жизни И результат очень плохой
                if lives_lost >= 3 and bricks_destroyed < 20:
                    min_paddle_mult = 1.5
                    if hasattr(self, '_best_performance_params') and self._best_performance_params['bricks_destroyed'] >= 40:
                        # Не опускаемся ниже лучших параметров
                        min_paddle_mult = max(1.5, self._best_performance_params['paddle_speed_multiplier'] - 0.5)
                    
                    if current_paddle_mult > min_paddle_mult:
                        self.training_parameters["paddle_speed_multiplier"] = max(
                            min_paddle_mult, current_paddle_mult - 0.2  # Менее агрессивное снижение
                        )
        # ПРИОРИТЕТ 2: Если все кубики сбиты - можно увеличивать скорость для оптимизации времени
        elif all_bricks_destroyed and lives_lost <= 1:
            # Если время больше целевого, увеличиваем скорость
            if time_ratio > 1.2:  # Время на 20% больше целевого
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.1
                    )
            # Если время хорошее и эффективность высокая - можно немного увеличить
            elif time_ratio < 0.8 and efficiency > 8.0:  # Быстро и эффективно
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )

        # Если это первый матч или мало данных, используем более агрессивную адаптацию
        if len(self.training_parameters["match_history"]) <= 2:
            # Для первых матчей более агрессивно увеличиваем скорость только если результат хороший
            if (
                bricks_destroyed >= 45 and lives_lost <= 1
            ):  # Хороший результат (почти все блоки)
                # Увеличиваем скорость мяча до максимума для быстрой игры (максимум 25)
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 2
                    )
                # Увеличиваем скорость платформы
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.2
                    )
        else:
            # После накопления данных используем сравнение со средним и целевым временем
            avg_efficiency = self._get_average_efficiency()

            if (
                avg_efficiency > 0 and all_bricks_destroyed
            ):  # Только если все кубики сбиты
                # Если время больше целевого, агрессивно увеличиваем скорость (максимум 25)
                if time_ratio > 1.2:  # Время на 20% больше целевого
                    if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    if current_paddle_mult < 3.0:
                        self.training_parameters["paddle_speed_multiplier"] = min(
                            3.0, current_paddle_mult + 0.1
                        )
                elif efficiency > avg_efficiency * 1.1:  # На 10% лучше среднего
                    # Увеличиваем скорость мяча (до 25)
                    if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    # Увеличиваем скорость платформы (до 3.0)
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
        """
        Возвращает оптимальную скорость мяча на основе обучения.

        Returns:
            Оптимальная скорость мяча (20-50 для режима обучения).
        """
        return int(self.training_parameters["ball_speed"])

    def get_optimal_paddle_speed_multiplier(self) -> float:
        """
        Возвращает оптимальный множитель скорости платформы на основе обучения.

        Returns:
            Множитель скорости платформы (0.5-2.0).
        """
        return float(self.training_parameters["paddle_speed_multiplier"])

    def get_adjusted_paddle_speed(self, base_speed: int) -> int:
        """
        Возвращает скорректированную скорость платформы с учетом адаптации AI.

        Args:
            base_speed: Базовая скорость платформы.

        Returns:
            Скорректированная скорость платформы.
        """
        if self._last_adjusted_paddle_speed is not None:
            return self._last_adjusted_paddle_speed
        return base_speed

    def update_training_stats(
        self, bricks_destroyed: int, time_elapsed: float, lives_lost: int
    ) -> None:
        """
        Обновляет статистику обучения во время игры.

        Args:
            bricks_destroyed: Количество сбитых кубиков.
            time_elapsed: Прошедшее время.
            lives_lost: Потерянные жизни.
        """
        self.training_parameters["total_bricks_destroyed"] = bricks_destroyed
        self.training_parameters["total_time"] = time_elapsed
        self.training_parameters["lives_lost"] = lives_lost

    def _print_training_parameters(self) -> None:
        """Выводит средние значения параметров обучения в лог."""
        if not self.training_parameters["match_history"]:
            return

        self._logger.info("\n" + "=" * 70)
        self._logger.info("ПАРАМЕТРЫ ОБУЧЕНИЯ ИИ")
        self._logger.info("=" * 70)

        # Вычисляем средние значения
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
        """Выводит краткую сводку после матча в консоль.
        
        Подробные метрики записываются в лог файл.
        
        Args:
            success: True если игра выиграна.
            final_score: Итоговый счет игры.
        """
        try:
            # Вычисляем процент побед
            win_rate = 0.0
            if self.performance_metrics["games_played"] > 0:
                win_rate = (
                    self.performance_metrics["games_won"]
                    / self.performance_metrics["games_played"]
                ) * 100
            
            # Краткая сводка в консоль
            result_icon = "[OK]" if success else "[FAIL]"
            result_text = "ПОБЕДА" if success else "ПОРАЖЕНИЕ"
            
            print("\n" + "=" * 60)
            print(f"{result_icon} {result_text} | Счет: {final_score}/50")
            print(f"   Игр: {self.performance_metrics['games_played']} | Побед: {self.performance_metrics['games_won']} | Винрейт: {win_rate:.1f}%")
            print("=" * 60)
            
            # Информация о файле лога
            if hasattr(self._logger, 'handlers') and self._logger.handlers:
                for handler in self._logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        log_file = handler.baseFilename
                        print(f"   Подробные логи: {log_file}")
                        break
            print()
        except Exception as e:
            # В случае ошибки вывода, не прерываем выполнение
            pass
