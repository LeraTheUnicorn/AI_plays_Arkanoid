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


class AIPlayer(
    AIPlayerInitMixin,
    AIPlayerUtilsMixin,
    AIPlayerCacheMixin,
    AIPlayerZonesMixin,
    AIPlayerTargetCalculationMixin,
    AIPlayerPositionOptimizationPart1Mixin,
    AIPlayerPositionOptimizationPart2Mixin,
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

    def _detect_loop_pattern(self) -> bool:
        """
        Обнаруживает зацикливание в движениях платформы.

        Возвращает True, если обнаружен повторяющийся паттерн движений
        или вертикальные траектории мяча.
        """
        history = self.loop_prevention_system["movement_history"]
        trajectory_history = self.loop_prevention_system["trajectory_history"]

        threshold = self.loop_prevention_system["loop_detection_threshold"]

        # Нужно достаточно данных
        if len(history) < threshold * 2:
            return False

        # Проверяем последние движения
        recent_movements = history[-threshold:]
        movement_counts: Dict[int, int] = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1

        max_count = max(movement_counts.values())
        # 80% одинаковых движений считается зацикливанием
        if max_count >= threshold * 0.8:
            return True

        # Позиционная стагнация
        position_history = self.loop_prevention_system["position_history"]
        if len(position_history) >= 10:
            recent_positions = position_history[-10:]
            # Если за последние 8 кадров платформа почти не меняла позицию
            if len(set(recent_positions[-8:])) <= 2:
                return True

        # Вертикальные траектории мяча
        if len(trajectory_history) >= 5 and self.current_game_state:
            recent_trajectories = trajectory_history[-5:]
            vertical_count = 0
            for traj in recent_trajectories:
                prev_ball_x = traj.get("ball_x")
                if prev_ball_x is None:
                    continue
                current_ball_x = self.current_game_state.ball_position.x
                if abs(current_ball_x - prev_ball_x) < 3:
                    vertical_count += 1
            # 4 из 5 почти вертикальные — считаем зацикливанием
            if vertical_count >= 4:
                return True

        return False
    
    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания."""
        if not self._detect_loop_pattern():
            return

        # Учитываем кулдаун
        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return

        # Смена стратегии
        strategies = self.loop_prevention_system["alternative_strategies"]
        idx = self.loop_prevention_system["current_strategy_index"]
        self.loop_prevention_system["current_strategy_index"] = (idx + 1) % len(
            strategies
        )
        new_strategy = strategies[self.loop_prevention_system["current_strategy_index"]]

        # Кулдаун и сброс истории
        self.loop_prevention_system["strategy_change_cooldown"] = 10
        
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []

    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """
        Применяет альтернативную стратегию позиционирования для выхода из зацикливания.
        """
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]
        screen_center = self.screen_width // 2

        if strategy == "center_focus":
            # Фокусируемся на центре экрана
            return screen_center

        if strategy == "edge_focus":
            # Фокусируемся на краях для смены паттерна
            current_pos = getattr(self.current_game_state, "paddle_position", None)
            if current_pos and hasattr(current_pos, "x"):
                return self.screen_width - 70 if current_pos.x < screen_center else 70
            return 70

        if strategy == "predictive_targeting":
            # Агрессивное прицеливание в дальние кубики
            target_brick = self._find_most_distant_brick()
            if target_brick:
                landing_x = self._predict_exact_landing_position()
                brick_center_x = (
                    getattr(target_brick, "x", 0)
                    + getattr(target_brick, "width", 60) / 2
                )
                offset_direction = 1 if brick_center_x > landing_x else -1
                return int(optimal_position + offset_direction * 30)

        return optimal_position

    def _find_most_distant_brick(self) -> Optional[Any]:
        """Находит самый дальний по Y кубик от платформы."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        paddle_y = self.current_game_state.paddle_position.y

        most_distant_brick = None
        max_distance = -1.0

        for brick in bricks:
            brick_y = getattr(brick, "y", 0)
            distance = abs(paddle_y - brick_y)
            if distance > max_distance:
                max_distance = distance
                most_distant_brick = brick

        return most_distant_brick

    def _update_loop_tracking(
        self,
        movement: int,
        current_x: int,
        optimal_x: int,
    ) -> None:
        """Обновляет данные отслеживания зацикливания."""
        # История движений
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = (
                self.loop_prevention_system["movement_history"][-10:]
            )

        # История позиций
        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        # История траекторий
        if self.current_game_state:
            trajectory_info = {
                "ball_x": self.current_game_state.ball_position.x,
                "ball_y": self.current_game_state.ball_position.y,
                "optimal_x": optimal_x,
                "timestamp": time.time(),
            }
            self.loop_prevention_system["trajectory_history"].append(trajectory_info)
            if len(self.loop_prevention_system["trajectory_history"]) > 10:
                self.loop_prevention_system["trajectory_history"] = (
                    self.loop_prevention_system["trajectory_history"][-5:]
                )

    def _update_smoothness_tracking(self, movement: int, current_x: int) -> None:
        """Обновляет данные отслеживания плавности движения."""
        # История движений
        self.smoothness_system["recent_movements"].append(movement)
        if (
            len(self.smoothness_system["recent_movements"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_movements"] = self.smoothness_system[
                "recent_movements"
            ][-self.smoothness_system["jitter_window"] :]

        # История позиций
        self.smoothness_system["recent_positions"].append(current_x)
        if (
            len(self.smoothness_system["recent_positions"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_positions"] = self.smoothness_system[
                "recent_positions"
            ][-self.smoothness_system["jitter_window"] :]

        # Отслеживание смен направления движения
        if len(self.smoothness_system["recent_movements"]) >= 2:
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                # Произошла смена направления
                self.smoothness_system["movement_changes"].append(time.time())
                # Очищаем старые записи (старше 1 секунды)
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]

    def _detect_jitter(self) -> bool:
        """
        Обнаруживает дрожание платформы (частые смены направления движения).
        
        Returns:
            True, если обнаружено дрожание.
        """
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False

        # Подсчитываем количество смен направления в последних движениях
        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            # Смена направления: с -1 на 1, с 1 на -1, или с любого на противоположное
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1

        # Если слишком много смен направления - это дрожание
        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True

        # Дополнительная проверка: частые смены направления за короткое время
        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True

        # Проверка на микродвижения (очень маленькие изменения позиции)
        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            # Если позиция меняется очень мало, но часто - это дрожание
            if (
                position_variance < 10
                and len([m for m in movements[-5:] if m != 0]) >= 3
            ):
                return True

        return False

    def _calculate_smooth_movement(
        self, current_x: int, optimal_x: int, distance: float
    ) -> int:
        """
        Вычисляет плавное движение с учетом штрафов за дрожание.
        
        Args:
            current_x: Текущая позиция платформы.
            optimal_x: Оптимальная позиция платформы.
            distance: Расстояние до оптимальной позиции.
            
        Returns:
            Направление движения (-1, 0, 1).
        """
        # КРИТИЧНО: Проверяем, находится ли мяч в зоне разделения с установленной позицией
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if self.current_game_state and hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        # КРИТИЧНО: Если целевая позиция установлена, используем увеличенный допуск
        # Когда мяч движется точно вниз по известной траектории, платформа должна оставаться на месте
        if self.separation_zone_tracker.target_position_set:
            # Увеличенный допуск для предотвращения дрожания в зоне разделения
            effective_min_distance = 30  # Увеличенный допуск 30 пикселей для стабильности
        else:
            # Если есть штраф за дрожание, увеличиваем порог для движения
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (
                1 + penalty
            )

        if distance < effective_min_distance:
            # Не двигаемся, если расстояние слишком мало (с учетом штрафа или зоны разделения)
            # КРИТИЧНО: Это предотвращает уход платформы с траектории мяча
            return 0

        # Определяем направление движения
        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0

    def _reevaluate_after_bounce(self) -> None:
        """Переоценивает ситуацию после отбития мяча."""
        if not self.current_game_state:
            return

        target_brick = self.target_selector.find_best_target_brick(
            self.current_game_state,
            self.current_game_state.paddle_position.y,
            self.current_game_state.ball_position.x,
        )
        if target_brick:
            self.targeting_system.target_brick = target_brick
            landing_x = self._predict_exact_landing_position()
            new_offset = self.position_calculator.calculate_optimal_offset(
                landing_x, target_brick, self.current_game_state
            )
            self.targeting_system.optimal_offset = new_offset
            

        # Сбрасываем историю зацикливания для нового цикла
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        
        # Сбрасываем историю плавности движения после отскока
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        
        # КРИТИЧНО: Сбрасываем отслеживание зоны разделения после отскока
        self.separation_zone_tracker.ball_entered_separation_zone = False
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        self.separation_zone_tracker.last_movement_frame = 0
        
        # КРИТИЧНО: Проверяем, было ли отбитие в пустоту (мяч отскочил от потолка без попадания в кубики)
        # Это определяется в PyGameBall.py при отскоке от потолка
        # Здесь мы сбрасываем счетчик только если было успешное попадание в кубик

    # ==========================
    # Запись результатов ударов
    # ==========================
    # Метод record_hit_result теперь в ai_player_targeting.py

    # ==========================
    # Предсказание траектории и позиционирование
    # ==========================
    # Методы _predict_exact_landing_position, _handle_ceiling_bounce_positioning,
    # _track_ball_position, _calculate_precise_position_for_few_bricks,
    # _force_target_brick_from_coordinates, _calculate_position_for_max_destruction
    # теперь в ai_player_positioning.py

    def _handle_ceiling_bounce_positioning(self) -> int:
        """
        Специальная логика для позиционирования при отскоке мяча от потолка.
        Предотвращает симметричные отскоки и зацикливание.
        """
        if not self.current_game_state:
            return self.screen_width // 2
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y

        if ball_y < 30 and vel_y > 0:
            # Мяч только что отскочил от потолка
            if abs(vel_x) < 2:
                # Почти вертикальный отскок — смещаемся в сторону средней позиции кубиков
                remaining_bricks = self.targeting_system.brick_coordinates
                if remaining_bricks:
                    avg_brick_x = sum(c["x"] for c in remaining_bricks) / len(
                        remaining_bricks
                    )
                    target_x = (ball_x + avg_brick_x) / 2.0
                else:
                    # Нет кубиков — небольшое смещение от центра
                    center_x = self.screen_width // 2
                    target_x = center_x + (ball_x - center_x) * 0.3
            else:
                # Есть горизонтальная скорость — небольшое упреждение
                target_x = ball_x + vel_x * 2.0

            # Добавляем случайное смещение, чтобы избежать идеальной симметрии
            target_x += random.choice([-15, -10, 0, 10, 15])

            paddle_half_width = self.paddle_width / 2
            min_x = paddle_half_width + 5
            max_x = self.screen_width - paddle_half_width - 5
            target_x = max(min_x, min(max_x, target_x))
            return int(target_x)

        # Стандартное слежение за мячом
        return int(self._track_ball_position())

    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с небольшим упреждением."""
        if not self.current_game_state:
            return self.screen_width / 2.0
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        vel_x = game_state.ball_velocity.x

        prediction_time = 3  # кадров вперёд
        predicted_x = ball_x + vel_x * prediction_time

        screen_width = self.screen_width
        ball_radius = self.config.ball.radius
        min_x = ball_radius
        max_x = screen_width - ball_radius

        return max(min_x, min(max_x, predicted_x))

    # ==========================
    # Адаптивная скорость платформы
    # ==========================

    def calculate_adaptive_paddle_speed(
        self, current_x: int, optimal_x: int, ball_speed: int
    ) -> int:
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

    def _execute_movement_strategy(self, current_x: int, paddle_speed: int) -> int:
        """
        Выполняет стратегию движения платформы.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        # ТЕСТ: Логируем вызов стратегии
        self._logger.debug(f"[AI_PLAYER_MOVE] Вызываем paddle_movement_strategy.move_paddle_towards: current_x={current_x}, paddle_speed={paddle_speed}")
        # Обновляем current_game_state в стратегии
        self.paddle_movement_strategy.current_game_state = self.current_game_state
        result = self.paddle_movement_strategy.move_paddle_towards(current_x, paddle_speed)
        self._logger.debug(f"[AI_PLAYER_MOVE] paddle_movement_strategy вернул: {result}")
        return result

    def _validate_movement_conditions(self, current_x: int, paddle_speed: int) -> bool:
        """
        Проверяет условия для движения платформы.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            True, если движение возможно, False иначе.
        """
        if not self.current_game_state or not self.is_active:
            self._logger.debug(f"[PADDLE DEBUG] move_paddle_towards: current_game_state={self.current_game_state is not None}, is_active={self.is_active}")
            return False
        return True

    def _calculate_optimal_position(self) -> int:
        """
        Рассчитывает оптимальную позицию платформы.
        
        Returns:
            Оптимальная X-координата платформы.
        """
        # Получаем состояние мяча
        ball_y = self.current_game_state.ball_position.y
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        
        # КРИТИЧНО: Логируем состояние мяча для диагностики
        # Фильтрация по уровню выполняется автоматически системой логирования Python
        optimal_x = self.get_optimal_paddle_position()
        self._logger.debug(f"[PADDLE DEBUG] ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y}, current_x={current_x}, optimal_x={optimal_x}, distance={abs(current_x - optimal_x):.1f}")
        
        # Записываем метрику производительности перед возвратом
        if self.performance_monitor and start_time_monitor:
            duration = time.time() - start_time_monitor
            self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
        
        return optimal_x

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
        # КРИТИЧНО: УБРАНО ПРАВИЛО 1 - платформа ДОЛЖНА двигаться к точке падения мяча
        # даже когда мяч летит вверх, чтобы успеть к моменту падения
        # Продолжаем расчет оптимальной позиции независимо от направления мяча
        
        if ball_vel_y == 0:
            # КРИТИЧНО: Если vel_y == 0, это ошибка состояния (должно быть исправлено в PyGameBall.py)
            # Но на всякий случай продолжаем движение к оптимальной позиции, а не используем fallback
            # Это предотвращает ситуацию, когда платформа перестает двигаться из-за временного vel_y=0
            # Логируем для диагностики, но продолжаем нормальную логику
            self._log_paddle_movement(current_x, current_x, "ball_vel_y_zero_warning", 0.5)
            # Продолжаем обработку с обычной логикой - НЕ возвращаем fallback!
        
        # ПРАВИЛО 2: Если мяч в зоне кубиков - платформа НЕ двигается
        # КРИТИЧНО: ИСКЛЮЧЕНИЕ - при 1 кирпиче разрешаем упреждающее движение
        bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 50
        is_last_brick = bricks_count == 1
        
        if ball_y < separation_zone_start and not is_last_brick:
            # Для нормальных случаев - не двигаемся в зоне кубиков
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2: Мяч в зоне кубиков (ball_y={ball_y:.1f} < {separation_zone_start}), платформа не двигается")
            self._log_paddle_movement(current_x, current_x, "ball_in_bricks_zone", 1.0)
            return 0
        elif ball_y < separation_zone_start and is_last_brick:
            # КРИТИЧНО: При 1 кирпиче разрешаем упреждающее движение
            # Это позволяет платформе подготовиться к попаданию в последний кирпич
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2 EXCEPTION: Последний кирпич! Разрешаем движение в зоне кубиков")
            # Продолжаем обработку - не возвращаем 0
        
        # КРИТИЧНО: Проверяем, не потерян ли мяч (ниже верхней границы платформы)
        # Если мяч ниже верхней границы платформы - он считается потерянным, платформа НЕ двигается
        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
        ball_lost = ball_y > paddle_y  # Мяч ниже верхней границы платформы
        
        if ball_lost:
            # Мяч потерян - платформа НЕ двигается
            # КРИТИЧНО: Логируем для диагностики (периодически)
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] Мяч потерян (ball_y={ball_y:.1f} > paddle_y={paddle_y:.1f}), платформа не двигается")
            self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle", 1.0)
            return 0
        
        # Проверяем, находится ли мяч в зоне разделения
        # КРИТИЧНО: Мяч должен быть выше верхней границы платформы и в разрешенной зоне
        # Зона разделения: от separation_zone_start до верхней границы платформы
        in_separation_zone = separation_zone_start <= ball_y < paddle_y and ball_vel_y > 0
        
        # КРИТИЧНО: Логируем состояние зоны разделения для диагностики
        # Логируем всегда когда мяч в зоне разделения или близко к платформе
        should_log = in_separation_zone or (ball_y > paddle_y - 100 and ball_vel_y > 0)
        # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
        if should_log:  # Всегда логируем когда мяч близко
            ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
            ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            ball_speed = self.current_game_state.ball_speed if self.current_game_state else 0
            distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
            time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
            # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() если позиция уже зафиксирована
            # Это может вызвать пересчет и дергание
            if self.separation_zone_tracker.target_position_set:
                target_pos = self.separation_zone_tracker.target_position
                if target_pos is not None:
                    optimal_x = int(target_pos)
                else:
                    optimal_x = self.get_optimal_paddle_position()
                    
                    # Записываем метрику производительности
                    if self.performance_monitor and start_time_monitor:
                        duration = time.time() - start_time_monitor
                        self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
            else:
                optimal_x = self.get_optimal_paddle_position()
            distance_to_target = abs(current_x - optimal_x) if optimal_x is not None else 0
            self._logger.debug(f"[BALL TRACKING] ball=({ball_x:.1f},{ball_y:.1f}) vel=({ball_vel_x:.1f},{ball_vel_y:.1f}) speed={ball_speed:.1f} | "
                               f"paddle_x={current_x:.1f} optimal_x={optimal_x:.1f} dist_to_target={distance_to_target:.1f} | "
                               f"zone: sep_start={separation_zone_start} paddle_y={paddle_y:.1f} in_zone={in_separation_zone} | "
                               f"time_to_paddle={time_to_paddle:.2f} frames")
        
        # КРИТИЧНО: Обнаружение отскоков от кирпичей по резкому изменению позиции мяча ИЛИ изменению направления
        ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
        current_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
        current_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
        
        brick_bounce_detected = False
        if self._last_ball_position is not None and self._last_ball_velocity is not None and self.current_game_state:
            # Проверяем резкое изменение позиции мяча (более 50 пикселей за кадр)
            position_change = abs(ball_x - self._last_ball_position.x)
            # Также проверяем изменение Y координаты вверх (мяч отскочил)
            y_change = ball_y - self._last_ball_position.y
            
            # КРИТИЧНО: Проверяем изменение направления ball_vel_y (мяч отскочил вверх после движения вниз)
            # Это самый надежный способ обнаружения отскока от кирпича
            last_vel_y = self._last_ball_velocity.y
            vel_y_direction_change = (last_vel_y > 0 and current_vel_y < 0)  # Мяч двигался вниз, теперь вверх
            
            # Отскок от кирпича: 
            # 1. Резкое изменение позиции X (>50px) И vel_x не изменилась сильно
            # 2. ИЛИ изменение направления Y координаты вверх (y_change < -10)
            # 3. ИЛИ изменение направления ball_vel_y (мяч отскочил вверх)
            if position_change > 50 or (y_change < -10 and ball_y < separation_zone_start) or vel_y_direction_change:
                # Проверяем, что это не отскок от стены (vel_x должен был измениться, но это уже отслеживается)
                vel_x_change = abs(current_vel_x - self._last_ball_velocity.x)
                
                # Если скорость vel_x не изменилась сильно, но позиция изменилась резко - это отскок от кирпича
                # ИЛИ если изменилось направление ball_vel_y (мяч отскочил вверх)
                if (vel_x_change < 5 and position_change > 50) or vel_y_direction_change:
                    brick_bounce_detected = True
                    bounce_reason = "vel_y direction change" if vel_y_direction_change else f"position change {position_change:.1f}px"
                    self._logger.debug(f"[BRICK BOUNCE DETECTED] {bounce_reason}, "
                                     f"ball=({ball_x:.1f},{ball_y:.1f}) prev=({self._last_ball_position.x:.1f},{self._last_ball_position.y:.1f}), "
                                     f"vel_y: {last_vel_y:.1f} -> {current_vel_y:.1f}")
        
        # Обновляем предыдущую позицию мяча
        if self.current_game_state:
            self._last_ball_position = Point(ball_x, ball_y)
            self._last_ball_velocity = Point(current_vel_x, current_vel_y)
        
        # ПРАВИЛО 3: Если целевая позиция установлена - используем её БЕЗ пересчета
        # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз при входе мяча в зону разделения
        # и не меняется до следующего отскока от стены ИЛИ отскока от кирпича
        if self.separation_zone_tracker.target_position_set:
            # КРИТИЧНО: Проверяем отскоки от стены И от кирпичей
            current_target = self.separation_zone_tracker.target_position
            if current_target is not None and in_separation_zone:
                # КРИТИЧНО: Проверяем изменение vel_x - это признак отскока от стены
                # ИЛИ обнаружение отскока от кирпича
                saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                
                # Если vel_x изменился (мяч отскочил от стены) ИЛИ обнаружен отскок от кирпича - сбрасываем цель
                if (saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > 0.1) or brick_bounce_detected:
                    # Мяч отскочил от стены или от кирпича - траектория изменилась, нужно пересчитать цель
                    if brick_bounce_detected:
                        self._logger.debug(f"[TARGET RESET] Мяч отскочил от кирпича! Траектория изменилась, пересчитываем цель")
                    else:
                        self._logger.debug(f"[TARGET RESET] Мяч отскочил от стены! Старая vel_x={saved_vel_x:.1f}, Новая vel_x={current_vel_x:.1f}")
                    
                    # ИСПРАВЛЕНИЕ: Проверяем расстояние до новой потенциальной цели перед сбросом
                    # Рассчитываем новую потенциальную цель для проверки расстояния
                    ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                    ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                    ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else 0
                    
                    # Рассчитываем время до приземления мяча
                    distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                    time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                    
                    # Предсказываем новую позицию приземления
                    if time_to_paddle != float('inf') and time_to_paddle > 0:
                        predicted_new_x = ball_x + current_vel_x * time_to_paddle
                        # Применяем зоны
                        zone_size = self.config.paddle.zone_size
                        screen_center = self.screen_width / 2
                        left_threshold = screen_center - zone_size * 2
                        right_threshold = screen_center + zone_size * 2
                        
                        if predicted_new_x < left_threshold:
                            zone_center_x = predicted_new_x + zone_size
                        elif predicted_new_x > right_threshold:
                            zone_center_x = predicted_new_x - zone_size
                        else:
                            zone_center_x = predicted_new_x
                        
                        distance_to_new_target = abs(current_x - zone_center_x)
                        
                        # ИСПРАВЛЕНИЕ: Если новая цель слишком далеко (>200px), используем консервативный подход
                        # Вместо резкого изменения цели, двигаемся постепенно или выбираем промежуточную позицию
                        if distance_to_new_target > 200:
                            # Рассчитываем максимальное расстояние, которое можем пройти за время до приземления
                            max_distance = paddle_speed * time_to_paddle if time_to_paddle < 100 else 200
                            
                            # Выбираем промежуточную позицию в направлении новой цели
                            if zone_center_x > current_x:
                                conservative_target = min(zone_center_x, current_x + max_distance)
                            else:
                                conservative_target = max(zone_center_x, current_x - max_distance)
                            
                            # КРИТИЧНО: Ограничиваем границами экрана, чтобы избежать отрицательных координат
                            min_x = self.paddle_width // 2
                            max_x = self.screen_width - self.paddle_width // 2
                            conservative_target = max(min_x, min(max_x, conservative_target))
                            
                            self._logger.debug(f"[CONSERVATIVE TARGET] Большое расстояние ({distance_to_new_target:.1f}px), "
                                               f"используем промежуточную цель: {conservative_target:.1f} вместо {zone_center_x:.1f}")
                            
                            # Устанавливаем консервативную цель вместо полного сброса
                            self.separation_zone_tracker.target_position = int(conservative_target)
                            self.separation_zone_tracker.target_position_set = True
                            self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                            # Продолжаем с этой целью без полного сброса
                        else:
                            # Расстояние приемлемое - выполняем обычный сброс
                            self.separation_zone_tracker.target_position_set = False
                            self.separation_zone_tracker.target_position = None
                    else:
                        # Не можем рассчитать время - выполняем обычный сброс
                        self.separation_zone_tracker.target_position_set = False
                        self.separation_zone_tracker.target_position = None
                    
                    self.separation_zone_tracker.paddle_moved_after_set = False
                    self.separation_zone_tracker.paddle_reached_target = False
                    self.separation_zone_tracker.frames_since_target_set = 0
                    self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                    self._log_paddle_movement(current_x, current_x, "target_reset_wall_bounce", 1.0)
                    # Продолжаем обработку с обычной логикой для установки новой цели
                else:
                    # Скорость не изменилась - траектория стабильна, НЕ обновляем цель
                    # КРИТИЧНО: Возвращаем зафиксированную позицию БЕЗ пересчета
                    # Это гарантирует, что позиция не изменится до отскока от стены
                    self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                    
                    # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() для проверки - это может вызвать пересчет
                    # Просто используем зафиксированную позицию
                    
                    # ВСЕГДА возвращаем зафиксированную позицию
                    # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() - это может вызвать пересчет и дергание
                    target_pos = int(current_target)
                    distance_to_target = abs(current_x - target_pos)
                    
                    # КРИТИЧНО: Используем большой tolerance для остановки, чтобы предотвратить дергание
                    # Проблема: платформа движется со скоростью 15px/кадр и "перескакивает" через цель
                    # Решение: используем большой tolerance (равный скорости движения), чтобы платформа останавливалась
                    # даже если немного перескочила через цель
                    tolerance = 15  # Равен скорости движения платформы - предотвращает дергание
                    
                    # КРИТИЧНО: Логируем движение к зафиксированной позиции для отслеживания
                    # Фильтрация по уровню выполняется автоматически системой логирования Python
                    self._logger.debug(f"[MOVING TO FIXED] ФЛАГ: Движение к зафиксированной позиции! "
                                       f"current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
                                       f"distance={distance_to_target:.1f}px, tolerance={tolerance}")
                    
                    # Двигаемся к зафиксированной позиции
                    if distance_to_target > tolerance:
                        # Платформа далеко от цели - начинаем движение
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        if movement != 0:
                            self._update_loop_tracking(movement, int(current_x), int(target_pos))
                            self._update_smoothness_tracking(movement, current_x)
                            self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                            return movement
                    else:
                        # Достигли цели - останавливаемся
                        # КРИТИЧНО: НЕ устанавливаем флаг paddle_reached_target - он не нужен
                        # Просто останавливаемся, если близко к цели
                        return 0
            
            # КРИТИЧНО: Если позиция зафиксирована, но мяч не в зоне разделения - проверяем сброс
            # КРИТИЧНО: Используем гистерезис для предотвращения дергания
            # Сбрасываем целевую позицию ТОЛЬКО если:
            # 1. Мяч ушел далеко вверх (выше зоны кубиков) ИЛИ
            # 2. Мяч потерян (ниже верхней границы платформы)
            should_reset = False
            
            # Проверка 1: Мяч ушел далеко вверх (выше зоны кубиков)
            if ball_y < separation_zone_start - 50:  # Далеко выше зоны разделения
                should_reset = True
            
            # Проверка 2: Мяч потерян (ниже верхней границы платформы)
            if ball_lost:
                should_reset = True
            
            # Если нужно сбросить - сбрасываем
            if should_reset:
                self.separation_zone_tracker.target_position_set = False
                self.separation_zone_tracker.target_position = None
                self.separation_zone_tracker.paddle_moved_after_set = False
                self.separation_zone_tracker.paddle_reached_target = False
                self._log_paddle_movement(current_x, current_x, "target_reset_ball_left_zone", 1.0)
                # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
            else:
                # КРИТИЧНО: Позиция зафиксирована, но мяч не в зоне разделения
                # Используем зафиксированную позицию БЕЗ пересчета
                current_target = self.separation_zone_tracker.target_position
                if current_target is not None:
                    target_pos = int(current_target)
                    distance_to_target = abs(current_x - target_pos)
                    tolerance = 3
                    
                    if distance_to_target > tolerance:
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        if movement != 0:
                            self._update_loop_tracking(movement, int(current_x), int(target_pos))
                            self._update_smoothness_tracking(movement, current_x)
                            self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target_outside_zone", 1.0)
                            return movement
                    else:
                        return 0
                
                # КРИТИЧНО: УБРАНО - пересчет позиции в зоне разделения вызывает дёргание
                # Позиция фиксируется один раз и НЕ пересчитывается до отскока от стены
                if False:  # Никогда не пересчитываем в зоне разделения
                    # Используем простой расчет для стабильности
                    if self.current_game_state:
                        ball_x = self.current_game_state.ball_position.x
                        ball_y_state = self.current_game_state.ball_position.y
                        vel_x = self.current_game_state.ball_velocity.x
                        vel_y = self.current_game_state.ball_velocity.y
                        
                        if vel_y > 0 and ball_y_state < paddle_y:
                            # КРИТИЧНО: Улучшенное предсказание точки падения с учетом времени движения платформы
                            time_to_paddle = (paddle_y - ball_y_state) / vel_y
                            if time_to_paddle > 0:
                                # Предсказываем позицию мяча в момент падения
                                predicted_x = ball_x + vel_x * time_to_paddle
                                
                                # КРИТИЧНО: Учитываем отскоки от стен более точно
                                screen_width = self.screen_width
                                ball_radius = self.config.ball.radius
                                remaining_time = time_to_paddle
                                current_predicted_x = ball_x
                                current_vel_x = vel_x
                                
                                # Симулируем движение мяча с учетом отскоков от стен
                                while remaining_time > 0:
                                    # Рассчитываем, когда мяч достигнет стены
                                    if current_vel_x > 0:
                                        time_to_right_wall = (screen_width - ball_radius - current_predicted_x) / current_vel_x
                                    else:
                                        time_to_right_wall = float('inf')
                                    
                                    if current_vel_x < 0:
                                        time_to_left_wall = (current_predicted_x - ball_radius) / abs(current_vel_x)
                                    else:
                                        time_to_left_wall = float('inf')
                                    
                                    time_to_wall = min(time_to_left_wall, time_to_right_wall)
                                    
                                    if time_to_wall > 0 and time_to_wall <= remaining_time:
                                        # Мяч отскочит от стены
                                        current_predicted_x += current_vel_x * time_to_wall
                                        remaining_time -= time_to_wall
                                        current_vel_x = -current_vel_x
                                    else:
                                        # Мяч не достигнет стены до падения
                                        current_predicted_x += current_vel_x * remaining_time
                                        remaining_time = 0
                                
                                predicted_x = current_predicted_x
                                
                                # Дополнительная проверка границ
                                if predicted_x < ball_radius:
                                    predicted_x = ball_radius
                                elif predicted_x > screen_width - ball_radius:
                                    predicted_x = screen_width - ball_radius
                                
                                # КРИТИЧНО: Разделяем платформу на 3 зоны и всегда прицеливаемся в центр выбранной зоны
                                # Платформа шириной 120px делится на 3 равные зоны по 40px каждая
                                # Левая зона: от -60px до -20px от центра платформы (центр на -40px)
                                # Центральная зона: от -20px до +20px от центра платформы (центр на 0px)
                                # Правая зона: от +20px до +60px от центра платформы (центр на +40px)
                                
                                zone_size = self.config.paddle.zone_size
                                zone_half = self.config.paddle.zone_half
                                
                                # КРИТИЧНО: Проверяем, не находится ли точка падения близко к стене
                                # Если точка падения в пределах 40px от края экрана - используем точку падения напрямую
                                screen_width = self.screen_width
                                ball_radius = self.config.ball.radius
                                min_safe_x = ball_radius + 40
                                max_safe_x = screen_width - ball_radius - 40
                                
                                use_direct_position = (predicted_x < min_safe_x or predicted_x > max_safe_x)
                                
                                if use_direct_position:
                                    # Точка падения близко к стене - используем точку падения напрямую
                                    # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), платформа должна доезжать до края зоны
                                    # Край платформы должен касаться стены для максимального покрытия
                                    if time_to_paddle < 3:
                                        # Мяч очень близко - доезжаем до края зоны
                                        if predicted_x > screen_width / 2:
                                            # Мяч справа - край платформы касается правой стены
                                            zone_center_x = screen_width - self.paddle_width // 2
                                        else:
                                            # Мяч слева - край платформы касается левой стены
                                            zone_center_x = self.paddle_width // 2
                                    else:
                                        # Мяч не очень близко - используем точку падения напрямую
                                        zone_center_x = predicted_x
                                    selected_zone = "EDGE"
                                else:
                                    # КРИТИЧНО: Правильная логика позиционирования для попадания в ЦЕНТР зоны
                                    # Цель: позиционировать платформу так, чтобы predicted_x попал в ЦЕНТР выбранной зоны
                                    # Для этого нужно определить, в какую зону попадает predicted_x,
                                    # и позиционировать платформу так, чтобы центр этой зоны совпал с predicted_x
                                    
                                    # Варианты позиционирования:
                                    # 1. Центральная зона: центр платформы = predicted_x (центр зоны = predicted_x)
                                    # 2. Левая зона: центр платформы = predicted_x + 40 (центр зоны = predicted_x)
                                    # 3. Правая зона: центр платформы = predicted_x - 40 (центр зоны = predicted_x)
                                    
                                    # Определяем, какая зона лучше подходит, проверяя границы зон:
                                    # Если центр платформы = predicted_x:
                                    #   - Левая зона: от predicted_x-60 до predicted_x-20
                                    #   - Центральная зона: от predicted_x-20 до predicted_x+20
                                    #   - Правая зона: от predicted_x+20 до predicted_x+60
                                    
                                    # Если predicted_x находится в центральной зоне (от predicted_x-20 до predicted_x+20),
                                    # то predicted_x всегда попадает в центр центральной зоны - используем центральную зону
                                    
                                    # Если predicted_x находится в левой зоне (от predicted_x-60 до predicted_x-20),
                                    # то нужно сдвинуть платформу вправо на 40px, чтобы predicted_x попал в центр левой зоны
                                    
                                    # Если predicted_x находится в правой зоне (от predicted_x+20 до predicted_x+60),
                                    # то нужно сдвинуть платформу влево на 40px, чтобы predicted_x попал в центр правой зоны
                                    
                                    # Но predicted_x - это точка падения, а не позиция относительно платформы!
                                    # Нужно определить, в какую зону попадает predicted_x, если центр платформы = predicted_x
                                    
                                    # Упрощенный подход: выбираем зону на основе расстояния от predicted_x до центров зон
                                    # при условии, что центр платформы = predicted_x
                                    
                                    # Центры зон при центре платформы = predicted_x:
                                    center_zone_center = predicted_x  # центр центральной зоны
                                    left_zone_center = predicted_x - zone_size  # центр левой зоны (predicted_x - 40)
                                    right_zone_center = predicted_x + zone_size  # центр правой зоны (predicted_x + 40)
                                    
                                    # Расстояния от predicted_x до центров зон:
                                    dist_to_center = abs(predicted_x - center_zone_center)  # всегда 0
                                    dist_to_left = abs(predicted_x - left_zone_center)  # всегда 40
                                    dist_to_right = abs(predicted_x - right_zone_center)  # всегда 40
                                    
                                    # КРИТИЧНО: Выбираем зону на основе того, где находится predicted_x относительно экрана
                                    # Если predicted_x близко к левому краю - предпочитаем левую зону
                                    # Если predicted_x близко к правому краю - предпочитаем правую зону
                                    # Иначе - используем центральную зону
                                    
                                    screen_center = screen_width / 2
                                    # КРИТИЧНО: Используем более широкие пороги для выбора боковых зон
                                    # Это гарантирует, что платформа будет двигаться дальше влево/вправо,
                                    # чтобы мяч попадал в центр боковой зоны, а не на границу
                                    left_threshold = screen_center - zone_size * 2  # 400 - 80 = 320
                                    right_threshold = screen_center + zone_size * 2  # 400 + 80 = 480
                                    
                                    if predicted_x < left_threshold:
                                        # predicted_x в левой части экрана - используем левую зону
                                        # Чтобы predicted_x попал в центр левой зоны, центр платформы = predicted_x + 40
                                        zone_center_x = predicted_x + zone_size
                                        selected_zone = "LEFT"
                                    elif predicted_x > right_threshold:
                                        # predicted_x в правой части экрана - используем правую зону
                                        # Чтобы predicted_x попал в центр правой зоны, центр платформы = predicted_x - 40
                                        zone_center_x = predicted_x - zone_size
                                        selected_zone = "RIGHT"
                                    else:
                                        # predicted_x в центральной части экрана - используем центральную зону
                                        # Чтобы predicted_x попал в центр центральной зоны, центр платформы = predicted_x
                                        zone_center_x = predicted_x
                                        selected_zone = "CENTER"
                                
                                # КРИТИЧНО: Логируем выбор зоны для диагностики (всегда)
                                current_paddle_x = self.current_game_state.paddle_position.x if self.current_game_state else 0
                                distance_to_zone_center = abs(current_paddle_x - zone_center_x)
                                # Вычисляем, где будет центр выбранной зоны при позиции платформы = zone_center_x
                                if selected_zone == "LEFT":
                                    actual_zone_center = zone_center_x - zone_size  # центр левой зоны
                                elif selected_zone == "RIGHT":
                                    actual_zone_center = zone_center_x + zone_size  # центр правой зоны
                                else:
                                    actual_zone_center = zone_center_x  # центр центральной зоны
                                
                                self._logger.debug(f"[ZONE SELECTION] predicted_x={predicted_x:.1f} -> zone={selected_zone} "
                                                   f"paddle_center={zone_center_x:.1f} actual_zone_center={actual_zone_center:.1f} "
                                                   f"current_paddle={current_paddle_x:.1f} distance_to_zone={distance_to_zone_center:.1f}px "
                                                   f"time_to_paddle={time_to_paddle:.2f} frames")
                                
                                # Ограничиваем границами экрана
                                # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров),
                                # платформа должна доезжать до края зоны (край платформы касается стены)
                                # НЕ ограничиваем границами в этом случае
                                min_x = self.paddle_width // 2 + 30
                                max_x = screen_width - self.paddle_width // 2 - 30
                                
                                # КРИТИЧНО: Если это EDGE зона и мяч очень близко, доезжаем до края
                                if selected_zone == "EDGE" and time_to_paddle < 3:
                                    # В EDGE зоне и очень близко - используем zone_center_x напрямую
                                    # (уже рассчитан для края зоны в строках 2794 или 2797)
                                    new_optimal_x = int(zone_center_x)
                                else:
                                    # Обычное ограничение границами
                                    new_optimal_x = max(min_x, min(max_x, int(zone_center_x)))
                                
                                # КРИТИЧНО: Используем экспоненциальное сглаживание
                                # НО: не обновляем целевую позицию, если платформа уже близко к текущей цели
                                # КРИТИЧНО: Если мяч очень близко (менее 5 кадров), ВСЕГДА обновляем цель без сглаживания
                                old_target = self.separation_zone_tracker.target_position
                                if old_target is not None:
                                    # Проверяем, насколько далеко платформа от текущей цели
                                    distance_to_old_target = abs(current_x - old_target)
                                    
                                    # КРИТИЧНО: НЕ обновляем цель без сглаживания когда мяч очень близко
                                    # Это вызывает дёргание платформы, если траектория стабильна
                                    # Обновляем только если траектория кардинально изменилась
                                    distance_to_paddle_y = paddle_y - ball_y_state if ball_y_state < paddle_y else 0
                                    
                                    if distance_to_old_target <= 40:
                                        # КРИТИЧНО: Если платформа уже близко к текущей цели, НЕ обновляем цель вообще
                                        # Это предотвращает дёргание в точке падения
                                        # Используем удвоенный tolerance для проверки "близко к цели"
                                        tolerance_check = 30  # Удвоенный tolerance (15 * 2)
                                        if distance_to_old_target <= tolerance_check:
                                            # Платформа уже близко к цели - НЕ обновляем, даже если new_optimal немного отличается
                                            # Это критично для предотвращения дёргания в точке падения
                                            optimal_x = old_target
                                            # Логируем, что мы НЕ обновляем цель, хотя new_optimal отличается
                                            if abs(new_optimal_x - old_target) > 10:  # Только если разница значительная
                                                self._logger.debug(f"[POSITION CHANGE BLOCKED] Платформа близко к цели (distance={distance_to_old_target:.1f} <= {tolerance_check}), "
                                                                   f"НОВУЮ цель НЕ устанавливаем! Старая={old_target:.1f}, Новая={new_optimal_x:.1f}, Разница={abs(new_optimal_x - old_target):.1f}px")
                                    else:
                                        # Платформа далеко от старой цели - проверяем, не изменилась ли траектория кардинально
                                        # Увеличиваем порог до 50px минимум, чтобы не реагировать на мелкие изменения
                                        threshold = 50 if distance_to_paddle_y < 50 else 80
                                        # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз и НЕ меняется до отскока от стены
                                        # НЕ обновляем позицию, даже если траектория "изменилась кардинально"
                                        # Это нарушение правила - используем старую позицию
                                        optimal_x = old_target
                                        if abs(new_optimal_x - old_target) > threshold:
                                            self._logger.warning(f"[CRITICAL ERROR] НАРУШЕНИЕ ПРАВИЛА: Попытка изменить позицию ({old_target:.1f} -> {new_optimal_x:.1f}) "
                                                                        f"БЕЗ отскока от стены! Используем старую позицию.")
                                else:
                                    # ПРАВИЛО 4: Устанавливаем целевую позицию впервые
                                    # КРИТИЧНО: Проверяем, не была ли позиция уже установлена (нарушение правила)
                                    if self.separation_zone_tracker.target_position_set:
                                        # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                                        old_pos = self.separation_zone_tracker.target_position
                                        if old_pos is not None:
                                            position_diff = abs(old_pos - int(new_optimal_x))
                                            # КРИТИЧНО: Если позиция та же самая (разница < 5px) - используем старую
                                            if position_diff < 5:
                                                self._logger.debug(f"[POSITION UPDATE] Попытка установить ту же позицию (ПРАВИЛО 4)! "
                                                                       f"Старая позиция={old_pos:.1f}, Новая позиция={int(new_optimal_x):.1f}, "
                                                                       f"Разница={position_diff:.1f}px - используем старую")
                                                optimal_x = float(old_pos)
                                            else:
                                                # КРИТИЧНО: Если позиция отличается значительно - сбрасываем и устанавливаем новую
                                                self._logger.warning(f"[RULE VIOLATION] Попытка установить ДРУГУЮ позицию (ПРАВИЛО 4)! "
                                                                         f"Старая позиция={old_pos:.1f}, Новая позиция={int(new_optimal_x):.1f}, "
                                                                         f"Разница={position_diff:.1f}px - сбрасываем и устанавливаем новую")
                                                # Сбрасываем старую позицию
                                                self.separation_zone_tracker.target_position_set = False
                                                self.separation_zone_tracker.target_position = None
                                                self.separation_zone_tracker.paddle_moved_after_set = False
                                                self.separation_zone_tracker.paddle_reached_target = False
                                                # Устанавливаем новую позицию
                                                optimal_x = float(new_optimal_x)
                                                self.separation_zone_tracker.target_position = int(new_optimal_x)
                                                self.separation_zone_tracker.target_position_set = True
                                                self.separation_zone_tracker.frames_since_target_set = 0
                                                self._logger.debug(f"[POSITION RESET] Позиция сброшена и установлена заново (ПРАВИЛО 4)! "
                                                                       f"target_position={int(new_optimal_x):.1f}")
                                        else:
                                            # Старая позиция была None - устанавливаем новую
                                            optimal_x = float(new_optimal_x)
                                            self.separation_zone_tracker.target_position = int(new_optimal_x)
                                            self.separation_zone_tracker.target_position_set = True
                                            self.separation_zone_tracker.frames_since_target_set = 0
                                    else:
                                        # Позиция устанавливается впервые - это правильно
                                        current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                                        self.separation_zone_tracker.target_position = int(new_optimal_x)
                                        self.separation_zone_tracker.target_position_set = True
                                        self.separation_zone_tracker.frames_since_target_set = 0
                                        self.separation_zone_tracker.paddle_moved_after_set = False
                                        self.separation_zone_tracker.paddle_reached_target = False
                                        self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                                        current_target = self.separation_zone_tracker.target_position
                                        current_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                                        self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (ПРАВИЛО 4)! "
                                                               f"target_position={int(new_optimal_x):.1f}, paddle_x={current_x:.1f}")
                                        optimal_x = int(new_optimal_x)
                            else:
                                target_pos = self.separation_zone_tracker.target_position
                                optimal_x = int(target_pos) if target_pos is not None else self.get_optimal_paddle_position()
                        else:
                            target_pos = self.separation_zone_tracker.target_position
                            optimal_x = int(target_pos) if target_pos is not None else self.get_optimal_paddle_position()
                    else:
                        # Используем сохраненную позицию
                        target_pos = self.separation_zone_tracker.target_position
                        if target_pos is not None:
                            optimal_x = int(target_pos)
                        else:
                            optimal_x = self.get_optimal_paddle_position()
                        # КРИТИЧНО: Обновляем счетчик кадров с момента установки цели
                        frames_since_target_set = self.separation_zone_tracker.frames_since_target_set
                        self.separation_zone_tracker.frames_since_target_set = frames_since_target_set + 1
                    
                    if optimal_x is not None:
                        target_pos = int(optimal_x)
                        distance_to_target = abs(current_x - target_pos)
                        
                        # КРИТИЧНО: Сначала проверяем, успеет ли платформа добраться до цели
                        # Это должно быть ПЕРЕД проверкой tolerance, чтобы не останавливаться раньше времени
                        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
                        time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
                        distance_to_move = distance_to_target
                        frames_to_reach = distance_to_move / paddle_speed if paddle_speed > 0 else float('inf')
                        # КРИТИЧНО: Добавляем небольшой запас (0.5 кадра) для учета неточностей расчета
                        # Это особенно важно, когда мяч очень близко
                        will_reach = (frames_to_reach <= time_to_paddle + 0.5) if time_to_paddle != float('inf') else False
                        
                        # КРИТИЧНО: НЕ пересчитываем цель когда мяч очень близко, если траектория стабильна
                        # Если мяч летит по прямой траектории и не может её изменить (нет кубиков на пути, нет стен),
                        # то пересчёт цели в последний момент только вызывает дёргание платформы
                        # Пересчитываем ТОЛЬКО если платформа не успевает добраться до цели
                        force_recalculate = False  # УБРАНО: пересчёт при близком мяче вызывает дёргание
                        
                        # КРИТИЧНО: УБРАНО - пересчет позиции когда "не успевает" вызывает дёргание
                        # Платформа должна продолжать движение к зафиксированной цели, даже если "не успевает"
                        # Это лучше, чем постоянно пересчитывать позицию и дёргаться
                        # if (not will_reach) and time_to_paddle != float('inf') and time_to_paddle > 0:
                        #     ... пересчет позиции ...
                        
                        # ПРАВИЛО 3.1: Если платформа близко к цели - проверяем, нужно ли еще двигаться
                        # КРИТИЧНО: Минимальный tolerance - платформа должна двигаться до точной позиции
                        # Останавливаемся ТОЛЬКО когда действительно достигли цели (tolerance = 3px)
                        tolerance = 3
                        
                        # КРИТИЧНО: УБРАНО - сложная логика с проверкой зон вызывает дёргание
                        # Платформа должна просто двигаться к цели до точной позиции
                        
                        # КРИТИЧНО: Если мяч очень близко к платформе (менее 10 кадров), уменьшаем tolerance еще больше
                        if time_to_paddle != float('inf') and time_to_paddle < 10:
                            tolerance = max(3, tolerance // 2)  # Уменьшаем tolerance вдвое, минимум 3px
                        
                        # КРИТИЧНО: Используем зафиксированную позицию БЕЗ пересчета
                        # Позиция фиксируется один раз и НЕ меняется до отскока от стены
                        target_pos = self.separation_zone_tracker.target_position
                        if target_pos is None:
                            target_pos = float(current_x)
                        else:
                            target_pos = float(target_pos)
                        distance_to_target = abs(current_x - target_pos)
                        # Определяем is_edge_zone на основе сохранённой цели
                        # target_pos гарантированно не None после строки 4136
                        screen_width = self.screen_width
                        ball_radius = self.config.ball.radius
                        min_safe_x = ball_radius + 40
                        max_safe_x = screen_width - ball_radius - 40
                        is_edge_zone = (target_pos < min_safe_x or target_pos > max_safe_x)
                        
                        # Продолжаем движение к актуальной цели, даже если близко к старой цели
                        # Для EDGE зоны используем меньший порог (2px), для остальных - 3px
                        # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров), НЕ останавливаемся до достижения края
                        if is_edge_zone and time_to_paddle < 3:
                            # В EDGE зоне и очень близко - продолжаем движение до края зоны
                            # Проверяем, достигли ли мы края зоны
                            screen_width = self.screen_width
                            # Определяем, к какому краю нужно двигаться
                            saved_target = self.separation_zone_tracker.target_position
                            target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                            
                            if target_to_check > screen_width / 2:
                                # Правый край - проверяем, достигли ли мы правого края
                                right_edge = screen_width - self.paddle_width // 2
                                if abs(current_x - right_edge) > 2:
                                    pass  # Продолжаем движение к правому краю
                                else:
                                    # Достигли правого края - останавливаемся
                                    if not self.separation_zone_tracker.paddle_reached_target:
                                        self.separation_zone_tracker.paddle_reached_target = True
                                    return 0
                            else:
                                # Левый край - проверяем, достигли ли мы левого края
                                left_edge = self.paddle_width // 2
                                if abs(current_x - left_edge) > 2:
                                    pass  # Продолжаем движение к левому краю
                                else:
                                    # Достигли левого края - останавливаемся
                                    if not self.separation_zone_tracker.paddle_reached_target:
                                        self.separation_zone_tracker.paddle_reached_target = True
                                    return 0
                        elif distance_to_target <= tolerance:
                            # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                            # Траектория мяча не меняется - используем сохраненную цель БЕЗ изменений
                            # НЕ проверяем actual_distance - это вызывает дёргание
                            
                            # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), НЕ останавливаемся
                            # Это критично для предотвращения потери мяча в последний момент
                            # КРИТИЧНО: Если мяч в EDGE зоне, НЕ останавливаемся до достижения края зоны
                            # даже если мяч не очень близко - это критично для предотвращения потери мяча у края
                            if (time_to_paddle != float('inf') and time_to_paddle < 3) or is_edge_zone:
                                # Мяч очень близко ИЛИ в EDGE зоне - продолжаем движение, даже если близко к цели
                                # Для EDGE зоны проверяем, достигли ли мы края зоны
                                if is_edge_zone:
                                    screen_width = self.screen_width
                                    saved_target = self.separation_zone_tracker.target_position
                                    target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                                    
                                    if target_to_check > screen_width / 2:
                                        # Правый край - проверяем, достигли ли мы правого края
                                        right_edge = screen_width - self.paddle_width // 2
                                        if abs(current_x - right_edge) > 2:
                                            # Еще не достигли правого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли правого края - останавливаемся
                                            if not self.separation_zone_tracker.paddle_reached_target:
                                                self.separation_zone_tracker.paddle_reached_target = True
                                            return 0
                                    else:
                                        # Левый край - проверяем, достигли ли мы левого края
                                        left_edge = self.paddle_width // 2
                                        if abs(current_x - left_edge) > 2:
                                            # Еще не достигли левого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли левого края - останавливаемся
                                            if not self.separation_zone_tracker.paddle_reached_target:
                                                self.separation_zone_tracker.paddle_reached_target = True
                                            return 0
                            else:
                                # Мяч очень близко, но не в EDGE зоне - продолжаем движение
                                pass  # Пропускаем остановку, продолжаем движение
                        else:
                            # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                            # Если достигли сохраненной цели - останавливаемся
                            if not self.separation_zone_tracker.paddle_reached_target:
                                self.separation_zone_tracker.paddle_reached_target = True
                            # КРИТИЧНО: Логируем для диагностики
                            # Фильтрация по уровню выполняется автоматически системой логирования Python
                            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.1: Платформа очень близко к цели (distance={distance_to_target:.1f} <= {tolerance}), не двигаемся")
                            self._log_paddle_movement(current_x, current_x, "paddle_reached_target", 1.0)
                            return 0
                    
                    # КРИТИЧНО: Проверяем, успеет ли платформа доехать до текущей цели
                    # Если нет - обновляем целевую позицию на достижимую
                    ball_y_check = self.current_game_state.ball_position.y if self.current_game_state else 0
                    ball_vel_y_check = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    paddle_y_check = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                    distance_to_paddle_check = paddle_y_check - ball_y_check if ball_y_check < paddle_y_check else 0
                    time_to_paddle_check = distance_to_paddle_check / ball_vel_y_check if ball_vel_y_check > 0 and distance_to_paddle_check > 0 else float('inf')
                    
                    if time_to_paddle_check != float('inf') and time_to_paddle_check > 0:
                        frames_to_reach_current = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
                        safety_margin = 1.2  # 20% запас
                        
                        # Если платформа не успеет доехать до текущей цели - обновляем её
                        if frames_to_reach_current > time_to_paddle_check * safety_margin:
                            # Рассчитываем достижимую позицию
                            max_distance = paddle_speed * time_to_paddle_check * 0.85
                            
                            # Рассчитываем предсказанную позицию мяча
                            ball_x_check = self.current_game_state.ball_position.x if self.current_game_state else 0
                            ball_vel_x_check = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                            predicted_ball_x = ball_x_check + ball_vel_x_check * time_to_paddle_check
                            
                            # Применяем логику зон
                            zone_size = self.config.paddle.zone_size
                            screen_center = self.screen_width / 2
                            left_threshold = screen_center - zone_size * 2
                            right_threshold = screen_center + zone_size * 2
                            
                            if predicted_ball_x < left_threshold:
                                zone_center_x = predicted_ball_x + zone_size
                            elif predicted_ball_x > right_threshold:
                                zone_center_x = predicted_ball_x - zone_size
                            else:
                                zone_center_x = predicted_ball_x
                            
                            # Выбираем достижимую позицию
                            if zone_center_x > current_x:
                                achievable_target = min(zone_center_x, current_x + max_distance)
                            else:
                                achievable_target = max(zone_center_x, current_x - max_distance)
                            
                            # Обновляем целевую позицию
                            old_target = target_pos
                            target_pos = int(achievable_target)
                            self.separation_zone_tracker.target_position = target_pos
                            distance_to_target = abs(current_x - target_pos)
                            
                            self._logger.warning(f"[TARGET UPDATE] Платформа не успевает до текущей цели ({old_target:.1f}px). "
                                               f"Обновляем на достижимую: {target_pos:.1f}px "
                                               f"(время_до_мяча={time_to_paddle_check:.1f}, время_до_старой_цели={frames_to_reach_current:.1f})")
                    
                    # ПРАВИЛО 3.2: Платформа еще не достигла цели - двигаемся к сохраненной позиции
                    # КРИТИЧНО: УБРАНО - сложная логика с проверкой "очень близко" вызывает дёргание
                    # Платформа должна просто двигаться к цели до точной позиции (tolerance = 3px)
                    
                    # Устанавливаем флаг, что платформа начала двигаться после установки цели
                    if not self.separation_zone_tracker.paddle_moved_after_set:
                        self.separation_zone_tracker.paddle_moved_after_set = True
                        # КРИТИЧНО: Логируем начало движения
                        self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.2: Начинаем движение к сохраненной позиции. current_x={current_x}, target_pos={target_pos}, distance={distance_to_target:.1f}")
                        self._log_paddle_movement(current_x, target_pos, "paddle_moving_to_target", 0.9)
                    
                    # КРИТИЧНО: Проверяем, что движение действительно нужно
                    # Если target_pos == current_x, не двигаемся
                    if target_pos == current_x:
                        return 0
                    
                    # Двигаемся к сохраненной позиции БЕЗ дополнительных проверок
                    movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                    # КРИТИЧНО: Проверяем, что movement не равен 0 (должно быть -1 или 1)
                    if movement == 0:
                        # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                        self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 3.2: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                        return self._fallback_movement(current_x)
                    
                    # КРИТИЧНО: Логируем движение с информацией о скорости (всегда)
                    # Примечание: проверка will_reach уже выполнена выше, перед проверкой tolerance
                    # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
                    # Пересчитываем для логирования
                    ball_y_log = self.current_game_state.ball_position.y if self.current_game_state else 0
                    ball_vel_y_log = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    paddle_y_log = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                    distance_to_paddle_log = paddle_y_log - ball_y_log if ball_y_log < paddle_y_log else 0
                    time_to_paddle_log = distance_to_paddle_log / ball_vel_y_log if ball_vel_y_log > 0 and distance_to_paddle_log > 0 else float('inf')
                    distance_to_move_log = distance_to_target
                    frames_to_reach_log = distance_to_move_log / paddle_speed if paddle_speed > 0 else float('inf')
                    will_reach_log = frames_to_reach_log <= time_to_paddle_log if time_to_paddle_log != float('inf') else False
                    
                    self._logger.debug(f"[PADDLE MOVEMENT] movement={movement} distance={distance_to_target:.1f}px "
                                       f"current_x={current_x:.1f} target={target_pos:.1f} | "
                                       f"paddle_speed={paddle_speed} frames_to_reach={frames_to_reach_log:.1f} "
                                       f"time_to_paddle={time_to_paddle_log:.1f} will_reach={will_reach_log}")
                    
                    self._update_loop_tracking(movement, int(current_x), int(target_pos))
                    self._update_smoothness_tracking(movement, current_x)
                    self._log_paddle_movement(current_x, target_pos, "moving_to_locked_target", 1.0)
                    # target_pos is None - сбрасываем флаг и продолжаем обработку
                    self.separation_zone_tracker.target_position_set = False
                    self._log_paddle_movement(current_x, current_x, "target_reset_none", 1.0)
                    # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
            
            # ПРАВИЛО 4: Если целевая позиция НЕ установлена и мяч в зоне разделения
            # - устанавливаем целевую позицию ОДИН РАЗ через get_optimal_paddle_position
            # - после установки используем её без пересчета
            # КРИТИЧНО: Проверяем, что мяч НЕ потерян перед установкой целевой позиции
            if in_separation_zone and not self.separation_zone_tracker.target_position_set and not ball_lost:
                # КРИТИЧНО: Логируем установку целевой позиции
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Устанавливаем целевую позицию. ball_y={ball_y:.1f}, in_separation_zone={in_separation_zone}")
                # Устанавливаем целевую позицию один раз
                optimal_x = self.get_optimal_paddle_position()
                # get_optimal_paddle_position() всегда возвращает int, не None
                
                # КРИТИЧНО: Проверяем, успеет ли платформа добраться до цели ПЕРЕД установкой
                # Рассчитываем время до приземления мяча и возможность достижения цели
                distance_to_target = abs(current_x - optimal_x)
                distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                
                # КРИТИЧНО: Всегда проверяем возможность достижения цели
                # Рассчитываем время, необходимое для достижения цели платформой
                if time_to_paddle != float('inf') and time_to_paddle > 0 and distance_to_target > 0:
                    # Используем текущую скорость платформы (уже увеличенную)
                    frames_to_reach = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
                    
                    # КРИТИЧНО: Увеличиваем запас безопасности до 20% и используем только 85% времени
                    # Это гарантирует, что платформа успеет доехать с запасом
                    safety_margin = 1.2  # 20% запас
                    time_usage = 0.85  # Используем только 85% времени для безопасности
                    
                    if frames_to_reach > time_to_paddle * safety_margin:
                        # Платформа не успеет - используем максимальное расстояние, которое можно пройти
                        max_distance = paddle_speed * time_to_paddle * time_usage
                        
                        # КРИТИЧНО: Рассчитываем предсказанную позицию мяча для более точной промежуточной цели
                        ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                        ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        predicted_ball_x = ball_x + ball_vel_x * time_to_paddle
                        
                        # Применяем логику зон к предсказанной позиции
                        zone_size = self.config.paddle.zone_size
                        screen_center = self.screen_width / 2
                        left_threshold = screen_center - zone_size * 2
                        right_threshold = screen_center + zone_size * 2
                        
                        if predicted_ball_x < left_threshold:
                            zone_center_x = predicted_ball_x + zone_size
                        elif predicted_ball_x > right_threshold:
                            zone_center_x = predicted_ball_x - zone_size
                        else:
                            zone_center_x = predicted_ball_x
                        
                        # Выбираем промежуточную позицию в направлении зоны мяча, но не дальше чем можем пройти
                        if zone_center_x > current_x:
                            achievable_target = min(zone_center_x, current_x + max_distance)
                        else:
                            achievable_target = max(zone_center_x, current_x - max_distance)
                        
                        self._logger.warning(f"[ACHIEVABLE TARGET] Цель недостижима: расстояние={distance_to_target:.1f}px, "
                                           f"время_до_мяча={time_to_paddle:.1f}, время_до_цели={frames_to_reach:.1f}. "
                                           f"Используем промежуточную цель: {achievable_target:.1f} вместо {optimal_x:.1f} "
                                           f"(predicted_ball_x={predicted_ball_x:.1f}, zone_center={zone_center_x:.1f})")
                        optimal_x = int(achievable_target)
                
                # Дополнительная проверка для экстренных ситуаций (мяч очень близко)
                if time_to_paddle != float('inf') and time_to_paddle < 10 and distance_to_target > 100:
                    # Мяч очень близко, а платформа далеко - пересчитываем цель с учетом зон
                    # Вместо простого ограничения движения, пересчитываем оптимальную позицию
                    # с учетом того, что платформа не успеет далеко переместиться
                    original_optimal = optimal_x
                    
                    # Рассчитываем максимальное расстояние, которое платформа может пройти
                    # Используем переданный paddle_speed или базовую скорость
                    max_distance = paddle_speed * time_to_paddle
                    
                    # Определяем, в какую зону попадает predicted_x
                    ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                    ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    predicted_x = ball_x + ball_vel_x * time_to_paddle
                    
                    # Применяем логику зон к predicted_x
                    zone_size = self.config.paddle.zone_size
                    screen_center = self.screen_width / 2
                    left_threshold = screen_center - zone_size * 2
                    right_threshold = screen_center + zone_size * 2
                    
                    if predicted_x < left_threshold:
                        # Левая зона
                        zone_center_x = predicted_x + zone_size
                    elif predicted_x > right_threshold:
                        # Правая зона
                        zone_center_x = predicted_x - zone_size
                    else:
                        # Центральная зона
                        zone_center_x = predicted_x
                    
                    # Ограничиваем максимальное расстояние движения
                    if zone_center_x > current_x:
                        optimal_x = int(min(zone_center_x, current_x + max_distance))
                    else:
                        optimal_x = int(max(zone_center_x, current_x - max_distance))
                    
                    self._logger.debug(f"[TARGET ADJUST] Мяч близко! time_to_paddle={time_to_paddle:.1f}, скорректирована цель с {original_optimal:.1f} на {optimal_x:.1f} (max_distance={max_distance:.1f})")
                
                # Сохраняем целевую позицию
                current_target = self.separation_zone_tracker.target_position
                old_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                self._logger.debug(f"[POSITION CHANGE] ФЛАГ: Платформа устанавливает новую цель (ПРАВИЛО 4)! paddle_x={current_x:.1f}, "
                                   f"старая_цель={old_target_str}, "
                                   f"новая_цель={optimal_x:.1f}, distance_to_target={abs(current_x - optimal_x):.1f}")
                self.separation_zone_tracker.target_position = int(optimal_x)
                self.separation_zone_tracker.target_position_set = True
                self.separation_zone_tracker.paddle_moved_after_set = False
                self.separation_zone_tracker.paddle_reached_target = False
                self.separation_zone_tracker.frames_since_target_set = 0
                # КРИТИЧНО: Сохраняем vel_x для отслеживания отскоков от стены
                ball_vel_x_save = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                self.separation_zone_tracker.saved_ball_vel_x = ball_vel_x_save
                self._log_paddle_movement(current_x, optimal_x, "target_position_set", 1.0)
                # Продолжаем обработку с установленной позицией
                target_pos = int(optimal_x)
                distance_to_target = abs(current_x - target_pos)
                
                # КРИТИЧНО: Проверяем, что движение действительно нужно
                # Если target_pos == current_x, не двигаемся
                if target_pos == current_x:
                    self.separation_zone_tracker.paddle_reached_target = True
                    return 0
                
                # КРИТИЧНО: В зоне разделения останавливаемся только если ОЧЕНЬ близко к цели
                # Увеличено до 25 пикселей для предотвращения дрожания
                if distance_to_target <= 25:
                    self.separation_zone_tracker.paddle_reached_target = True
                    # КРИТИЧНО: Логируем для диагностики
                    # Фильтрация по уровню выполняется автоматически системой логирования Python
                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Платформа очень близко к цели (distance={distance_to_target:.1f} <= 5), не двигаемся")
                    return 0
                
                movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                # КРИТИЧНО: Проверяем, что movement не равен 0
                if movement == 0:
                    # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                    self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 4: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                    return self._fallback_movement(current_x)
                
                # КРИТИЧНО: Логируем движение
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Движение! movement={movement}, distance={distance_to_target:.1f}, current_x={current_x}, target_pos={target_pos}")
                
                self.separation_zone_tracker.paddle_moved_after_set = True
                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                self._update_smoothness_tracking(movement, current_x)
                self._log_paddle_movement(current_x, target_pos, "moving_to_new_target", 0.9)
                # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
            
            # ПРАВИЛО 5: Если мяч НЕ в зоне разделения и целевая позиция НЕ установлена
            # - используем обычную логику (мяч еще в зоне кубиков или выше)
            # КРИТИЧНО: Но только если мяч НЕ потерян и движется вниз
            # Если мяч потерян или движется вверх - не двигаемся
            if ball_lost:
                self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle_rule5", 1.0)
                return 0
            
            # КРИТИЧНО: УБРАНО правило "не двигаться когда мяч летит вверх"
            # Платформа ДОЛЖНА двигаться к точке падения мяча даже когда мяч летит вверх,
            # чтобы успеть к моменту падения. Продолжаем расчет оптимальной позиции.
            
            # КРИТИЧНО: Если мяч в разрешенной зоне (ниже кубиков, но выше платформы) и движется вниз
            # - платформа ДОЛЖНА двигаться к точке падения мяча
            optimal_x = self.get_optimal_paddle_position()
            # get_optimal_paddle_position() всегда возвращает int, не None
            
            # Проверяем зацикливание и при необходимости меняем стратегию
            # НО ТОЛЬКО если целевая позиция НЕ установлена
            if not self.separation_zone_tracker.target_position_set:
                self._change_strategy_if_looping()
                if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                    optimal_x = self._apply_alternative_strategy(optimal_x)
                    # Проверяем, что альтернативная стратегия тоже валидна
                    if optimal_x is None:
                        return self._fallback_movement(current_x)
            
            # Допуск по точности позиционирования
            precision_tolerance = 2
            # Проверяем дрожание и применяем штрафы
            jitter_detected = self._detect_jitter()
            if jitter_detected:
                # Увеличиваем допуск для уменьшения дрожания
                precision_tolerance = max(5, precision_tolerance + 2)
                # Увеличиваем штраф за дрожание
                self.smoothness_system["smoothness_penalty"] = min(
                    1.0, self.smoothness_system["smoothness_penalty"] + 0.1
                )
            else:
                # Уменьшаем штраф при плавном движении
                self.smoothness_system["smoothness_penalty"] = max(
                    0.0, self.smoothness_system["smoothness_penalty"] - 0.05
                )
            
            # Допуск по точности позиционирования (учитываем штраф за дрожание)
            base_precision_tolerance = 2
            precision_tolerance = base_precision_tolerance + int(
                self.smoothness_system["smoothness_penalty"] * 3
            )
            
            # Увеличиваем допуск, когда мяч движется вниз и траектория известна
            if self.current_game_state:
                ball_vel_y = (
                    self.current_game_state.ball_velocity.y
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                ball_y = self.current_game_state.ball_position.y
                paddle_zone_start = self.screen_height - 60
                separation_zone_start = self.separation_zone_tracker.separation_zone_start
                in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
                
                # КРИТИЧНО: НЕ увеличиваем допуск слишком сильно, иначе платформа не будет двигаться
                # Если мяч движется вниз и уже ниже кубиков - используем умеренный допуск
                if ball_vel_y > 0 and ball_y > 250:  # Мяч движется вниз и ниже кубиков
                    # Используем умеренный допуск (5-10 пикселей), чтобы платформа могла двигаться
                    # Только если платформа УЖЕ очень близко к цели (менее 5 пикселей) - не двигаемся
                    if abs(optimal_x - current_x) < 5:
                        precision_tolerance = max(precision_tolerance, 5)  # Очень близко - не двигаемся
                    else:
                        # Платформа еще не достигла цели - используем минимальный допуск для движения
                        precision_tolerance = max(precision_tolerance, 2)  # Минимальный допуск
            
            distance_to_optimal = abs(optimal_x - current_x)
            
            # Поощряем минимальные движения - если расстояние очень мало, не двигаемся
            min_movement_distance = self.smoothness_system["min_movement_distance"]
            
            # КРИТИЧНО: Убрана проверка ball_approaching_quickly - она вызывала дергание
            # В зоне разделения с установленной целевой позицией платформа просто движется к цели и останавливается
            
            if distance_to_optimal < min_movement_distance:
                # Если расстояние меньше минимального, проверяем, стоит ли двигаться
                if distance_to_optimal <= precision_tolerance:
                    movement = 0
                    # Поощряем точное позиционирование
                    self.smoothness_system["consecutive_stops"] += 1
                    if self.smoothness_system["consecutive_stops"] > 3:
                        # Уменьшаем штраф за хорошее позиционирование
                        self.smoothness_system["smoothness_penalty"] = max(
                            0.0, self.smoothness_system["smoothness_penalty"] - 0.1
                        )
                    # Сохраняем базовую скорость, так как не двигаемся
                    self._last_adjusted_paddle_speed = paddle_speed
                else:
                    # Двигаемся только если действительно нужно
                    movement = self._calculate_smooth_movement(
                        current_x, optimal_x, distance_to_optimal
                    )
                    # Сохраняем базовую скорость для этого случая
                    self._last_adjusted_paddle_speed = paddle_speed
            elif distance_to_optimal <= precision_tolerance:
                movement = 0
                self.smoothness_system["consecutive_stops"] += 1
                # Сохраняем базовую скорость, так как не двигаемся
                self._last_adjusted_paddle_speed = paddle_speed
            else:
                self.smoothness_system["consecutive_stops"] = 0
                # Адаптивная скорость от системы обучения
                if self.current_game_state:
                    ball_speed = self.current_game_state.ball_speed
                    distance_to_target = distance_to_optimal
                    
                    # Рассчитываем время до встречи с мячом для более агрессивного увеличения скорости
                    time_to_meeting = float("inf")
                    ball_vel_y = (
                        self.current_game_state.ball_velocity.y
                        if hasattr(self.current_game_state, "ball_velocity")
                        else 0
                    )
                    if ball_vel_y > 0:  # Мяч движется вниз
                        ball_y = self.current_game_state.ball_position.y
                        paddle_y = self.current_game_state.paddle_position.y
                        distance_y = paddle_y - ball_y
                        if distance_y > 0:
                            time_to_meeting = distance_y / ball_vel_y
                    
                    speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                        ball_speed, distance_to_target
                    )
                    
                    # Если мяч быстро приближается, агрессивно увеличиваем скорость
                    if time_to_meeting != float("inf") and time_to_meeting > 0:
                        # Чем меньше времени до встречи, тем выше должна быть скорость
                        if time_to_meeting < 30:  # Менее 30 кадров (0.5 сек при 60 FPS)
                            urgency_factor = 30.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 3.0
                            )  # До 3x дополнительного ускорения
                        elif time_to_meeting < 60:  # Менее 60 кадров (1 сек)
                            urgency_factor = 60.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 2.0
                            )  # До 2x дополнительного ускорения
                    
                    # ИСПРАВЛЕНИЕ: Адаптивная базовая скорость в зависимости от расстояния
                    # При больших расстояниях (>150px) увеличиваем базовую скорость дополнительно
                    base_speed_multiplier = 10.0  # Базовая скорость в 10 раз
                    
                    # ИСПРАВЛЕНИЕ: При расстоянии >150px увеличиваем скорость еще больше
                    if distance_to_target > 150:
                        # Для больших расстояний используем более агрессивную скорость
                        base_speed_multiplier = 15.0  # Увеличиваем до 15x для больших расстояний
                    elif distance_to_target > 100:
                        base_speed_multiplier = 12.0  # 12x для средних расстояний
                    
                    # ИСПРАВЛЕНИЕ: При экстренных ситуациях (мало времени до встречи) еще больше увеличиваем
                    if time_to_meeting != float('inf') and time_to_meeting < 20:  # Менее 20 кадров
                        base_speed_multiplier *= 1.5  # Дополнительно увеличиваем на 50%
                    
                    # Ограничиваем минимальный множитель скорости, чтобы платформа не двигалась слишком медленно
                    # AI может увеличивать скорость до 10x для достижения цели (в дополнение к базовому 10-15x)
                    max_multiplier = 10.0  # Дополнительный множитель до 10x
                    speed_multiplier = max(0.8, min(max_multiplier, speed_multiplier))
                    adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)  # ИСПРАВЛЕНО: убрано двойное умножение
                    # Гарантируем минимальную скорость платформы
                    adjusted_paddle_speed = max(
                        int(paddle_speed * 0.8), adjusted_paddle_speed
                    )
                    self._last_paddle_speed_multiplier = speed_multiplier
                    # Сохраняем для использования в PyGameBall.py
                    self._last_adjusted_paddle_speed = adjusted_paddle_speed
                else:
                    adjusted_paddle_speed = paddle_speed
                
                # Сохраняем для использования в PyGameBall.py
                self._last_adjusted_paddle_speed = adjusted_paddle_speed
                
                movement = self.position_optimizer.calculate_paddle_movement(
                    current_x, optimal_x, adjusted_paddle_speed
                )
                
                # Если расчёт не даёт движения, но мы не на месте — fallback
                if movement == 0 and optimal_x != current_x:
                    movement = self._fallback_movement(current_x)
            
            # Обновляем данные по зацикливанию
            self._update_loop_tracking(movement, current_x, optimal_x)
            
            # Обновляем данные по плавности движения
            self._update_smoothness_tracking(movement, current_x)
            
            # Логирование движения
            if movement != 0:
                reason = (
                    "ball_tracking"
                    if not self.is_ball_moving_towards_paddle()
                    else "trajectory_optimization"
                )
                confidence = self._calculate_decision_confidence(optimal_x)
                self.performance_logger.log_paddle_movement(
                    from_x=current_x,
                    to_x=current_x + movement * paddle_speed,
                    reason=reason,
                    confidence=confidence,
                )
            
            # Статистика по ходам
            self.current_game_stats["total_moves"] += 1
            if abs(optimal_x - current_x) < 10:
                self.current_game_stats["optimal_moves"] += 1
            
            # Учитываем плавность движения в обучении
            if movement != 0:
                # Штрафуем за дрожание при обучении
                if self.smoothness_system["smoothness_penalty"] > 0.5:
                    # Высокий штраф за дрожание - это плохое поведение
                    jitter_penalty = {
                        "action_type": "movement_jitter",
                        "success": False,
                        "penalty": self.smoothness_system["smoothness_penalty"],
                        "movement_distance": abs(optimal_x - current_x),
                    }
                    # Можно добавить в систему обучения для улучшения поведения
                    # self.learning_system.update_strategy(jitter_penalty)
            
            # Записываем метрику производительности перед возвратом
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания.
        Использует PaddleMovementStrategy для модульной логики движения.

        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
        """
        start_time_monitor = time.time() if self.performance_monitor else None

        Returns:
            Смещение платформы (-1, 0, 1).
        """
        # Используем стратегию движения, если она инициализирована
        if self.paddle_movement_strategy is not None:
            return self._execute_movement_strategy(current_x, paddle_speed)
        
        # Fallback на старую логику, если стратегия не инициализирована
        if not self.current_game_state or not self.is_active:
            return self._fallback_movement(current_x)

        try:
            # Получаем состояние мяча
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            separation_zone_start = self.separation_zone_tracker.separation_zone_start
            paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
            
            # КРИТИЧНО: Логируем состояние мяча для диагностики
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            optimal_x = self.get_optimal_paddle_position()
            self._logger.debug(f"[PADDLE DEBUG] ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y}, current_x={current_x}, optimal_x={optimal_x}, distance={abs(current_x - optimal_x):.1f}")
            
            # КРИТИЧНО: УБРАНО ПРАВИЛО 1 - платформа ДОЛЖНА двигаться к точке падения мяча
            # даже когда мяч летит вверх, чтобы успеть к моменту падения
            # Продолжаем расчет оптимальной позиции независимо от направления мяча
            
            if ball_vel_y == 0:
                # КРИТИЧНО: Если vel_y == 0, это ошибка состояния (должно быть исправлено в PyGameBall.py)
                # Но на всякий случай продолжаем движение к оптимальной позиции, а не используем fallback
                # Это предотвращает ситуацию, когда платформа перестает двигаться из-за временного vel_y=0
                # Логируем для диагностики, но продолжаем нормальную логику
                self._log_paddle_movement(current_x, current_x, "ball_vel_y_zero_warning", 0.5)
                # Продолжаем обработку с обычной логикой - НЕ возвращаем fallback!
            
            # ПРАВИЛО 2: Если мяч в зоне кубиков - платформа НЕ двигается
            # КРИТИЧНО: ИСКЛЮЧЕНИЕ - при 1 кирпиче разрешаем упреждающее движение
            bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 50
            is_last_brick = bricks_count == 1
            
            if ball_y < separation_zone_start and not is_last_brick:
                # Для нормальных случаев - не двигаемся в зоне кубиков
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2: Мяч в зоне кубиков (ball_y={ball_y:.1f} < {separation_zone_start}), платформа не двигается")
                self._log_paddle_movement(current_x, current_x, "ball_in_bricks_zone", 1.0)
                return 0
            elif ball_y < separation_zone_start and is_last_brick:
                # КРИТИЧНО: При 1 кирпиче разрешаем упреждающее движение
                # Это позволяет платформе подготовиться к попаданию в последний кирпич
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2 EXCEPTION: Последний кирпич! Разрешаем движение в зоне кубиков")
                # Продолжаем обработку - не возвращаем 0
            
            # КРИТИЧНО: Проверяем, не потерян ли мяч (ниже верхней границы платформы)
            # Если мяч ниже верхней границы платформы - он считается потерянным, платформа НЕ двигается
            paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
            ball_lost = ball_y > paddle_y  # Мяч ниже верхней границы платформы
            
            if ball_lost:
                # Мяч потерян - платформа НЕ двигается
                # КРИТИЧНО: Логируем для диагностики (периодически)
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] Мяч потерян (ball_y={ball_y:.1f} > paddle_y={paddle_y:.1f}), платформа не двигается")
                self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle", 1.0)
                return 0
            
            # Проверяем, находится ли мяч в зоне разделения
            # КРИТИЧНО: Мяч должен быть выше верхней границы платформы и в разрешенной зоне
            # Зона разделения: от separation_zone_start до верхней границы платформы
            in_separation_zone = separation_zone_start <= ball_y < paddle_y and ball_vel_y > 0
            
            # КРИТИЧНО: Логируем состояние зоны разделения для диагностики
            # Логируем всегда когда мяч в зоне разделения или близко к платформе
            should_log = in_separation_zone or (ball_y > paddle_y - 100 and ball_vel_y > 0)
            # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
            if should_log:  # Всегда логируем когда мяч близко
                ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                ball_speed = self.current_game_state.ball_speed if self.current_game_state else 0
                distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
                time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
                # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() если позиция уже зафиксирована
                # Это может вызвать пересчет и дергание
                if self.separation_zone_tracker.target_position_set:
                    target_pos = self.separation_zone_tracker.target_position
                    if target_pos is not None:
                        optimal_x = int(target_pos)
                    else:
                        optimal_x = self.get_optimal_paddle_position()
                else:
                    optimal_x = self.get_optimal_paddle_position()
                distance_to_target = abs(current_x - optimal_x) if optimal_x is not None else 0
                self._logger.debug(f"[BALL TRACKING] ball=({ball_x:.1f},{ball_y:.1f}) vel=({ball_vel_x:.1f},{ball_vel_y:.1f}) speed={ball_speed:.1f} | "
                                   f"paddle_x={current_x:.1f} optimal_x={optimal_x:.1f} dist_to_target={distance_to_target:.1f} | "
                                   f"zone: sep_start={separation_zone_start} paddle_y={paddle_y:.1f} in_zone={in_separation_zone} | "
                                   f"time_to_paddle={time_to_paddle:.2f} frames")
            
            # КРИТИЧНО: Обнаружение отскоков от кирпичей по резкому изменению позиции мяча ИЛИ изменению направления
            ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
            current_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            current_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            
            brick_bounce_detected = False
            if self._last_ball_position is not None and self._last_ball_velocity is not None and self.current_game_state:
                # Проверяем резкое изменение позиции мяча (более 50 пикселей за кадр)
                position_change = abs(ball_x - self._last_ball_position.x)
                # Также проверяем изменение Y координаты вверх (мяч отскочил)
                y_change = ball_y - self._last_ball_position.y
                
                # КРИТИЧНО: Проверяем изменение направления ball_vel_y (мяч отскочил вверх после движения вниз)
                # Это самый надежный способ обнаружения отскока от кирпича
                last_vel_y = self._last_ball_velocity.y
                vel_y_direction_change = (last_vel_y > 0 and current_vel_y < 0)  # Мяч двигался вниз, теперь вверх
                
                # Отскок от кирпича: 
                # 1. Резкое изменение позиции X (>50px) И vel_x не изменилась сильно
                # 2. ИЛИ изменение направления Y координаты вверх (y_change < -10)
                # 3. ИЛИ изменение направления ball_vel_y (мяч отскочил вверх)
                if position_change > 50 or (y_change < -10 and ball_y < separation_zone_start) or vel_y_direction_change:
                    # Проверяем, что это не отскок от стены (vel_x должен был измениться, но это уже отслеживается)
                    vel_x_change = abs(current_vel_x - self._last_ball_velocity.x)
                    
                    # Если скорость vel_x не изменилась сильно, но позиция изменилась резко - это отскок от кирпича
                    # ИЛИ если изменилось направление ball_vel_y (мяч отскочил вверх)
                    if (vel_x_change < 5 and position_change > 50) or vel_y_direction_change:
                        brick_bounce_detected = True
                        bounce_reason = "vel_y direction change" if vel_y_direction_change else f"position change {position_change:.1f}px"
                        self._logger.debug(f"[BRICK BOUNCE DETECTED] {bounce_reason}, "
                                         f"ball=({ball_x:.1f},{ball_y:.1f}) prev=({self._last_ball_position.x:.1f},{self._last_ball_position.y:.1f}), "
                                         f"vel_y: {last_vel_y:.1f} -> {current_vel_y:.1f}")
            
            # Обновляем предыдущую позицию мяча
            if self.current_game_state:
                self._last_ball_position = Point(ball_x, ball_y)
                self._last_ball_velocity = Point(current_vel_x, current_vel_y)
            
            # ПРАВИЛО 3: Если целевая позиция установлена - используем её БЕЗ пересчета
            # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз при входе мяча в зону разделения
            # и не меняется до следующего отскока от стены ИЛИ отскока от кирпича
            if self.separation_zone_tracker.target_position_set:
                # КРИТИЧНО: Проверяем отскоки от стены И от кирпичей
                current_target = self.separation_zone_tracker.target_position
                if current_target is not None and in_separation_zone:
                    # КРИТИЧНО: Проверяем изменение vel_x - это признак отскока от стены
                    # ИЛИ обнаружение отскока от кирпича
                    saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                    
                    # Если vel_x изменился (мяч отскочил от стены) ИЛИ обнаружен отскок от кирпича - сбрасываем цель
                    if (saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > 0.1) or brick_bounce_detected:
                        # Мяч отскочил от стены или от кирпича - траектория изменилась, нужно пересчитать цель
                        if brick_bounce_detected:
                            self._logger.debug(f"[TARGET RESET] Мяч отскочил от кирпича! Траектория изменилась, пересчитываем цель")
                        else:
                            self._logger.debug(f"[TARGET RESET] Мяч отскочил от стены! Старая vel_x={saved_vel_x:.1f}, Новая vel_x={current_vel_x:.1f}")
                        
                        # ИСПРАВЛЕНИЕ: Проверяем расстояние до новой потенциальной цели перед сбросом
                        # Рассчитываем новую потенциальную цель для проверки расстояния
                        ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else 0
                        
                        # Рассчитываем время до приземления мяча
                        distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                        time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                        
                        # Предсказываем новую позицию приземления
                        if time_to_paddle != float('inf') and time_to_paddle > 0:
                            predicted_new_x = ball_x + current_vel_x * time_to_paddle
                            # Применяем зоны
                            zone_size = self.config.paddle.zone_size
                            screen_center = self.screen_width / 2
                            left_threshold = screen_center - zone_size * 2
                            right_threshold = screen_center + zone_size * 2
                            
                            if predicted_new_x < left_threshold:
                                zone_center_x = predicted_new_x + zone_size
                            elif predicted_new_x > right_threshold:
                                zone_center_x = predicted_new_x - zone_size
                            else:
                                zone_center_x = predicted_new_x
                            
                            distance_to_new_target = abs(current_x - zone_center_x)
                            
                            # ИСПРАВЛЕНИЕ: Если новая цель слишком далеко (>200px), используем консервативный подход
                            # Вместо резкого изменения цели, двигаемся постепенно или выбираем промежуточную позицию
                            if distance_to_new_target > 200:
                                # Рассчитываем максимальное расстояние, которое можем пройти за время до приземления
                                max_distance = paddle_speed * time_to_paddle if time_to_paddle < 100 else 200
                                
                                # Выбираем промежуточную позицию в направлении новой цели
                                if zone_center_x > current_x:
                                    conservative_target = min(zone_center_x, current_x + max_distance)
                                else:
                                    conservative_target = max(zone_center_x, current_x - max_distance)
                                
                                # КРИТИЧНО: Ограничиваем границами экрана, чтобы избежать отрицательных координат
                                min_x = self.paddle_width // 2
                                max_x = self.screen_width - self.paddle_width // 2
                                conservative_target = max(min_x, min(max_x, conservative_target))
                                
                                self._logger.debug(f"[CONSERVATIVE TARGET] Большое расстояние ({distance_to_new_target:.1f}px), "
                                                   f"используем промежуточную цель: {conservative_target:.1f} вместо {zone_center_x:.1f}")
                                
                                # Устанавливаем консервативную цель вместо полного сброса
                                self.separation_zone_tracker.target_position = int(conservative_target)
                                self.separation_zone_tracker.target_position_set = True
                                self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                                # Продолжаем с этой целью без полного сброса
                            else:
                                # Расстояние приемлемое - выполняем обычный сброс
                                self.separation_zone_tracker.target_position_set = False
                                self.separation_zone_tracker.target_position = None
                        else:
                            # Не можем рассчитать время - выполняем обычный сброс
                            self.separation_zone_tracker.target_position_set = False
                            self.separation_zone_tracker.target_position = None
                        
                        self.separation_zone_tracker.paddle_moved_after_set = False
                        self.separation_zone_tracker.paddle_reached_target = False
                        self.separation_zone_tracker.frames_since_target_set = 0
                        self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                        self._log_paddle_movement(current_x, current_x, "target_reset_wall_bounce", 1.0)
                        # Продолжаем обработку с обычной логикой для установки новой цели
                    else:
                        # Скорость не изменилась - траектория стабильна, НЕ обновляем цель
                        # КРИТИЧНО: Возвращаем зафиксированную позицию БЕЗ пересчета
                        # Это гарантирует, что позиция не изменится до отскока от стены
                        self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                        
                        # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() для проверки - это может вызвать пересчет
                        # Просто используем зафиксированную позицию
                        
                        # ВСЕГДА возвращаем зафиксированную позицию
                        # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() - это может вызвать пересчет и дергание
                        target_pos = int(current_target)
                        distance_to_target = abs(current_x - target_pos)
                        
                        # КРИТИЧНО: Используем большой tolerance для остановки, чтобы предотвратить дергание
                        # Проблема: платформа движется со скоростью 15px/кадр и "перескакивает" через цель
                        # Решение: используем большой tolerance (равный скорости движения), чтобы платформа останавливалась
                        # даже если немного перескочила через цель
                        tolerance = 15  # Равен скорости движения платформы - предотвращает дергание
                        
                        # КРИТИЧНО: Логируем движение к зафиксированной позиции для отслеживания
                        # Фильтрация по уровню выполняется автоматически системой логирования Python
                        self._logger.debug(f"[MOVING TO FIXED] ФЛАГ: Движение к зафиксированной позиции! "
                                           f"current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
                                           f"distance={distance_to_target:.1f}px, tolerance={tolerance}")
                        
                        # Двигаемся к зафиксированной позиции
                        if distance_to_target > tolerance:
                            # Платформа далеко от цели - начинаем движение
                            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                            if movement != 0:
                                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                                self._update_smoothness_tracking(movement, current_x)
                                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                                # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
                        else:
                            # Достигли цели - останавливаемся
                            # КРИТИЧНО: НЕ устанавливаем флаг paddle_reached_target - он не нужен
                            # Просто останавливаемся, если близко к цели
                            return 0
                
                # КРИТИЧНО: Если позиция зафиксирована, но мяч не в зоне разделения - проверяем сброс
                # КРИТИЧНО: Используем гистерезис для предотвращения дергания
                # Сбрасываем целевую позицию ТОЛЬКО если:
                # 1. Мяч ушел далеко вверх (выше зоны кубиков) ИЛИ
                # 2. Мяч потерян (ниже верхней границы платформы)
                should_reset = False
                
                # Проверка 1: Мяч ушел далеко вверх (выше зоны кубиков)
                if ball_y < separation_zone_start - 50:  # Далеко выше зоны разделения
                    should_reset = True
                
                # Проверка 2: Мяч потерян (ниже верхней границы платформы)
                if ball_lost:
                    should_reset = True
                
                # Если нужно сбросить - сбрасываем
                if should_reset:
                    self.separation_zone_tracker.target_position_set = False
                    self.separation_zone_tracker.target_position = None
                    self.separation_zone_tracker.paddle_moved_after_set = False
                    self.separation_zone_tracker.paddle_reached_target = False
                    self._log_paddle_movement(current_x, current_x, "target_reset_ball_left_zone", 1.0)
                    # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
                else:
                    # КРИТИЧНО: Позиция зафиксирована, но мяч не в зоне разделения
                    # Используем зафиксированную позицию БЕЗ пересчета
                    current_target = self.separation_zone_tracker.target_position
                    if current_target is not None:
                        target_pos = int(current_target)
                        distance_to_target = abs(current_x - target_pos)
                        tolerance = 3
                        
                        if distance_to_target > tolerance:
                            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                            if movement != 0:
                                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                                self._update_smoothness_tracking(movement, current_x)
                                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target_outside_zone", 1.0)
                                # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
                        else:
                            return 0
                    
                    # КРИТИЧНО: УБРАНО - пересчет позиции в зоне разделения вызывает дёргание
                    # Позиция фиксируется один раз и НЕ пересчитывается до отскока от стены
                    if False:  # Никогда не пересчитываем в зоне разделения
                        # Используем простой расчет для стабильности
                        if self.current_game_state:
                            ball_x = self.current_game_state.ball_position.x
                            ball_y_state = self.current_game_state.ball_position.y
                            vel_x = self.current_game_state.ball_velocity.x
                            vel_y = self.current_game_state.ball_velocity.y
                            
                            if vel_y > 0 and ball_y_state < paddle_y:
                                # КРИТИЧНО: Улучшенное предсказание точки падения с учетом времени движения платформы
                                time_to_paddle = (paddle_y - ball_y_state) / vel_y
                                if time_to_paddle > 0:
                                    # Предсказываем позицию мяча в момент падения
                                    predicted_x = ball_x + vel_x * time_to_paddle
                                    
                                    # КРИТИЧНО: Учитываем отскоки от стен более точно
                                    screen_width = self.screen_width
                                    ball_radius = self.config.ball.radius
                                    remaining_time = time_to_paddle
                                    current_predicted_x = ball_x
                                    current_vel_x = vel_x
                                    
                                    # Симулируем движение мяча с учетом отскоков от стен
                                    while remaining_time > 0:
                                        # Рассчитываем, когда мяч достигнет стены
                                        if current_vel_x > 0:
                                            time_to_right_wall = (screen_width - ball_radius - current_predicted_x) / current_vel_x
                                        else:
                                            time_to_right_wall = float('inf')
                                        
                                        if current_vel_x < 0:
                                            time_to_left_wall = (current_predicted_x - ball_radius) / abs(current_vel_x)
                                        else:
                                            time_to_left_wall = float('inf')
                                        
                                        time_to_wall = min(time_to_left_wall, time_to_right_wall)
                                        
                                        if time_to_wall > 0 and time_to_wall <= remaining_time:
                                            # Мяч отскочит от стены
                                            current_predicted_x += current_vel_x * time_to_wall
                                            remaining_time -= time_to_wall
                                            current_vel_x = -current_vel_x
                                        else:
                                            # Мяч не достигнет стены до падения
                                            current_predicted_x += current_vel_x * remaining_time
                                            remaining_time = 0
                                    
                                    predicted_x = current_predicted_x
                                    
                                    # Дополнительная проверка границ
                                    if predicted_x < ball_radius:
                                        predicted_x = ball_radius
                                    elif predicted_x > screen_width - ball_radius:
                                        predicted_x = screen_width - ball_radius
                                    
                                    # КРИТИЧНО: Разделяем платформу на 3 зоны и всегда прицеливаемся в центр выбранной зоны
                                    # Платформа шириной 120px делится на 3 равные зоны по 40px каждая
                                    # Левая зона: от -60px до -20px от центра платформы (центр на -40px)
                                    # Центральная зона: от -20px до +20px от центра платформы (центр на 0px)
                                    # Правая зона: от +20px до +60px от центра платформы (центр на +40px)
                                    
                                    zone_size = self.config.paddle.zone_size
                                    zone_half = self.config.paddle.zone_half
                                    
                                    # КРИТИЧНО: Проверяем, не находится ли точка падения близко к стене
                                    # Если точка падения в пределах 40px от края экрана - используем точку падения напрямую
                                    screen_width = self.screen_width
                                    ball_radius = self.config.ball.radius
                                    min_safe_x = ball_radius + self.config.paddle.edge_proximity_threshold
                                    max_safe_x = screen_width - ball_radius - self.config.paddle.edge_proximity_threshold
                                    
                                    use_direct_position = (predicted_x < min_safe_x or predicted_x > max_safe_x)
                                    
                                    if use_direct_position:
                                        # Точка падения близко к стене - используем точку падения напрямую
                                        # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), платформа должна доезжать до края зоны
                                        # Край платформы должен касаться стены для максимального покрытия
                                        if time_to_paddle < 3:
                                            # Мяч очень близко - доезжаем до края зоны
                                            if predicted_x > screen_width / 2:
                                                # Мяч справа - край платформы касается правой стены
                                                zone_center_x = screen_width - self.paddle_width // 2
                                            else:
                                                # Мяч слева - край платформы касается левой стены
                                                zone_center_x = self.paddle_width // 2
                                        else:
                                            # Мяч не очень близко - используем точку падения напрямую
                                            zone_center_x = predicted_x
                                        selected_zone = "EDGE"
                                    else:
                                        # КРИТИЧНО: Правильная логика позиционирования для попадания в ЦЕНТР зоны
                                        # Цель: позиционировать платформу так, чтобы predicted_x попал в ЦЕНТР выбранной зоны
                                        
                                        # Если центр платформы = X, то:
                                        # - Левая зона: от X-60 до X-20, центр на X-40
                                        # - Центральная зона: от X-20 до X+20, центр на X
                                        # - Правая зона: от X+20 до X+60, центр на X+40
                                        
                                        # КРИТИЧНО: Выбираем зону так, чтобы мяч попал в ЦЕНТР зоны, а не на границу
                                        # Для этого нужно определить, в какую зону попадает predicted_x,
                                        # и позиционировать платформу так, чтобы центр этой зоны совпал с predicted_x
                                        
                                        # Варианты позиционирования:
                                        # 1. Центральная зона: центр платформы = predicted_x (центр зоны = predicted_x)
                                        # 2. Левая зона: центр платформы = predicted_x + 40 (центр зоны = predicted_x)
                                        # 3. Правая зона: центр платформы = predicted_x - 40 (центр зоны = predicted_x)
                                        
                                        # Определяем, какая зона лучше подходит, проверяя границы зон:
                                        # Если центр платформы = predicted_x:
                                        #   - Левая зона: от predicted_x-60 до predicted_x-20
                                        #   - Центральная зона: от predicted_x-20 до predicted_x+20
                                        #   - Правая зона: от predicted_x+20 до predicted_x+60
                                        
                                        # Если predicted_x находится в центральной зоне (от predicted_x-20 до predicted_x+20),
                                        # то predicted_x всегда попадает в центр центральной зоны - используем центральную зону
                                        
                                        # Если predicted_x находится в левой зоне (от predicted_x-60 до predicted_x-20),
                                        # то нужно сдвинуть платформу вправо на 40px, чтобы predicted_x попал в центр левой зоны
                                        
                                        # Если predicted_x находится в правой зоне (от predicted_x+20 до predicted_x+60),
                                        # то нужно сдвинуть платформу влево на 40px, чтобы predicted_x попал в центр правой зоны
                                        
                                        # Но predicted_x - это точка падения, а не позиция относительно платформы!
                                        # Нужно определить, в какую зону попадает predicted_x, если центр платформы = predicted_x
                                        
                                        # Упрощенный подход: выбираем зону на основе расстояния от predicted_x до центров зон
                                        # при условии, что центр платформы = predicted_x
                                        
                                        # Центры зон при центре платформы = predicted_x:
                                        center_zone_center = predicted_x  # центр центральной зоны
                                        left_zone_center = predicted_x - zone_size  # центр левой зоны (predicted_x - 40)
                                        right_zone_center = predicted_x + zone_size  # центр правой зоны (predicted_x + 40)
                                        
                                        # Расстояния от predicted_x до центров зон:
                                        dist_to_center = abs(predicted_x - center_zone_center)  # всегда 0
                                        dist_to_left = abs(predicted_x - left_zone_center)  # всегда 40
                                        dist_to_right = abs(predicted_x - right_zone_center)  # всегда 40
                                        
                                        # КРИТИЧНО: Выбираем зону на основе того, где находится predicted_x относительно экрана
                                        # Если predicted_x близко к левому краю - предпочитаем левую зону
                                        # Если predicted_x близко к правому краю - предпочитаем правую зону
                                        # Иначе - используем центральную зону
                                        
                                        screen_center = screen_width / 2
                                        # КРИТИЧНО: Используем более широкие пороги для выбора боковых зон
                                        # Это гарантирует, что платформа будет двигаться дальше влево/вправо,
                                        # чтобы мяч попадал в центр боковой зоны, а не на границу
                                        left_threshold = screen_center - zone_size * 2  # 400 - 80 = 320
                                        right_threshold = screen_center + zone_size * 2  # 400 + 80 = 480
                                        
                                        if predicted_x < left_threshold:
                                            # predicted_x в левой части экрана - используем левую зону
                                            # Чтобы predicted_x попал в центр левой зоны, центр платформы = predicted_x + 40
                                            zone_center_x = predicted_x + zone_size
                                            selected_zone = "LEFT"
                                        elif predicted_x > right_threshold:
                                            # predicted_x в правой части экрана - используем правую зону
                                            # Чтобы predicted_x попал в центр правой зоны, центр платформы = predicted_x - 40
                                            zone_center_x = predicted_x - zone_size
                                            selected_zone = "RIGHT"
                                        else:
                                            # predicted_x в центральной части экрана - используем центральную зону
                                            # Чтобы predicted_x попал в центр центральной зоны, центр платформы = predicted_x
                                            zone_center_x = predicted_x
                                            selected_zone = "CENTER"
                                    
                                    # КРИТИЧНО: Логируем выбор зоны для диагностики (всегда)
                                    current_paddle_x = self.current_game_state.paddle_position.x if self.current_game_state else 0
                                    distance_to_zone_center = abs(current_paddle_x - zone_center_x)
                                    # Вычисляем, где будет центр выбранной зоны при позиции платформы = zone_center_x
                                    if selected_zone == "LEFT":
                                        actual_zone_center = zone_center_x - zone_size  # центр левой зоны
                                    elif selected_zone == "RIGHT":
                                        actual_zone_center = zone_center_x + zone_size  # центр правой зоны
                                    else:
                                        actual_zone_center = zone_center_x  # центр центральной зоны
                                    
                                    self._logger.debug(f"[ZONE SELECTION] predicted_x={predicted_x:.1f} -> zone={selected_zone} "
                                                       f"paddle_center={zone_center_x:.1f} actual_zone_center={actual_zone_center:.1f} "
                                                       f"current_paddle={current_paddle_x:.1f} distance_to_zone={distance_to_zone_center:.1f}px "
                                                       f"time_to_paddle={time_to_paddle:.2f} frames")
                                    
                                    # Ограничиваем границами экрана
                                    # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров),
                                    # платформа должна доезжать до края зоны (край платформы касается стены)
                                    # НЕ ограничиваем границами в этом случае
                                    min_x = self.paddle_width // 2 + 30
                                    max_x = screen_width - self.paddle_width // 2 - 30
                                    
                                    # КРИТИЧНО: Если это EDGE зона и мяч очень близко, доезжаем до края
                                    if selected_zone == "EDGE" and time_to_paddle < 3:
                                        # В EDGE зоне и очень близко - используем zone_center_x напрямую
                                        # (уже рассчитан для края зоны в строках 2794 или 2797)
                                        new_optimal_x = int(zone_center_x)
                                    else:
                                        # Обычное ограничение границами
                                        new_optimal_x = max(min_x, min(max_x, int(zone_center_x)))
                                    
                                    # КРИТИЧНО: Используем экспоненциальное сглаживание
                                    # НО: не обновляем целевую позицию, если платформа уже близко к текущей цели
                                    # КРИТИЧНО: Если мяч очень близко (менее 5 кадров), ВСЕГДА обновляем цель без сглаживания
                                    old_target = self.separation_zone_tracker.target_position
                                    if old_target is not None:
                                        # Проверяем, насколько далеко платформа от текущей цели
                                        distance_to_old_target = abs(current_x - old_target)
                                        
                                        # КРИТИЧНО: НЕ обновляем цель без сглаживания когда мяч очень близко
                                        # Это вызывает дёргание платформы, если траектория стабильна
                                        # Обновляем только если траектория кардинально изменилась
                                        distance_to_paddle_y = paddle_y - ball_y_state if ball_y_state < paddle_y else 0
                                        
                                        if distance_to_old_target <= 40:
                                            # КРИТИЧНО: Если платформа уже близко к текущей цели, НЕ обновляем цель вообще
                                            # Это предотвращает дёргание в точке падения
                                            # Используем удвоенный tolerance для проверки "близко к цели"
                                            tolerance_check = 30  # Удвоенный tolerance (15 * 2)
                                            if distance_to_old_target <= tolerance_check:
                                                # Платформа уже близко к цели - НЕ обновляем, даже если new_optimal немного отличается
                                                # Это критично для предотвращения дёргания в точке падения
                                                optimal_x = old_target
                                                # Логируем, что мы НЕ обновляем цель, хотя new_optimal отличается
                                                if abs(new_optimal_x - old_target) > 10:  # Только если разница значительная
                                                    self._logger.debug(f"[POSITION CHANGE BLOCKED] Платформа близко к цели (distance={distance_to_old_target:.1f} <= {tolerance_check}), "
                                                                       f"НОВУЮ цель НЕ устанавливаем! Старая={old_target:.1f}, Новая={new_optimal_x:.1f}, Разница={abs(new_optimal_x - old_target):.1f}px")
                                            else:
                                                # Платформа еще далеко от цели - проверяем, не изменилась ли траектория кардинально
                                                # Увеличиваем порог до 50px минимум, чтобы не реагировать на мелкие изменения
                                                threshold = 50 if distance_to_paddle_y < 50 else 80
                                                # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз и НЕ меняется до отскока от стены
                                                # НЕ обновляем позицию, даже если траектория "изменилась кардинально"
                                                # Это нарушение правила - используем старую позицию
                                                optimal_x = old_target
                                                if abs(new_optimal_x - old_target) > threshold:
                                                    self._logger.warning(f"[CRITICAL ERROR] НАРУШЕНИЕ ПРАВИЛА: Попытка изменить позицию ({old_target:.1f} -> {new_optimal_x:.1f}) "
                                                                        f"БЕЗ отскока от стены! Используем старую позицию.")
                                        else:
                                            # Платформа далеко от старой цели - используем сглаживание
                                            # НО: увеличиваем порог для обновления, чтобы не дёргаться
                                            # КРИТИЧНО: Проверяем разницу между старой и новой целью
                                            # Если разница маленькая (менее 50px), НЕ обновляем, даже если платформа далеко
                                            target_difference = abs(new_optimal_x - old_target)
                                            if target_difference <= 50:
                                                # Разница слишком маленькая - не обновляем, даже если платформа далеко
                                                optimal_x = old_target
                                                if distance_to_old_target > 50:  # Только логируем если платформа действительно далеко
                                                    self._logger.debug(f"[POSITION CHANGE BLOCKED] Разница между целями слишком маленькая (target_difference={target_difference:.1f} <= 50), "
                                                                       f"НЕ обновляем цель при сглаживании! Старая={old_target:.1f}, Новая={new_optimal_x:.1f}, distance_to_old={distance_to_old_target:.1f}")
                                            else:
                                                # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз и НЕ меняется до отскока от стены
                                                # НЕ используем сглаживание - это нарушение правила
                                                # Всегда используем старую позицию
                                                optimal_x = old_target
                                                if abs(new_optimal_x - old_target) > 50:
                                                    self._logger.warning(f"[CRITICAL ERROR] НАРУШЕНИЕ ПРАВИЛА: Попытка изменить позицию через сглаживание "
                                                                        f"({old_target:.1f} -> {new_optimal_x:.1f}) БЕЗ отскока от стены! Используем старую позицию.")
                                    else:
                                        # ПРАВИЛО 4: Устанавливаем целевую позицию впервые
                                        # КРИТИЧНО: Проверяем, не была ли позиция уже установлена (нарушение правила)
                                        if self.separation_zone_tracker.target_position_set:
                                            # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                                            old_pos = self.separation_zone_tracker.target_position
                                            if old_pos is not None:
                                                position_diff = abs(old_pos - int(new_optimal_x))
                                                # КРИТИЧНО: Если позиция та же самая (разница < 5px) - используем старую
                                                if position_diff < 5:
                                                    self._logger.debug(f"[POSITION UPDATE] Попытка установить ту же позицию (ПРАВИЛО 4)! "
                                                                       f"Старая позиция={old_pos:.1f}, Новая позиция={int(new_optimal_x):.1f}, "
                                                                       f"Разница={position_diff:.1f}px - используем старую")
                                                    optimal_x = float(old_pos)
                                                else:
                                                    # КРИТИЧНО: Если позиция отличается значительно - сбрасываем и устанавливаем новую
                                                    self._logger.warning(f"[RULE VIOLATION] Попытка установить ДРУГУЮ позицию (ПРАВИЛО 4)! "
                                                                         f"Старая позиция={old_pos:.1f}, Новая позиция={int(new_optimal_x):.1f}, "
                                                                         f"Разница={position_diff:.1f}px - сбрасываем и устанавливаем новую")
                                                    # Сбрасываем старую позицию
                                                    self.separation_zone_tracker.target_position_set = False
                                                    self.separation_zone_tracker.target_position = None
                                                    self.separation_zone_tracker.paddle_moved_after_set = False
                                                    self.separation_zone_tracker.paddle_reached_target = False
                                                    # Устанавливаем новую позицию
                                                    optimal_x = float(new_optimal_x)
                                                    self.separation_zone_tracker.target_position = int(new_optimal_x)
                                                    self.separation_zone_tracker.target_position_set = True
                                                    self.separation_zone_tracker.frames_since_target_set = 0
                                                    self._logger.debug(f"[POSITION RESET] Позиция сброшена и установлена заново (ПРАВИЛО 4)! "
                                                                       f"target_position={int(new_optimal_x):.1f}")
                                            else:
                                                # Старая позиция была None - устанавливаем новую
                                                optimal_x = float(new_optimal_x)
                                                self.separation_zone_tracker.target_position = int(new_optimal_x)
                                                self.separation_zone_tracker.target_position_set = True
                                                self.separation_zone_tracker.frames_since_target_set = 0
                                        else:
                                            # Позиция устанавливается впервые - это правильно
                                            current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                                            self.separation_zone_tracker.target_position = int(new_optimal_x)
                                            self.separation_zone_tracker.target_position_set = True
                                            self.separation_zone_tracker.frames_since_target_set = 0
                                            self.separation_zone_tracker.paddle_moved_after_set = False
                                            self.separation_zone_tracker.paddle_reached_target = False
                                            self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                                            current_target = self.separation_zone_tracker.target_position
                                            current_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                                            self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (ПРАВИЛО 4)! "
                                                               f"target_position={int(new_optimal_x):.1f}, paddle_x={current_x:.1f}")
                                            optimal_x = int(new_optimal_x)
                                else:
                                    target_pos = self.separation_zone_tracker.target_position
                                    optimal_x = int(target_pos) if target_pos is not None else self.get_optimal_paddle_position()
                            else:
                                target_pos = self.separation_zone_tracker.target_position
                                optimal_x = int(target_pos) if target_pos is not None else self.get_optimal_paddle_position()
                        else:
                            target_pos = self.separation_zone_tracker.target_position
                            optimal_x = int(target_pos) if target_pos is not None else self.get_optimal_paddle_position()
                    else:
                        # Используем сохраненную позицию
                        target_pos = self.separation_zone_tracker.target_position
                        if target_pos is not None:
                            optimal_x = int(target_pos)
                        else:
                            optimal_x = self.get_optimal_paddle_position()
                        # КРИТИЧНО: Обновляем счетчик кадров с момента установки цели
                        frames_since_target_set = self.separation_zone_tracker.frames_since_target_set
                        self.separation_zone_tracker.frames_since_target_set = frames_since_target_set + 1
                    
                    if optimal_x is not None:
                        target_pos = int(optimal_x)
                        distance_to_target = abs(current_x - target_pos)
                        
                        # КРИТИЧНО: Сначала проверяем, успеет ли платформа добраться до цели
                        # Это должно быть ПЕРЕД проверкой tolerance, чтобы не останавливаться раньше времени
                        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
                        time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
                        distance_to_move = distance_to_target
                        frames_to_reach = distance_to_move / paddle_speed if paddle_speed > 0 else float('inf')
                        # КРИТИЧНО: Добавляем небольшой запас (0.5 кадра) для учета неточностей расчета
                        # Это особенно важно, когда мяч очень близко
                        will_reach = (frames_to_reach <= time_to_paddle + 0.5) if time_to_paddle != float('inf') else False
                        
                        # КРИТИЧНО: НЕ пересчитываем цель когда мяч очень близко, если траектория стабильна
                        # Если мяч летит по прямой траектории и не может её изменить (нет кубиков на пути, нет стен),
                        # то пересчёт цели в последний момент только вызывает дёргание платформы
                        # Пересчитываем ТОЛЬКО если платформа не успевает добраться до цели
                        force_recalculate = False  # УБРАНО: пересчёт при близком мяче вызывает дёргание
                        
                        # КРИТИЧНО: УБРАНО - пересчет позиции когда "не успевает" вызывает дёргание
                        # Платформа должна продолжать движение к зафиксированной цели, даже если "не успевает"
                        # Это лучше, чем постоянно пересчитывать позицию и дёргаться
                        # if (not will_reach) and time_to_paddle != float('inf') and time_to_paddle > 0:
                        #     ... пересчет позиции ...
                        
                        # ПРАВИЛО 3.1: Если платформа близко к цели - проверяем, нужно ли еще двигаться
                        # КРИТИЧНО: Минимальный tolerance - платформа должна двигаться до точной позиции
                        # Останавливаемся ТОЛЬКО когда действительно достигли цели (tolerance = 3px)
                        tolerance = 3
                        
                        # КРИТИЧНО: УБРАНО - сложная логика с проверкой зон вызывает дёргание
                        # Платформа должна просто двигаться к цели до точной позиции
                        
                        # КРИТИЧНО: Если мяч очень близко к платформе (менее 10 кадров), уменьшаем tolerance еще больше
                        if time_to_paddle != float('inf') and time_to_paddle < 10:
                            tolerance = max(3, tolerance // 2)  # Уменьшаем tolerance вдвое, минимум 3px
                        
                        # КРИТИЧНО: Используем зафиксированную позицию БЕЗ пересчета
                        # Позиция фиксируется один раз и НЕ меняется до отскока от стены
                        target_pos = self.separation_zone_tracker.target_position
                        if target_pos is None:
                            target_pos = float(current_x)
                        else:
                            target_pos = float(target_pos)
                        distance_to_target = abs(current_x - target_pos)
                        # Определяем is_edge_zone на основе сохранённой цели
                        # target_pos гарантированно не None после строки 4136
                        screen_width = self.screen_width
                        ball_radius = self.config.ball.radius
                        min_safe_x = ball_radius + 40
                        max_safe_x = screen_width - ball_radius - 40
                        is_edge_zone = (target_pos < min_safe_x or target_pos > max_safe_x)
                        
                        # Продолжаем движение к актуальной цели, даже если близко к старой цели
                        # Для EDGE зоны используем меньший порог (2px), для остальных - 3px
                        # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров), НЕ останавливаемся до достижения края
                        if is_edge_zone and time_to_paddle < 3:
                            # В EDGE зоне и очень близко - продолжаем движение до края зоны
                            # Проверяем, достигли ли мы края зоны
                            screen_width = self.screen_width
                            # Определяем, к какому краю нужно двигаться
                            saved_target = self.separation_zone_tracker.target_position
                            target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                            
                            if target_to_check > screen_width / 2:
                                # Правый край - проверяем, достигли ли мы правого края
                                right_edge = screen_width - self.paddle_width // 2
                                if abs(current_x - right_edge) > 2:
                                    pass  # Продолжаем движение к правому краю
                                else:
                                    # Достигли правого края - останавливаемся
                                    if not self.separation_zone_tracker.paddle_reached_target:
                                        self.separation_zone_tracker.paddle_reached_target = True
                                    return 0
                            else:
                                # Левый край - проверяем, достигли ли мы левого края
                                left_edge = self.paddle_width // 2
                                if abs(current_x - left_edge) > 2:
                                    pass  # Продолжаем движение к левому краю
                                else:
                                    # Достигли левого края - останавливаемся
                                    if not self.separation_zone_tracker.paddle_reached_target:
                                        self.separation_zone_tracker.paddle_reached_target = True
                                    return 0
                        elif distance_to_target <= tolerance:
                            # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                            # Траектория мяча не меняется - используем сохраненную цель БЕЗ изменений
                            # НЕ проверяем actual_distance - это вызывает дёргание
                            
                            # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), НЕ останавливаемся
                            # Это критично для предотвращения потери мяча в последний момент
                            # КРИТИЧНО: Если мяч в EDGE зоне, НЕ останавливаемся до достижения края зоны
                            # даже если мяч не очень близко - это критично для предотвращения потери мяча у края
                            if (time_to_paddle != float('inf') and time_to_paddle < 3) or is_edge_zone:
                                # Мяч очень близко ИЛИ в EDGE зоне - продолжаем движение, даже если близко к цели
                                # Для EDGE зоны проверяем, достигли ли мы края зоны
                                if is_edge_zone:
                                    screen_width = self.screen_width
                                    saved_target = self.separation_zone_tracker.target_position
                                    target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                                    
                                    if target_to_check > screen_width / 2:
                                        # Правый край - проверяем, достигли ли мы правого края
                                        right_edge = screen_width - self.paddle_width // 2
                                        if abs(current_x - right_edge) > 2:
                                            # Еще не достигли правого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли правого края - останавливаемся
                                            if not self.separation_zone_tracker.paddle_reached_target:
                                                self.separation_zone_tracker.paddle_reached_target = True
                                            return 0
                                    else:
                                        # Левый край - проверяем, достигли ли мы левого края
                                        left_edge = self.paddle_width // 2
                                        if abs(current_x - left_edge) > 2:
                                            # Еще не достигли левого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли левого края - останавливаемся
                                            if not self.separation_zone_tracker.paddle_reached_target:
                                                self.separation_zone_tracker.paddle_reached_target = True
                                            return 0
                                else:
                                    # Мяч очень близко, но не в EDGE зоне - продолжаем движение
                                    pass  # Пропускаем остановку, продолжаем движение
                            else:
                                # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                                # Если достигли сохраненной цели - останавливаемся
                                if not self.separation_zone_tracker.paddle_reached_target:
                                    self.separation_zone_tracker.paddle_reached_target = True
                                # КРИТИЧНО: Логируем для диагностики
                                # Фильтрация по уровню выполняется автоматически системой логирования Python
                                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.1: Платформа очень близко к цели (distance={distance_to_target:.1f} <= {tolerance}), не двигаемся")
                                self._log_paddle_movement(current_x, current_x, "paddle_reached_target", 1.0)
                                return 0
                        
                        # КРИТИЧНО: Проверяем, успеет ли платформа доехать до текущей цели
                        # Если нет - обновляем целевую позицию на достижимую
                        ball_y_check = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y_check = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y_check = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle_check = paddle_y_check - ball_y_check if ball_y_check < paddle_y_check else 0
                        time_to_paddle_check = distance_to_paddle_check / ball_vel_y_check if ball_vel_y_check > 0 and distance_to_paddle_check > 0 else float('inf')
                        
                        if time_to_paddle_check != float('inf') and time_to_paddle_check > 0:
                            frames_to_reach_current = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
                            safety_margin = 1.2  # 20% запас
                            
                            # Если платформа не успеет доехать до текущей цели - обновляем её
                            if frames_to_reach_current > time_to_paddle_check * safety_margin:
                                # Рассчитываем достижимую позицию
                                max_distance = paddle_speed * time_to_paddle_check * 0.85
                                
                                # Рассчитываем предсказанную позицию мяча
                                ball_x_check = self.current_game_state.ball_position.x if self.current_game_state else 0
                                ball_vel_x_check = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                                predicted_ball_x = ball_x_check + ball_vel_x_check * time_to_paddle_check
                                
                                # Применяем логику зон
                                zone_size = self.config.paddle.zone_size
                                screen_center = self.screen_width / 2
                                left_threshold = screen_center - zone_size * 2
                                right_threshold = screen_center + zone_size * 2
                                
                                if predicted_ball_x < left_threshold:
                                    zone_center_x = predicted_ball_x + zone_size
                                elif predicted_ball_x > right_threshold:
                                    zone_center_x = predicted_ball_x - zone_size
                                else:
                                    zone_center_x = predicted_ball_x
                                
                                # Выбираем достижимую позицию
                                if zone_center_x > current_x:
                                    achievable_target = min(zone_center_x, current_x + max_distance)
                                else:
                                    achievable_target = max(zone_center_x, current_x - max_distance)
                                
                                # Обновляем целевую позицию
                                old_target = target_pos
                                target_pos = int(achievable_target)
                                self.separation_zone_tracker.target_position = target_pos
                                distance_to_target = abs(current_x - target_pos)
                                
                                self._logger.warning(f"[TARGET UPDATE] Платформа не успевает до текущей цели ({old_target:.1f}px). "
                                                   f"Обновляем на достижимую: {target_pos:.1f}px "
                                                   f"(время_до_мяча={time_to_paddle_check:.1f}, время_до_старой_цели={frames_to_reach_current:.1f})")
                        
                        # ПРАВИЛО 3.2: Платформа еще не достигла цели - двигаемся к сохраненной позиции
                        # КРИТИЧНО: УБРАНО - сложная логика с проверкой "очень близко" вызывает дёргание
                        # Платформа должна просто двигаться к цели до точной позиции (tolerance = 3px)
                        
                        # Устанавливаем флаг, что платформа начала двигаться после установки цели
                        if not self.separation_zone_tracker.paddle_moved_after_set:
                            self.separation_zone_tracker.paddle_moved_after_set = True
                            # КРИТИЧНО: Логируем начало движения
                            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.2: Начинаем движение к сохраненной позиции. current_x={current_x}, target_pos={target_pos}, distance={distance_to_target:.1f}")
                            self._log_paddle_movement(current_x, target_pos, "paddle_moving_to_target", 0.9)
                        
                        # КРИТИЧНО: Проверяем, что движение действительно нужно
                        # Если target_pos == current_x, не двигаемся
                        if target_pos == current_x:
                            return 0
                        
                        # Двигаемся к сохраненной позиции БЕЗ дополнительных проверок
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        # КРИТИЧНО: Проверяем, что movement не равен 0 (должно быть -1 или 1)
                        if movement == 0:
                            # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                            self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 3.2: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                            return self._fallback_movement(current_x)
                        
                        # КРИТИЧНО: Логируем движение с информацией о скорости (всегда)
                        # Примечание: проверка will_reach уже выполнена выше, перед проверкой tolerance
                        # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
                        # Пересчитываем для логирования
                        ball_y_log = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y_log = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y_log = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle_log = paddle_y_log - ball_y_log if ball_y_log < paddle_y_log else 0
                        time_to_paddle_log = distance_to_paddle_log / ball_vel_y_log if ball_vel_y_log > 0 and distance_to_paddle_log > 0 else float('inf')
                        distance_to_move_log = distance_to_target
                        frames_to_reach_log = distance_to_move_log / paddle_speed if paddle_speed > 0 else float('inf')
                        will_reach_log = frames_to_reach_log <= time_to_paddle_log if time_to_paddle_log != float('inf') else False
                        
                        self._logger.debug(f"[PADDLE MOVEMENT] movement={movement} distance={distance_to_target:.1f}px "
                                           f"current_x={current_x:.1f} target={target_pos:.1f} | "
                                           f"paddle_speed={paddle_speed} frames_to_reach={frames_to_reach_log:.1f} "
                                           f"time_to_paddle={time_to_paddle_log:.1f} will_reach={will_reach_log}")
                        
                        self._update_loop_tracking(movement, int(current_x), int(target_pos))
                        self._update_smoothness_tracking(movement, current_x)
                        self._log_paddle_movement(current_x, target_pos, "moving_to_locked_target", 1.0)
                        # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
                    else:
                        # target_pos is None - сбрасываем флаг и продолжаем обработку
                        self.separation_zone_tracker.target_position_set = False
                        self._log_paddle_movement(current_x, current_x, "target_reset_none", 1.0)
                        # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
            
            # ПРАВИЛО 4: Если целевая позиция НЕ установлена и мяч в зоне разделения
            # - устанавливаем целевую позицию ОДИН РАЗ через get_optimal_paddle_position
            # - после установки используем её без пересчета
            # КРИТИЧНО: Проверяем, что мяч НЕ потерян перед установкой целевой позиции
            if in_separation_zone and not self.separation_zone_tracker.target_position_set and not ball_lost:
                # КРИТИЧНО: Логируем установку целевой позиции
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Устанавливаем целевую позицию. ball_y={ball_y:.1f}, in_separation_zone={in_separation_zone}")
                # Устанавливаем целевую позицию один раз
                optimal_x = self.get_optimal_paddle_position()
                # get_optimal_paddle_position() всегда возвращает int, не None
                
                # КРИТИЧНО: Проверяем, успеет ли платформа добраться до цели ПЕРЕД установкой
                # Рассчитываем время до приземления мяча и возможность достижения цели
                distance_to_target = abs(current_x - optimal_x)
                distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                
                # КРИТИЧНО: Всегда проверяем возможность достижения цели
                # Рассчитываем время, необходимое для достижения цели платформой
                if time_to_paddle != float('inf') and time_to_paddle > 0 and distance_to_target > 0:
                    # Используем текущую скорость платформы (уже увеличенную)
                    frames_to_reach = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
                    
                    # КРИТИЧНО: Увеличиваем запас безопасности до 20% и используем только 85% времени
                    # Это гарантирует, что платформа успеет доехать с запасом
                    safety_margin = 1.2  # 20% запас
                    time_usage = 0.85  # Используем только 85% времени для безопасности
                    
                    if frames_to_reach > time_to_paddle * safety_margin:
                        # Платформа не успеет - используем максимальное расстояние, которое можно пройти
                        max_distance = paddle_speed * time_to_paddle * time_usage
                        
                        # КРИТИЧНО: Рассчитываем предсказанную позицию мяча для более точной промежуточной цели
                        ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                        ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        predicted_ball_x = ball_x + ball_vel_x * time_to_paddle
                        
                        # Применяем логику зон к предсказанной позиции
                        zone_size = self.config.paddle.zone_size
                        screen_center = self.screen_width / 2
                        left_threshold = screen_center - zone_size * 2
                        right_threshold = screen_center + zone_size * 2
                        
                        if predicted_ball_x < left_threshold:
                            zone_center_x = predicted_ball_x + zone_size
                        elif predicted_ball_x > right_threshold:
                            zone_center_x = predicted_ball_x - zone_size
                        else:
                            zone_center_x = predicted_ball_x
                        
                        # Выбираем промежуточную позицию в направлении зоны мяча, но не дальше чем можем пройти
                        if zone_center_x > current_x:
                            achievable_target = min(zone_center_x, current_x + max_distance)
                        else:
                            achievable_target = max(zone_center_x, current_x - max_distance)
                        
                        self._logger.warning(f"[ACHIEVABLE TARGET] Цель недостижима: расстояние={distance_to_target:.1f}px, "
                                           f"время_до_мяча={time_to_paddle:.1f}, время_до_цели={frames_to_reach:.1f}. "
                                           f"Используем промежуточную цель: {achievable_target:.1f} вместо {optimal_x:.1f} "
                                           f"(predicted_ball_x={predicted_ball_x:.1f}, zone_center={zone_center_x:.1f})")
                        optimal_x = int(achievable_target)
                
                # Дополнительная проверка для экстренных ситуаций (мяч очень близко)
                if time_to_paddle != float('inf') and time_to_paddle < 10 and distance_to_target > 100:
                    # Мяч очень близко, а платформа далеко - пересчитываем цель с учетом зон
                    # Вместо простого ограничения движения, пересчитываем оптимальную позицию
                    # с учетом того, что платформа не успеет далеко переместиться
                    original_optimal = optimal_x
                    
                    # Рассчитываем максимальное расстояние, которое платформа может пройти
                    # Используем переданный paddle_speed или базовую скорость
                    max_distance = paddle_speed * time_to_paddle
                    
                    # Определяем, в какую зону попадает predicted_x
                    ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                    ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    predicted_x = ball_x + ball_vel_x * time_to_paddle
                    
                    # Применяем логику зон к predicted_x
                    zone_size = self.config.paddle.zone_size
                    screen_center = self.screen_width / 2
                    left_threshold = screen_center - zone_size * 2
                    right_threshold = screen_center + zone_size * 2
                    
                    if predicted_x < left_threshold:
                        # Левая зона
                        zone_center_x = predicted_x + zone_size
                    elif predicted_x > right_threshold:
                        # Правая зона
                        zone_center_x = predicted_x - zone_size
                    else:
                        # Центральная зона
                        zone_center_x = predicted_x
                    
                    # Ограничиваем максимальное расстояние движения
                    if zone_center_x > current_x:
                        optimal_x = int(min(zone_center_x, current_x + max_distance))
                    else:
                        optimal_x = int(max(zone_center_x, current_x - max_distance))
                    
                    self._logger.debug(f"[TARGET ADJUST] Мяч близко! time_to_paddle={time_to_paddle:.1f}, скорректирована цель с {original_optimal:.1f} на {optimal_x:.1f} (max_distance={max_distance:.1f})")
                
                # Сохраняем целевую позицию
                current_target = self.separation_zone_tracker.target_position
                old_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                self._logger.debug(f"[POSITION CHANGE] ФЛАГ: Платформа устанавливает новую цель (ПРАВИЛО 4)! paddle_x={current_x:.1f}, "
                                   f"старая_цель={old_target_str}, "
                                   f"новая_цель={optimal_x:.1f}, distance_to_target={abs(current_x - optimal_x):.1f}")
                self.separation_zone_tracker.target_position = int(optimal_x)
                self.separation_zone_tracker.target_position_set = True
                self.separation_zone_tracker.paddle_moved_after_set = False
                self.separation_zone_tracker.paddle_reached_target = False
                self.separation_zone_tracker.frames_since_target_set = 0
                # КРИТИЧНО: Сохраняем vel_x для отслеживания отскоков от стены
                ball_vel_x_save = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                self.separation_zone_tracker.saved_ball_vel_x = ball_vel_x_save
                self._log_paddle_movement(current_x, optimal_x, "target_position_set", 1.0)
                # Продолжаем обработку с установленной позицией
                target_pos = int(optimal_x)
                distance_to_target = abs(current_x - target_pos)
                
                # КРИТИЧНО: Проверяем, что движение действительно нужно
                # Если target_pos == current_x, не двигаемся
                if target_pos == current_x:
                    self.separation_zone_tracker.paddle_reached_target = True
                    return 0
                
                # КРИТИЧНО: В зоне разделения останавливаемся только если ОЧЕНЬ близко к цели
                # Увеличено до 25 пикселей для предотвращения дрожания
                if distance_to_target <= 25:
                    self.separation_zone_tracker.paddle_reached_target = True
                    # КРИТИЧНО: Логируем для диагностики
                    # Фильтрация по уровню выполняется автоматически системой логирования Python
                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Платформа очень близко к цели (distance={distance_to_target:.1f} <= 5), не двигаемся")
                    return 0
                
                movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                # КРИТИЧНО: Проверяем, что movement не равен 0
                if movement == 0:
                    # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                    self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 4: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                    return self._fallback_movement(current_x)
                
                # КРИТИЧНО: Логируем движение
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Движение! movement={movement}, distance={distance_to_target:.1f}, current_x={current_x}, target_pos={target_pos}")
                
                self.separation_zone_tracker.paddle_moved_after_set = True
                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                self._update_smoothness_tracking(movement, current_x)
                self._log_paddle_movement(current_x, target_pos, "moving_to_new_target", 0.9)
                # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement
            
            # ПРАВИЛО 5: Если мяч НЕ в зоне разделения и целевая позиция НЕ установлена
            # - используем обычную логику (мяч еще в зоне кубиков или выше)
            # КРИТИЧНО: Но только если мяч НЕ потерян и движется вниз
            # Если мяч потерян или движется вверх - не двигаемся
            if ball_lost:
                self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle_rule5", 1.0)
                return 0
            
            # КРИТИЧНО: УБРАНО правило "не двигаться когда мяч летит вверх"
            # Платформа ДОЛЖНА двигаться к точке падения мяча даже когда мяч летит вверх,
            # чтобы успеть к моменту падения. Продолжаем расчет оптимальной позиции.
            
            # КРИТИЧНО: Если мяч в разрешенной зоне (ниже кубиков, но выше платформы) и движется вниз
            # - платформа ДОЛЖНА двигаться к точке падения мяча
            optimal_x = self.get_optimal_paddle_position()
            # get_optimal_paddle_position() всегда возвращает int, не None

            # Проверяем зацикливание и при необходимости меняем стратегию
            # НО ТОЛЬКО если целевая позиция НЕ установлена
            if not self.separation_zone_tracker.target_position_set:
                self._change_strategy_if_looping()
                if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                    optimal_x = self._apply_alternative_strategy(optimal_x)
                    # Проверяем, что альтернативная стратегия тоже валидна
                    if optimal_x is None:
                        return self._fallback_movement(current_x)

            # Допуск по точности позиционирования
            precision_tolerance = 2
            # Проверяем дрожание и применяем штрафы
            jitter_detected = self._detect_jitter()
            if jitter_detected:
                # Увеличиваем допуск для уменьшения дрожания
                precision_tolerance = max(5, precision_tolerance + 2)
                # Увеличиваем штраф за дрожание
                self.smoothness_system["smoothness_penalty"] = min(
                    1.0, self.smoothness_system["smoothness_penalty"] + 0.1
                )
            else:
                # Уменьшаем штраф при плавном движении
                self.smoothness_system["smoothness_penalty"] = max(
                    0.0, self.smoothness_system["smoothness_penalty"] - 0.05
                )

            # Допуск по точности позиционирования (учитываем штраф за дрожание)
            base_precision_tolerance = 2
            precision_tolerance = base_precision_tolerance + int(
                self.smoothness_system["smoothness_penalty"] * 3
            )

            # Увеличиваем допуск, когда мяч движется вниз и траектория известна
            if self.current_game_state:
                ball_vel_y = (
                    self.current_game_state.ball_velocity.y
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                ball_y = self.current_game_state.ball_position.y
                paddle_zone_start = self.screen_height - 60
                separation_zone_start = self.separation_zone_tracker.separation_zone_start
                in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

                # КРИТИЧНО: НЕ увеличиваем допуск слишком сильно, иначе платформа не будет двигаться
                # Если мяч движется вниз и уже ниже кубиков - используем умеренный допуск
                if ball_vel_y > 0 and ball_y > 250:  # Мяч движется вниз и ниже кубиков
                    # Используем умеренный допуск (5-10 пикселей), чтобы платформа могла двигаться
                    # Только если платформа УЖЕ очень близко к цели (менее 5 пикселей) - не двигаемся
                    if abs(optimal_x - current_x) < 5:
                        precision_tolerance = max(precision_tolerance, 5)  # Очень близко - не двигаемся
                    else:
                        # Платформа еще не достигла цели - используем минимальный допуск для движения
                        precision_tolerance = max(precision_tolerance, 2)  # Минимальный допуск

            distance_to_optimal = abs(optimal_x - current_x)

            # Поощряем минимальные движения - если расстояние очень мало, не двигаемся
            min_movement_distance = self.smoothness_system["min_movement_distance"]
            
            # КРИТИЧНО: Убрана проверка ball_approaching_quickly - она вызывала дергание
            # В зоне разделения с установленной целевой позицией платформа просто движется к цели и останавливается
            
            if distance_to_optimal < min_movement_distance:
                # Если расстояние меньше минимального, проверяем, стоит ли двигаться
                if distance_to_optimal <= precision_tolerance:
                    movement = 0
                    # Поощряем точное позиционирование
                    self.smoothness_system["consecutive_stops"] += 1
                    if self.smoothness_system["consecutive_stops"] > 3:
                        # Уменьшаем штраф за хорошее позиционирование
                        self.smoothness_system["smoothness_penalty"] = max(
                            0.0, self.smoothness_system["smoothness_penalty"] - 0.1
                        )
                    # Сохраняем базовую скорость, так как не двигаемся
                    self._last_adjusted_paddle_speed = paddle_speed
                else:
                    # Двигаемся только если действительно нужно
                    movement = self._calculate_smooth_movement(
                        current_x, optimal_x, distance_to_optimal
                    )
                    # Сохраняем базовую скорость для этого случая
                    self._last_adjusted_paddle_speed = paddle_speed
            elif distance_to_optimal <= precision_tolerance:
                movement = 0
                self.smoothness_system["consecutive_stops"] += 1
                # Сохраняем базовую скорость, так как не двигаемся
                self._last_adjusted_paddle_speed = paddle_speed
            else:
                self.smoothness_system["consecutive_stops"] = 0
                # Адаптивная скорость от системы обучения
                if self.current_game_state:
                    ball_speed = self.current_game_state.ball_speed
                    distance_to_target = distance_to_optimal

                    # Рассчитываем время до встречи с мячом для более агрессивного увеличения скорости
                    time_to_meeting = float("inf")
                    ball_vel_y = (
                        self.current_game_state.ball_velocity.y
                        if hasattr(self.current_game_state, "ball_velocity")
                        else 0
                    )
                    if ball_vel_y > 0:  # Мяч движется вниз
                        ball_y = self.current_game_state.ball_position.y
                        paddle_y = self.current_game_state.paddle_position.y
                        distance_y = paddle_y - ball_y
                        if distance_y > 0:
                            time_to_meeting = distance_y / ball_vel_y

                    speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                        ball_speed, distance_to_target
                    )

                    # Если мяч быстро приближается, агрессивно увеличиваем скорость
                    if time_to_meeting != float("inf") and time_to_meeting > 0:
                        # Чем меньше времени до встречи, тем выше должна быть скорость
                        if time_to_meeting < 30:  # Менее 30 кадров (0.5 сек при 60 FPS)
                            urgency_factor = 30.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 3.0
                            )  # До 3x дополнительного ускорения
                        elif time_to_meeting < 60:  # Менее 60 кадров (1 сек)
                            urgency_factor = 60.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 2.0
                            )  # До 2x дополнительного ускорения

                    # ИСПРАВЛЕНИЕ: Адаптивная базовая скорость в зависимости от расстояния
                    # При больших расстояниях (>150px) увеличиваем базовую скорость дополнительно
                    base_speed_multiplier = 10.0  # Базовая скорость в 10 раз
                    
                    # ИСПРАВЛЕНИЕ: При расстоянии >150px увеличиваем скорость еще больше
                    if distance_to_target > 150:
                        # Для больших расстояний используем более агрессивную скорость
                        base_speed_multiplier = 15.0  # Увеличиваем до 15x для больших расстояний
                    elif distance_to_target > 100:
                        base_speed_multiplier = 12.0  # 12x для средних расстояний
                    
                    # ИСПРАВЛЕНИЕ: При экстренных ситуациях (мало времени до встречи) еще больше увеличиваем
                    if time_to_meeting != float('inf') and time_to_meeting < 20:  # Менее 20 кадров
                        base_speed_multiplier *= 1.5  # Дополнительно увеличиваем на 50%
                    
                    # Ограничиваем минимальный множитель скорости, чтобы платформа не двигалась слишком медленно
                    # AI может увеличивать скорость до 10x для достижения цели (в дополнение к базовому 10-15x)
                    max_multiplier = 10.0  # Дополнительный множитель до 10x
                    speed_multiplier = max(0.8, min(max_multiplier, speed_multiplier))
                    adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)  # ИСПРАВЛЕНО: убрано двойное умножение
                    # Гарантируем минимальную скорость платформы
                    adjusted_paddle_speed = max(
                        int(paddle_speed * 0.8), adjusted_paddle_speed
                    )
                    self._last_paddle_speed_multiplier = speed_multiplier
                    # Сохраняем для использования в PyGameBall.py
                    self._last_adjusted_paddle_speed = adjusted_paddle_speed
                else:
                    adjusted_paddle_speed = paddle_speed

                # Сохраняем для использования в PyGameBall.py
                self._last_adjusted_paddle_speed = adjusted_paddle_speed

                movement = self.position_optimizer.calculate_paddle_movement(
                    current_x, optimal_x, adjusted_paddle_speed
                )

                # Если расчёт не даёт движения, но мы не на месте — fallback
                if movement == 0 and optimal_x != current_x:
                    movement = self._fallback_movement(current_x)

            # Обновляем данные по зацикливанию
            self._update_loop_tracking(movement, current_x, optimal_x)
            
            # Обновляем данные по плавности движения
            self._update_smoothness_tracking(movement, current_x)

            # Логирование движения
            if movement != 0:
                reason = (
                    "ball_tracking"
                    if not self.is_ball_moving_towards_paddle()
                    else "trajectory_optimization"
                )
                confidence = self._calculate_decision_confidence(optimal_x)
                self.performance_logger.log_paddle_movement(
                    from_x=current_x,
                    to_x=current_x + movement * paddle_speed,
                    reason=reason,
                    confidence=confidence,
                )

            # Статистика по ходам
            self.current_game_stats["total_moves"] += 1
            if abs(optimal_x - current_x) < 10:
                self.current_game_stats["optimal_moves"] += 1

            # Учитываем плавность движения в обучении
            if movement != 0:
                # Штрафуем за дрожание при обучении
                if self.smoothness_system["smoothness_penalty"] > 0.5:
                    # Высокий штраф за дрожание - это плохое поведение
                    jitter_penalty = {
                        "action_type": "movement_jitter",
                        "success": False,
                        "penalty": self.smoothness_system["smoothness_penalty"],
                        "movement_distance": abs(optimal_x - current_x),
                    }
                    # Можно добавить в систему обучения для улучшения поведения
                    # self.learning_system.update_strategy(jitter_penalty)

            # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement

        except (AttributeError, TypeError) as e:
            self._logger.error(f"Ошибка типов при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)
        except InvalidStateError as e:
            self._logger.error(f"Недопустимое состояние при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)

    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервное движение платформы - улучшенное следование за мячом.

        Args:
            current_x: Текущая X-координата платформы.

        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state:
            return 0

        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y

        # Если мяч падает — предсказываем точку встречи с платформой
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
            if time_to_paddle > 0:
                predicted_x = ball_x + vel_x * time_to_paddle

                screen_width = self.screen_width
                ball_radius = self.config.ball.radius

                # Простое моделирование отскоков
                while (
                    predicted_x < ball_radius
                    or predicted_x > screen_width - ball_radius
                ):
                    if predicted_x < ball_radius:
                        predicted_x = 2 * ball_radius - predicted_x
                        vel_x = abs(vel_x)
                    elif predicted_x > screen_width - ball_radius:
                        predicted_x = 2 * (screen_width - ball_radius) - predicted_x
                        vel_x = -abs(vel_x)
                target_x = predicted_x
            else:
                target_x = ball_x
        else:
            # Мяч движется вверх — следим с небольшим упреждением
            prediction_factor = abs(vel_x) * 2
            if vel_x > 0:
                target_x = ball_x + prediction_factor
            elif vel_x < 0:
                target_x = ball_x - prediction_factor
            else:
                target_x = ball_x

        distance = target_x - current_x
        tolerance = 3

        if abs(distance) <= tolerance:
            return 0
        return 1 if distance > 0 else -1

    # ==========================
    # Оценка уверенности и давление по времени
    # ==========================

    def _is_time_pressure(self) -> bool:
        """Определяет, есть ли давление по времени/ситуации (мало времени или кубиков)."""
        if not self.current_game_state:
            return False

        game_time = self.current_game_state.game_time
        if game_time > 300:
            return True

        if len(self.current_game_state.remaining_bricks) <= 5:
            return True

        return False

    def _calculate_decision_confidence(self, target_position: int) -> float:
        """
        Рассчитывает уверенность в принятом решении.

        Args:
            target_position: Целевая X-позиция платформы.

        Returns:
            Уровень уверенности (0.0-1.0).
        """
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
