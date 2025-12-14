"""
Двигатель движения платформы.

Отвечает за управление движением платформы с учетом:
- Предсказания траектории мяча
- Оптимизации позиции
- Предотвращения зацикливания
- Плавности движения
"""

import time
import math
import random
from typing import List, Optional, Dict, Any

from ..game_state import GameState, Point
from ..config import AIConfig
from ..exceptions import InvalidStateError, PredictionError, LearningError, DataError
from ..prediction.trajectory_engine import TrajectoryEngine
from ..prediction.collision_detector import CollisionDetector
from ..learning.pattern_analyzer import PatternAnalyzer
from ..learning.strategy_optimizer import StrategyOptimizer
from ..performance_logger import PerformanceLogger


class MovementEngine:
    """
    Двигатель движения платформы.
    
    Отвечает за управление движением платформы с учетом:
    - Предсказания траектории мяча
    - Оптимизации позиции
    - Предотвращения зацикливания
    - Плавности движения
    """

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        config: AIConfig,
        trajectory_engine: TrajectoryEngine,
        collision_detector: CollisionDetector,
        pattern_analyzer: PatternAnalyzer,
        strategy_optimizer: StrategyOptimizer,
        performance_logger: PerformanceLogger,
        logger,
    ):
        """
        Инициализация MovementEngine.
        
        Args:
            screen_width: Ширина игрового экрана.
            screen_height: Высота игрового экрана.
            config: Конфигурация AI.
            trajectory_engine: Двигатель предсказания траекторий.
            collision_detector: Детектор столкновений.
            pattern_analyzer: Анализатор паттернов.
            strategy_optimizer: Оптимизатор стратегий.
            performance_logger: Логгер производительности.
            logger: Логгер для отладки.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = config
        self.trajectory_engine = trajectory_engine
        self.collision_detector = collision_detector
        self.pattern_analyzer = pattern_analyzer
        self.strategy_optimizer = strategy_optimizer
        self.performance_logger = performance_logger
        self._logger = logger
        
        # Состояние движения
        self.current_game_state: Optional[GameState] = None
        self.is_active = False
        
        # Система предотвращения зацикливания
        self.loop_prevention_system: Dict[str, Any] = {
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
        
        # Система отслеживания плавности движения
        self.smoothness_system: Dict[str, Any] = {
            "recent_movements": [],
            "recent_positions": [],
            "movement_changes": [],
            "jitter_threshold": 3,
            "jitter_window": 8,
            "min_movement_distance": self.config.paddle.min_movement_distance,
            "smoothness_penalty": 0.0,
            "consecutive_stops": 0,
        }
        
        # Отслеживание отбитий в пустоту
        self.empty_bounce_tracker: Dict[str, Any] = {
            "consecutive_empty_bounces": 0,
            "last_bounce_position": None,
            "last_bounce_time": 0,
            "max_empty_bounces": 1,
            "bounce_history": [],
            "ceiling_bounces": 0,
        }
        
        # Отслеживание зоны разделения
        self.separation_zone_tracker = self._create_separation_zone_tracker()
        
        # Последняя скорректированная скорость платформы
        self._last_adjusted_paddle_speed: Optional[int] = None
        self._last_paddle_speed_multiplier = 1.0
        
        # Отслеживание предыдущей позиции и скорости мяча
        self._last_ball_position: Optional[Point] = None
        self._last_ball_velocity: Optional[Point] = None
        
    def _create_separation_zone_tracker(self):
        """Создает трекер зоны разделения."""
        return {
            "ball_entered_separation_zone": False,
            "target_position_set": False,
            "target_position": None,
            "separation_zone_start": self.config.zones.separation_zone_start,
            "paddle_zone_start": self.config.zones.paddle_zone_start(self.screen_height),
            "paddle_moved_after_set": False,
            "paddle_reached_target": False,
            "last_movement_frame": 0,
            "frames_since_target_set": 0,
            "saved_ball_vel_x": None,
            "game_restart_required": False,
            "last_ball_vel_y": None,
            "ball_moving_downward_last_frame": False,
        }
    
    def activate(self) -> None:
        """Активирует движок движения."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Деактивирует движок движения."""
        self.is_active = False
    
    def update_game_state(self, game_state: GameState) -> None:
        """Обновляет состояние игры."""
        self.current_game_state = game_state
    
    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
        
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state or not self.is_active:
            return self._fallback_movement(current_x)
        
        try:
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            ball_x = self.current_game_state.ball_position.x
            
            # Обновляем отслеживание направления мяча
            self.separation_zone_tracker["last_ball_vel_y"] = ball_vel_y
            
            # Рассчитываем зоны
            zones = self._calculate_zones()
            
            # Если мяч в зоне кубиков - платформа НЕ должна двигаться
            if ball_y < zones["separation_zone_start"]:
                return self._handle_bricks_zone(ball_y)
            
            # Обрабатываем зону разделения
            separation_result = self._handle_separation_zone(ball_y, ball_vel_y, zones)
            if separation_result is not None:
                return separation_result
            
            # Мяч ниже кубиков и движется вниз/в разделительной зоне — считаем прицельную позицию
            if ball_y < zones["paddle_zone_start"]:
                intersection_point = self.trajectory_engine.predict_paddle_intersection(
                    self.current_game_state,
                    self.current_game_state.paddle_position.y
                )
                
                if intersection_point is None:
                    landing_x = self._predict_exact_landing_position()
                else:
                    landing_x = intersection_point.x
                
                optimal_x = self._calculate_target_position(landing_x, ball_y, zones)
                
                return self._execute_movement(current_x, optimal_x, paddle_speed)
            else:
                # Мяч движется вверх — обрабатываем возможный отскок от потолка
                return self._handle_upward_movement(ball_y)
                
        except (AttributeError, TypeError) as e:
            self._logger.error(f"Ошибка типов при движении платформы: {e}", exc_info=True)
            if self.current_game_state and hasattr(self.current_game_state, "paddle_position"):
                return int(self.current_game_state.paddle_position.x)
            return self.screen_width // 2
        except InvalidStateError as e:
            self._logger.error(f"Недопустимое состояние при движении платформы: {e}", exc_info=True)
            return self.screen_width // 2
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при движении платформы: {e}", exc_info=True)
            if self.current_game_state and hasattr(self.current_game_state, "paddle_position"):
                return int(self.current_game_state.paddle_position.x)
            return self.screen_width // 2
    
    def _calculate_zones(self) -> Dict[str, float]:
        """Рассчитывает границы зон игры."""
        bricks_zone_end = self.config.zones.bricks_zone_end
        separation_zone_start = self.config.zones.separation_zone_start
        paddle_zone_start = self.config.zones.paddle_zone_start(self.screen_height)
        
        # Обновляем отслеживание зоны разделения
        self.separation_zone_tracker["separation_zone_start"] = separation_zone_start
        self.separation_zone_tracker["paddle_zone_start"] = paddle_zone_start
        
        return {
            "bricks_zone_end": bricks_zone_end,
            "separation_zone_start": separation_zone_start,
            "paddle_zone_start": paddle_zone_start,
        }
    
    def _handle_bricks_zone(self, ball_y: float) -> int:
        """Обрабатывает ситуацию, когда мяч находится в зоне кубиков."""
        if not self.current_game_state:
            return self.screen_width // 2
        
        # В зоне кубиков платформа не двигается
        return int(self.current_game_state.paddle_position.x)
    
    def _handle_separation_zone(
        self, ball_y: float, ball_vel_y: float, zones: Dict[str, float]
    ) -> Optional[int]:
        """Обрабатывает ситуацию, когда мяч находится в зоне разделения."""
        if not self.current_game_state:
            return None
        
        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]
        
        # Если мяч в разделительной зоне, но движется вверх — не дёргаем платформу
        if separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0:
            return int(self.current_game_state.paddle_position.x)
        
        # Проверяем, вошел ли мяч в зону разделения
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        # Если позиция уже зафиксирована в зоне разделения - возвращаем её БЕЗ пересчета
        if in_separation_zone and self.separation_zone_tracker["target_position_set"]:
            fixed_position = self.separation_zone_tracker["target_position"]
            if fixed_position is not None:
                return int(fixed_position)
        
        # Если мяч только что вошел в зону разделения, отмечаем это
        if in_separation_zone and not self.separation_zone_tracker["ball_entered_separation_zone"]:
            self.separation_zone_tracker["ball_entered_separation_zone"] = True
        
        return None
    
    def _handle_upward_movement(self, ball_y: float) -> int:
        """Обрабатывает ситуацию, когда мяч движется вверх."""
        if ball_y < self.config.zones.ball_reset_height:
            return self._handle_ceiling_bounce_positioning()
        return int(self._track_ball_position())
    
    def _calculate_target_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float]
    ) -> int:
        """Рассчитывает целевую позицию платформы."""
        bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 0
        ball_speed = self.current_game_state.ball_speed if self.current_game_state else self.config.ball.default_speed
        
        # Получаем текущую ситуацию для обучения
        current_situation = {
            "bricks_remaining": bricks_count,
            "ball_speed": ball_speed,
            "time_pressure": self._is_time_pressure(),
        }
        
        # Применяем пользовательские правила из промпта
        user_rules = self.strategy_optimizer.apply_user_prompt_rules(current_situation)
        
        # КРИТИЧНО: Для малого количества блоков (<=10) ВСЕГДА используем точное прицеливание
        precision_priority = user_rules.get("precision_priority", False) or bricks_count <= self.config.precision_priority_threshold
        
        # Применяем правила из промпта: если указан приоритет точности, используем его
        if user_rules.get("destruction_priority", False):
            precision_priority = True
        
        # КРИТИЧНО: Если было отбитие в пустоту, принудительно используем точное прицеливание
        if self.empty_bounce_tracker["consecutive_empty_bounces"] >= self.empty_bounce_tracker["max_empty_bounces"]:
            precision_priority = True
        
        if precision_priority:
            return self._calculate_precision_position(landing_x, ball_y, zones, bricks_count, ball_speed, user_rules)
        
        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            return self._calculate_position_for_max_destruction(landing_x, ball_y, zones, bricks_count)
        
        # Ищем целевой кирпич и рассчитываем позицию
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        
        return self._calculate_position_with_target_brick(landing_x, ball_y, zones, bricks_count)
    
    def _calculate_precision_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float],
        bricks_count: int, ball_speed: int, user_rules: Dict[str, Any]
    ) -> int:
        """Рассчитывает точную позицию для малого количества блоков."""
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        
        optimal_position = self._calculate_precise_position_for_few_bricks(landing_x)
        
        if optimal_position is not None:
            action_plan = {
                "ball_speed": ball_speed,
                "movement_distance": abs(optimal_position - self.current_game_state.paddle_position.x),
                "confidence": 0.8,
            }
            success_prob = self.strategy_optimizer.predict_success_probability(action_plan)
            
            if success_prob > self.config.low_success_probability_threshold or bricks_count <= self.config.precision_priority_threshold:
                in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
                if self.separation_zone_tracker["target_position_set"]:
                    target_pos = self.separation_zone_tracker["target_position"]
                    if target_pos is not None:
                        return int(target_pos)
                
                # Применяем защиту от попадания в углы платформы
                safe_margin = 30
                paddle_half_width = self.config.paddle.width / 2
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                
                if in_separation_zone:
                    self._set_target_position_if_needed(int(optimal_position), "few_bricks")
                
                if user_rules.get("use_movement_log", True) and self.current_game_state:
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        int(optimal_position),
                        f"Точное прицеливание в {bricks_count} блоков",
                        0.9
                    )
                return int(optimal_position)
        
        return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
    
    def _calculate_position_for_max_destruction(
        self, landing_x: float, ball_y: float, zones: Dict[str, float], bricks_count: int
    ) -> int:
        """Рассчитывает позицию для максимизации разрушений."""
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        
        optimal_position = self._find_optimal_angle_for_max_destruction()
        
        if optimal_position is not None:
            action_plan = {
                "ball_speed": self.current_game_state.ball_speed,
                "movement_distance": abs(optimal_position - self.current_game_state.paddle_position.x),
                "confidence": self.config.confidence_default,
            }
            success_prob = self.strategy_optimizer.predict_success_probability(action_plan)
            
            if success_prob > self.config.success_probability_threshold:
                if self.separation_zone_tracker["target_position_set"]:
                    target_pos = self.separation_zone_tracker["target_position"]
                    if target_pos is not None:
                        return int(target_pos)
                
                # Применяем защиту от попадания в углы платформы
                safe_margin = 30
                paddle_half_width = self.config.paddle.width / 2
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                return int(optimal_position)
        
        return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
    
    def _calculate_position_with_target_brick(
        self, landing_x: float, ball_y: float, zones: Dict[str, float], bricks_count: int
    ) -> int:
        """Рассчитывает позицию с учетом целевого кирпича."""
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        
        game_state = self.current_game_state
        target_brick = self._find_best_target_brick()
        
        if target_brick:
            optimal_offset = self._calculate_optimal_offset(landing_x, target_brick)
            
            paddle_half_width = self.config.paddle.width / 2
            optimal_position = landing_x - (optimal_offset * paddle_half_width)
            
            # Обеспечиваем безопасную позицию
            safe_margin = 30
            min_position = paddle_half_width + safe_margin
            max_position = self.screen_width - paddle_half_width - safe_margin
            optimal_position = max(min_position, min(max_position, optimal_position))
            
            # Дополнительная проверка границ
            paddle_left_edge = optimal_position - paddle_half_width
            paddle_right_edge = optimal_position + paddle_half_width
            if paddle_left_edge < safe_margin:
                optimal_position = safe_margin + paddle_half_width
            elif paddle_right_edge > self.screen_width - safe_margin:
                optimal_position = self.screen_width - safe_margin - paddle_half_width
            
            # Учитываем предпочтения позиций
            position_preference = self.strategy_optimizer.get_optimal_position_preference(int(optimal_position))
            if position_preference < 0.4:
                if not self.separation_zone_tracker["target_position_set"]:
                    for offset in range(self.config.paddle_zone_offset_range[0], self.config.paddle_zone_offset_range[1], self.config.paddle_zone_offset_step):
                        test_x = int(optimal_position) + offset
                        if min_position <= test_x <= max_position:
                            pref = self.strategy_optimizer.get_optimal_position_preference(test_x)
                            if pref > 0.6:
                                return test_x
            
            in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
            if in_separation_zone and not self.separation_zone_tracker["target_position_set"]:
                self.separation_zone_tracker["target_position"] = int(optimal_position)
                self.separation_zone_tracker["target_position_set"] = True
            
            if self.current_game_state:
                self._log_paddle_movement(
                    self.current_game_state.paddle_position.x,
                    int(optimal_position),
                    f"Прицеливание в целевой блок (осталось {bricks_count} блоков)",
                    0.8
                )
            return int(optimal_position)
        else:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
    
    def _calculate_fallback_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float], bricks_count: int
    ) -> int:
        """Рассчитывает резервную позицию, когда нет явной цели."""
        in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
        
        if in_separation_zone and self.separation_zone_tracker["target_position_set"]:
            fixed_position = self.separation_zone_tracker["target_position"]
            if fixed_position is not None:
                return int(fixed_position)
        
        safe_margin = 30
        paddle_half_width = self.config.paddle.width / 2
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        base_position = max(min_position, min(max_position, int(landing_x)))
        
        # Применяем защиту от попадания в углы платформы
        base_position = self._ensure_safe_paddle_position(float(base_position), landing_x)
        base_position = max(min_position, min(max_position, int(base_position)))
        
        if in_separation_zone:
            self._set_target_position_if_needed(int(base_position), "простое движение")
        
        if self.current_game_state is not None:
            self._log_paddle_movement(
                self.current_game_state.paddle_position.x,
                base_position,
                f"Простое движение к мячу (осталось {bricks_count} блоков)",
                0.5
            )
        
        base_position_int = int(base_position)
        position_preference = self.strategy_optimizer.get_optimal_position_preference(base_position_int)
        if position_preference < 0.4:
            for offset in range(-40, 41, 10):
                test_x = base_position_int + offset
                if min_position <= test_x <= max_position:
                    pref = self.strategy_optimizer.get_optimal_position_preference(test_x)
                    if pref > 0.6:
                        return test_x
        return base_position_int
    
    def _set_target_position_if_needed(self, position: int, reason: str) -> None:
        """Устанавливает целевую позицию, если она еще не установлена."""
        current_pos = None
        if self.current_game_state:
            current_pos = int(self.current_game_state.paddle_position.x)
        
        # Используем трекер для установки позиции с проверкой расстояния
        self._update_target_position(position, reason, current_pos)
    
    def _update_target_position(self, position: int, reason: str, current_pos: Optional[int]) -> None:
        """Обновляет целевую позицию."""
        if not self.separation_zone_tracker["target_position_set"]:
            self.separation_zone_tracker["target_position"] = position
            self.separation_zone_tracker["target_position_set"] = True
            self.separation_zone_tracker["frames_since_target_set"] = 0
            
            if self.current_game_state:
                ball_vel_x = self.current_game_state.ball_velocity.x if hasattr(self.current_game_state, "ball_velocity") else 0
                self.separation_zone_tracker["saved_ball_vel_x"] = ball_vel_x
    
    def _ensure_safe_paddle_position(self, paddle_center_x: float, landing_x: float) -> float:
        """Обеспечивает безопасную позицию платформы, предотвращая попадание мяча в углы."""
        paddle_half_width = self.config.paddle.width / 2
        ball_radius = 8
        safe_edge_distance = 25
        
        paddle_left_edge = paddle_center_x - paddle_half_width
        paddle_right_edge = paddle_center_x + paddle_half_width
        
        distance_to_left_edge = landing_x - paddle_left_edge
        distance_to_right_edge = paddle_right_edge - landing_x
        
        if distance_to_left_edge < safe_edge_distance:
            adjustment = safe_edge_distance - distance_to_left_edge
            paddle_center_x += adjustment
        elif distance_to_right_edge < safe_edge_distance:
            adjustment = safe_edge_distance - distance_to_right_edge
            paddle_center_x -= adjustment
        
        safe_margin = 30
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        paddle_center_x = max(min_position, min(max_position, paddle_center_x))
        
        return paddle_center_x
    
    def _find_best_target_brick(self) -> Optional[Any]:
        """Находит лучший кубик для прицеливания."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        bricks_count = len(self.current_game_state.remaining_bricks)
        
        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            return self._find_optimal_angle_for_max_destruction()
        
        # Для малого количества блоков — отдельная логика
        if bricks_count <= 5:
            return self._find_best_target_for_few_bricks()
        
        best_brick = None
        best_score = -float("inf")
        
        for brick in self.current_game_state.remaining_bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = self.current_game_state.paddle_position.y - brick_y
            
            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 1000.0
            
            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3
            
            horizontal_distance = abs(brick_center_x - self.current_game_state.ball_position.x)
            score -= horizontal_distance * 0.5
            
            if score > best_score:
                best_score = score
                best_brick = brick
        
        return best_brick
    
    def _find_optimal_angle_for_max_destruction(self) -> Optional[Any]:
        """Находит оптимальный угол удара для максимизации количества разрушенных блоков."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        landing_x = self._predict_exact_landing_position()
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.config.paddle.width / 2
        
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0
        best_target_brick = None
        
        for offset in test_offsets:
            bounce_x = landing_x - (offset * paddle_half_width)
            
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            intersection_point = self.trajectory_engine.predict_paddle_intersection(
                self.current_game_state, paddle_y
            )
            
            if intersection_point is None:
                continue
            
            after_bounce_trajectory = self.trajectory_engine.predict_after_bounce_trajectory(
                self.current_game_state, intersection_point, bounce_x
            )
            
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset
                
                first_hit_brick = self._find_first_brick_in_trajectory(
                    after_bounce_trajectory, self.current_game_state.remaining_bricks
                )
                if first_hit_brick:
                    best_target_brick = first_hit_brick
        
        return best_target_brick
    
    def _count_bricks_in_trajectory(self, trajectory: List[Point], bricks: List[Any]) -> int:
        """Подсчитывает количество блоков, которые будут разрушены траекторией."""
        if not trajectory or not bricks:
            return 0
        
        destroyed_bricks = set()
        ball_radius = self.config.ball.radius
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
            
            for brick in bricks:
                brick_id = id(brick)
                if brick_id in destroyed_bricks:
                    continue
                
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        destroyed_bricks.add(brick_id)
        
        return len(destroyed_bricks)
    
    def _find_first_brick_in_trajectory(self, trajectory: List[Point], bricks: List[Any]) -> Optional[Any]:
        """Находит первый блок, который будет разрушен траекторией."""
        if not trajectory or not bricks:
            return None
        
        ball_radius = self.config.ball.radius
        min_distance = float("inf")
        first_brick = None
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
            
            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        distance = math.sqrt(
                            (point.x - trajectory[0].x) ** 2
                            + (point.y - trajectory[0].y) ** 2
                        )
                        
                        if distance < min_distance:
                            min_distance = distance
                            first_brick = brick
                            break
        
        return first_brick
    
    def _find_best_target_for_few_bricks(self) -> Optional[Any]:
        """Специальная логика выбора цели для малого количества оставшихся кубиков."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        bricks = self.current_game_state.remaining_bricks
        
        # Для 1 кирпича - используем улучшенную логику
        if len(bricks) == 1:
            brick = bricks[0]
            return brick
        
        # Для 2-3 кубиков — самый нижний, но с учетом траектории
        if len(bricks) <= 3:
            bottom_brick = min(bricks, key=lambda b: getattr(b, "y", 0))
            
            ball_y = self.current_game_state.ball_position.y
            vel_x = self.current_game_state.ball_velocity.x if hasattr(self.current_game_state, "ball_velocity") else 0
            
            for brick in bricks:
                brick_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
                brick_y = getattr(brick, "y", 0)
                
                if abs(brick_x - self.current_game_state.ball_position.x) < 150 and brick_y <= bottom_brick.y + 30:
                    if (vel_x > 0 and brick_x > self.current_game_state.ball_position.x) or (vel_x < 0 and brick_x < self.current_game_state.ball_position.x):
                        return brick
            
            return bottom_brick
        
        # Для 4–5 — более сложная оценка
        best_brick = None
        best_score = -float("inf")
        
        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = self.current_game_state.paddle_position.y - brick_y
            
            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 2000.0
            
            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3
            
            horizontal_distance = abs(brick_center_x - self.current_game_state.ball_position.x)
            score -= horizontal_distance * 0.2
            
            if score > best_score:
                best_score = score
                best_brick = brick
        
        return best_brick
    
    def _calculate_optimal_offset(self, landing_x: float, target_brick: Any) -> float:
        """Рассчитывает оптимальное смещение на платформе для попадания в кубик."""
        if not target_brick or not self.current_game_state:
            return 0.0
        
        bricks_count = len(self.current_game_state.remaining_bricks)
        
        if bricks_count == 1:
            brick_center_x = getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
            brick_y = getattr(target_brick, "y", 0)
            
            ball_y = self.current_game_state.ball_position.y
            paddle_y = self.current_game_state.paddle_position.y
            distance_to_brick = brick_y - paddle_y
            horizontal_offset_needed = brick_center_x - landing_x
            
            paddle_half_width = self.config.paddle.width / 2
            max_offset = 1.5
            
            if abs(horizontal_offset_needed) > paddle_half_width * max_offset:
                offset = max_offset if horizontal_offset_needed > 0 else -max_offset
            else:
                offset = horizontal_offset_needed / (paddle_half_width * max_offset) * max_offset
            
            vel_x = self.current_game_state.ball_velocity.x if hasattr(self.current_game_state, "ball_velocity") else 0
            if abs(vel_x) > 0.1:
                prediction_adjustment = (vel_x / abs(vel_x)) * 0.2
                offset += prediction_adjustment
            
            offset = max(-max_offset, min(max_offset, offset))
            return offset
        
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_width = getattr(target_brick, "width", 60)
        brick_height = getattr(target_brick, "height", 20)
        
        brick_center_x = brick_x + brick_width / 2
        brick_center_y = brick_y + brick_height / 2
        
        paddle_y = self.current_game_state.paddle_position.y
        ball_x = self.current_game_state.ball_position.x
        ball_vel_x = self.current_game_state.ball_velocity.x
        
        if abs(ball_vel_x) > 0:
            if ball_vel_x > 0 and ball_x < brick_center_x:
                target_x = brick_center_x + min(brick_width * 0.15, 10)
            elif ball_vel_x < 0 and ball_x > brick_center_x:
                target_x = brick_center_x - min(brick_width * 0.15, 10)
            else:
                target_x = brick_center_x
        else:
            target_x = brick_center_x
        
        target_x = max(brick_x, min(brick_x + brick_width, target_x))
        delta_x = target_x - landing_x
        delta_y = paddle_y - brick_center_y
        
        if delta_y <= 0:
            return 0.0
        
        target_angle = math.atan2(delta_x, delta_y)
        max_angle = math.pi / 4
        offset = target_angle / max_angle
        offset = max(-1.0, min(1.0, offset))
        
        if abs(offset) < 0.1:
            if delta_x > 0:
                offset = 0.25
            else:
                offset = -0.25
        elif abs(delta_x) < 10:
            if delta_x > 0:
                offset = max(0.2, offset)
            else:
                offset = min(-0.2, offset)
        
        return offset
    
    def _calculate_precise_position_for_few_bricks(self, landing_x: float) -> Optional[float]:
        """Вычисляет точную позицию платформы для попадания в оставшиеся блоки."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        bricks = self.current_game_state.remaining_bricks
        bricks_count = len(bricks)
        
        if bricks_count > 10:
            return None
        
        is_critical = bricks_count == 1
        paddle_y = self.current_game_state.paddle_position.y
        paddle_half_width = self.config.paddle.width / 2
        
        intersection_point = self.trajectory_engine.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        best_position = None
        best_score = -float("inf")
        
        for brick in bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x + brick_width / 2
            brick_center_y = brick_y + brick_height / 2
            
            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y
            
            if dy <= 0:
                continue
            
            target_angle = math.atan2(dx, dy)
            max_angle = math.atan2(paddle_half_width, 50)
            normalized_angle = max(-max_angle, min(max_angle, target_angle))
            required_offset = normalized_angle / max_angle if max_angle > 0 else 0
            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))
            
            after_bounce_trajectory = self.trajectory_engine.predict_after_bounce_trajectory(
                self.current_game_state, intersection_point, bounce_x
            )
            
            will_hit = False
            hit_confidence = 0.0
            
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue
                
                ball_radius = self.config.ball.radius
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    center_x = brick_x + brick_width / 2
                    center_y = brick_y + brick_height / 2
                    distance_to_center = math.sqrt(
                        (point.x - center_x) ** 2 + (point.y - center_y) ** 2
                    )
                    max_distance = math.sqrt((brick_width / 2 + ball_radius) ** 2 + (brick_height / 2 + ball_radius) ** 2)
                    hit_confidence = max(hit_confidence, 1.0 - (distance_to_center / max_distance))
                    break
            
            if is_critical and not will_hit:
                min_distance_to_brick = float('inf')
                for point in after_bounce_trajectory:
                    if not hasattr(point, "x") or not hasattr(point, "y"):
                        continue
                    closest_x = max(brick_x, min(point.x, brick_x + brick_width))
                    closest_y = max(brick_y, min(point.y, brick_y + brick_height))
                    distance = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    min_distance_to_brick = min(min_distance_to_brick, distance)
                
                if min_distance_to_brick <= 30:
                    will_hit = True
                    hit_confidence = max(0.3, 1.0 - (min_distance_to_brick / 30.0))
            
            if will_hit:
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)
                
                if brick_y > 200:
                    score += 5000.0
                
                center_distance = abs(brick_center_x - self.screen_width // 2)
                score -= center_distance * 0.1
                
                if is_critical:
                    score += hit_confidence * 50000.0
                    if hit_confidence > 0.2:
                        score += 100000.0
                
                if score > best_score:
                    best_score = score
                    best_position = paddle_position
        
        if best_position is None and bricks:
            closest_brick = min(
                bricks,
                key=lambda b: (
                    paddle_y - getattr(b, "y", 0),
                    abs(
                        (getattr(b, "x", 0) + getattr(b, "width", 60) / 2)
                        - landing_x
                    ),
                ),
            )
            
            brick_center_x = (
                getattr(closest_brick, "x", 0)
                + getattr(closest_brick, "width", 60) / 2
            )
            
            if is_critical:
                for test_offset_multiplier in [1.0, 1.2, 1.5, 2.0]:
                    dx = brick_center_x - landing_x
                    required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * test_offset_multiplier)))
                    test_position = landing_x - (required_offset * paddle_half_width)
                    
                    min_position = paddle_half_width
                    max_position = self.screen_width - paddle_half_width
                    test_position = max(min_position, min(max_position, test_position))
                    
                    if abs(test_position - landing_x) < self.screen_width:
                        best_position = test_position
                        break
            else:
                dx = brick_center_x - landing_x
                required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
                best_position = landing_x - (required_offset * paddle_half_width)
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            if best_position is not None:
                best_position = max(min_position, min(max_position, best_position))
        
        if best_position is None and bricks_count <= 10 and bricks:
            closest_brick = min(
                bricks,
                key=lambda b: (
                    paddle_y - getattr(b, "y", 0),
                    abs(
                        (getattr(b, "x", 0) + getattr(b, "width", 60) / 2)
                        - landing_x
                    ),
                ),
            )
            
            brick_center_x = (
                getattr(closest_brick, "x", 0)
                + getattr(closest_brick, "width", 60) / 2
            )
            
            dx = brick_center_x - landing_x
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))
        
        return best_position
    
    def _execute_movement(self, current_x: int, optimal_x: int, paddle_speed: int) -> int:
        """Выполняет движение платформы."""
        distance_to_optimal = abs(optimal_x - current_x)
        
        # Проверяем зацикливание и при необходимости меняем стратегию
        self._change_strategy_if_looping()
        if self.loop_prevention_system["strategy_change_cooldown"] == 0:
            optimal_x = self._apply_alternative_strategy(optimal_x)
        
        # Допуск по точности позиционирования
        precision_tolerance = 2
        jitter_detected = self._detect_jitter()
        if jitter_detected:
            precision_tolerance = max(5, precision_tolerance + 2)
            self.smoothness_system["smoothness_penalty"] = min(
                1.0, self.smoothness_system["smoothness_penalty"] + 0.1
            )
        else:
            self.smoothness_system["smoothness_penalty"] = max(
                0.0, self.smoothness_system["smoothness_penalty"] - 0.05
            )
        
        base_precision_tolerance = 2
        precision_tolerance = base_precision_tolerance + int(
            self.smoothness_system["smoothness_penalty"] * 3
        )
        
        if distance_to_optimal < self.smoothness_system["min_movement_distance"]:
            if distance_to_optimal <= precision_tolerance:
                movement = 0
                self.smoothness_system["consecutive_stops"] += 1
                if self.smoothness_system["consecutive_stops"] > 3:
                    self.smoothness_system["smoothness_penalty"] = max(
                        0.0, self.smoothness_system["smoothness_penalty"] - 0.1
                    )
                self._last_adjusted_paddle_speed = paddle_speed
            else:
                movement = self._calculate_smooth_movement(current_x, optimal_x, distance_to_optimal)
                self._last_adjusted_paddle_speed = paddle_speed
        elif distance_to_optimal <= precision_tolerance:
            movement = 0
            self.smoothness_system["consecutive_stops"] += 1
            self._last_adjusted_paddle_speed = paddle_speed
        else:
            self.smoothness_system["consecutive_stops"] = 0
            
            if self.current_game_state:
                ball_speed = self.current_game_state.ball_speed
                distance_to_target = distance_to_optimal
                
                time_to_meeting = float("inf")
                ball_vel_y = (
                    self.current_game_state.ball_velocity.y
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                if ball_vel_y > 0:
                    ball_y = self.current_game_state.ball_position.y
                    paddle_y = self.current_game_state.paddle_position.y
                    distance_y = paddle_y - ball_y
                    if distance_y > 0:
                        time_to_meeting = distance_y / ball_vel_y
                
                speed_multiplier = self.strategy_optimizer.get_adaptive_paddle_speed(
                    ball_speed, distance_to_target
                )
                
                if time_to_meeting != float("inf") and time_to_meeting > 0:
                    if time_to_meeting < 30:
                        urgency_factor = 30.0 / max(time_to_meeting, 1)
                        speed_multiplier *= min(urgency_factor, 3.0)
                    elif time_to_meeting < 60:
                        urgency_factor = 60.0 / max(time_to_meeting, 1)
                        speed_multiplier *= min(urgency_factor, 2.0)
                    elif time_to_meeting < 80:
                        urgency_factor = 80.0 / max(time_to_meeting, 1)
                        speed_multiplier *= min(urgency_factor, 1.5)
                    else:
                        speed_multiplier *= 1.0
                else:
                    speed_multiplier *= 0.8
                
                base_speed_multiplier = 10.0
                if distance_to_target > 150:
                    base_speed_multiplier = 15.0
                elif distance_to_target > 100:
                    base_speed_multiplier = 12.0
                
                if time_to_meeting != float('inf') and time_to_meeting < 20:
                    base_speed_multiplier *= 1.5
                
                speed_multiplier = max(0.8, min(10.0, speed_multiplier))
                adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)
                adjusted_paddle_speed = max(
                    int(paddle_speed * 0.8), adjusted_paddle_speed
                )
                self._last_paddle_speed_multiplier = speed_multiplier
                self._last_adjusted_paddle_speed = adjusted_paddle_speed
            else:
                adjusted_paddle_speed = paddle_speed
            
            self._last_adjusted_paddle_speed = adjusted_paddle_speed
            movement = self._calculate_smooth_movement(current_x, optimal_x, distance_to_optimal)
        
        self._update_loop_tracking(movement, current_x, optimal_x)
        self._update_smoothness_tracking(movement, current_x)
        
        if movement != 0:
            reason = "ball_tracking" if not self._is_ball_moving_towards_paddle() else "trajectory_optimization"
            confidence = self._calculate_decision_confidence(optimal_x)
            self.performance_logger.log_paddle_movement(
                from_x=current_x,
                to_x=current_x + movement * paddle_speed,
                reason=reason,
                confidence=confidence,
            )
        
        return movement
    
    def _calculate_smooth_movement(
        self, current_x: int, optimal_x: int, distance: float
    ) -> int:
        """Вычисляет плавное движение с учетом штрафов за дрожание."""
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if self.current_game_state and hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker["separation_zone_start"]
        paddle_zone_start = self.separation_zone_tracker["paddle_zone_start"]
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        if self.separation_zone_tracker["target_position_set"]:
            effective_min_distance = 30
        else:
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (1 + penalty)
        
        if distance < effective_min_distance:
            return 0
        
        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0
    
    def _is_ball_moving_towards_paddle(self) -> bool:
        """Проверяет, движется ли мяч к платформе (вниз)."""
        if not self.current_game_state:
            return False
        return self.current_game_state.is_ball_falling()
    
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
    
    def _log_paddle_movement(self, from_x: float, to_x: float, reason: str, confidence: float = 1.0) -> None:
        """Логирует передвижение платформы для анализа."""
        self.performance_logger.log_paddle_movement(int(from_x), int(to_x), reason, confidence)
    
    def _predict_exact_landing_position(self) -> float:
        """Точное предсказание X-координаты, где мяч встретится с платформой."""
        if not self.current_game_state:
            return self.screen_width / 2.0
        
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y
        
        if vel_y <= 0:
            return ball_x
        
        ball_radius = self.config.ball.radius
        paddle_height = 15
        screen_width = self.screen_width
        
        paddle_top = paddle_y - paddle_height / 2
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return ball_x
        
        time_to_paddle = distance_y / vel_y
        if time_to_paddle <= 0:
            return ball_x
        
        current_x = ball_x
        current_vel_x = vel_x
        remaining_time = time_to_paddle
        min_center_x = ball_radius
        max_center_x = screen_width - ball_radius
        
        while remaining_time > 0 and abs(current_vel_x) > 0.001:
            new_x = current_x + current_vel_x * remaining_time
            
            if new_x < min_center_x:
                time_to_wall = (min_center_x - current_x) / current_vel_x if current_vel_x < 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = min_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            elif new_x > max_center_x:
                time_to_wall = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = max_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            else:
                current_x = new_x
                break
        
        min_x = self.config.paddle.width // 2
        max_x = screen_width - self.config.paddle.width // 2
        return max(min_x, min(max_x, current_x))
    
    def _handle_ceiling_bounce_positioning(self) -> int:
        """Специальная логика для позиционирования при отскоке мяча от потолка."""
        if not self.current_game_state:
            return self.screen_width // 2
        
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        if ball_y < 30 and vel_y > 0:
            if abs(vel_x) < 2:
                remaining_bricks = self.current_game_state.remaining_bricks
                if remaining_bricks:
                    avg_brick_x = sum(
                        getattr(b, "x", 0) + getattr(b, "width", 60) / 2
                        for b in remaining_bricks
                    ) / len(remaining_bricks)
                    target_x = (ball_x + avg_brick_x) / 2.0
                else:
                    center_x = self.screen_width // 2
                    target_x = center_x + (ball_x - center_x) * 0.3
            else:
                target_x = ball_x + vel_x * 2.0
            
            target_x += random.choice([-15, -10, 0, 10, 15])
            
            paddle_half_width = self.config.paddle.width / 2
            min_x = paddle_half_width + 5
            max_x = self.screen_width - paddle_half_width - 5
            target_x = max(min_x, min(max_x, target_x))
            return int(target_x)
        
        return int(self._track_ball_position())
    
    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с небольшим упреждением."""
        if not self.current_game_state:
            return self.screen_width / 2.0
        
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        vel_x = game_state.ball_velocity.x
        
        prediction_time = 3
        predicted_x = ball_x + vel_x * prediction_time
        
        screen_width = self.screen_width
        ball_radius = self.config.ball.radius
        min_x = ball_radius
        max_x = screen_width - ball_radius
        
        return max(min_x, min(max_x, predicted_x))
    
    def _detect_loop_pattern(self) -> bool:
        """Обнаруживает зацикливание в движениях платформы."""
        history = self.loop_prevention_system["movement_history"]
        trajectory_history = self.loop_prevention_system["trajectory_history"]
        threshold = self.loop_prevention_system["loop_detection_threshold"]
        
        if len(history) < threshold * 2:
            return False
        
        recent_movements = history[-threshold:]
        movement_counts = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1
        
        max_count = max(movement_counts.values())
        if max_count >= threshold * 0.8:
            return True
        
        position_history = self.loop_prevention_system["position_history"]
        if len(position_history) >= 10:
            recent_positions = position_history[-10:]
            if len(set(recent_positions[-8:])) <= 2:
                return True
        
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
            if vertical_count >= 4:
                return True
        
        return False
    
    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания."""
        if not self._detect_loop_pattern():
            return
        
        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return
        
        strategies = self.loop_prevention_system["alternative_strategies"]
        idx = self.loop_prevention_system["current_strategy_index"]
        self.loop_prevention_system["current_strategy_index"] = (idx + 1) % len(strategies)
        
        self.loop_prevention_system["strategy_change_cooldown"] = 10
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
    
    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """Применяет альтернативную стратегию позиционирования для выхода из зацикливания."""
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]
        screen_center = self.screen_width // 2
        
        if strategy == "center_focus":
            return screen_center
        
        if strategy == "edge_focus":
            current_pos = getattr(self.current_game_state, "paddle_position", None)
            if current_pos and hasattr(current_pos, "x"):
                return self.screen_width - 70 if current_pos.x < screen_center else 70
            return 70
        
        if strategy == "predictive_targeting":
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
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = self.loop_prevention_system["movement_history"][-10:]
        
        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = self.loop_prevention_system["position_history"][-10:]
        
        if self.current_game_state:
            trajectory_info = {
                "ball_x": self.current_game_state.ball_position.x,
                "ball_y": self.current_game_state.ball_position.y,
                "optimal_x": optimal_x,
                "timestamp": time.time(),
            }
            self.loop_prevention_system["trajectory_history"].append(trajectory_info)
            if len(self.loop_prevention_system["trajectory_history"]) > 10:
                self.loop_prevention_system["trajectory_history"] = self.loop_prevention_system["trajectory_history"][-5:]
    
    def _update_smoothness_tracking(self, movement: int, current_x: int) -> None:
        """Обновляет данные отслеживания плавности движения."""
        self.smoothness_system["recent_movements"].append(movement)
        if len(self.smoothness_system["recent_movements"]) > self.smoothness_system["jitter_window"]:
            self.smoothness_system["recent_movements"] = self.smoothness_system["recent_movements"][-self.smoothness_system["jitter_window"]:]
        
        self.smoothness_system["recent_positions"].append(current_x)
        if len(self.smoothness_system["recent_positions"]) > self.smoothness_system["jitter_window"]:
            self.smoothness_system["recent_positions"] = self.smoothness_system["recent_positions"][-self.smoothness_system["jitter_window"]:]
        
        if len(self.smoothness_system["recent_movements"]) >= 2:
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                self.smoothness_system["movement_changes"].append(time.time())
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]
    
    def _detect_jitter(self) -> bool:
        """Обнаруживает дрожание платформы (частые смены направления движения)."""
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False
        
        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1
        
        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True
        
        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True
        
        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            if (
                position_variance < 10
                and len([m for m in movements[-5:] if m != 0]) >= 3
            ):
                return True
        
        return False
    
    def _fallback_movement(self, current_x: int) -> int:
        """Резервное движение платформы — улучшенное следование за мячом."""
        if not self.current_game_state:
            return 0
        
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y
        
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
            if time_to_paddle > 0:
                predicted_x = ball_x + vel_x * time_to_paddle
                
                screen_width = self.screen_width
                ball_radius = self.config.ball.radius
                
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
    
    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """Обучает движок на основе результата действия."""
        action_type = action_result.get("action_type", "")
        
        if action_type == "paddle_bounce":
            bricks_before = action_result.get("game_state_before", {}).get("bricks_remaining", 0)
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
