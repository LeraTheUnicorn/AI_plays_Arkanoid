"""
Основной координатор AI системы.

Координирует работу всех компонентов AI системы:
- MovementEngine для управления движением платформы
- DecisionMaker для принятия решений
- PredictionEngine для предсказания траекторий
- LearningSystem для обучения
"""

import time
import logging
from typing import List, Optional, Dict, Any

from ..game_state import GameState, Point
from ..config import AIConfig
from ..exceptions import InvalidStateError, PredictionError, LearningError, DataError
from .movement_engine import MovementEngine
from .decision_maker import DecisionMaker
from ..prediction.trajectory_engine import TrajectoryEngine
from ..prediction.collision_detector import CollisionDetector
from ..learning.pattern_analyzer import PatternAnalyzer
from ..learning.strategy_optimizer import StrategyOptimizer
from ..performance_logger import PerformanceLogger
from ..debug_logger import DebugLogger


class AICoordinator:
    """
    Основной координатор AI системы.
    
    Координирует работу всех компонентов AI системы:
    - MovementEngine для управления движением платформы
    - DecisionMaker для принятия решений
    - TrajectoryEngine для предсказания траекторий
    - CollisionDetector для детекции столкновений
    - PatternAnalyzer для анализа паттернов
    - StrategyOptimizer для оптимизации стратегий
    """

    def __init__(
        self,
        screen_width: int = 800,
        screen_height: int = 600,
        debug_mode: bool = False,
    ):
        """
        Инициализация AICoordinator.
        
        Args:
            screen_width: Ширина игрового экрана.
            screen_height: Высота игрового экрана.
            debug_mode: Режим отладки с визуализацией.
        """
        # Конфигурация
        self.config: AIConfig = AIConfig()
        
        # Параметры экрана
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = bool(debug_mode)
        
        # Настройка логирования
        self._logger = self._setup_logging()
        
        # Инициализация компонентов
        self.trajectory_engine = TrajectoryEngine(screen_width, screen_height)
        self.collision_detector = CollisionDetector(screen_width, screen_height)
        self.pattern_analyzer = PatternAnalyzer()
        self.strategy_optimizer = StrategyOptimizer()
        self.performance_logger = PerformanceLogger()
        self.debug_logger = DebugLogger(log_interval=self.config.debug_log_interval)
        
        # Инициализация движка движения и принятия решений
        self.movement_engine = MovementEngine(
            screen_width,
            screen_height,
            self.config,
            self.trajectory_engine,
            self.collision_detector,
            self.pattern_analyzer,
            self.strategy_optimizer,
            self.performance_logger,
            self._logger,
        )
        
        self.decision_maker = DecisionMaker(
            screen_width,
            screen_height,
            self.config,
            self.trajectory_engine,
            self.collision_detector,
            self.pattern_analyzer,
            self.strategy_optimizer,
            self.performance_logger,
            self._logger,
        )
        
        # Состояние AI
        self.current_game_state: Optional[GameState] = None
        self.last_paddle_position: Optional[float] = None
        self.last_action_time = time.time()
        
        # Метрики производительности
        self.performance_metrics: Dict[str, Any] = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
            "best_time_50_bricks": None,
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
        
        # Кэш карты кирпичей
        self._brick_map_cache: Optional[tuple] = None
        self._brick_cache_stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
        }
        
        # Последняя скорректированная скорость платформы
        self._last_adjusted_paddle_speed: Optional[int] = None
        
        # Метрики по сессиям
        self.session_metrics: List[Dict[str, Any]] = []
        self.session_counter: int = 0
        
        # Параметры режима обучения
        self.training_parameters: Dict[str, Any] = {
            "ball_speed": 8,
            "paddle_speed_multiplier": 2.0,
            "total_bricks_destroyed": 0,
            "total_time": 0,
            "lives_lost": 0,
            "match_history": [],
        }
        
        # Отслеживание предыдущей позиции и скорости мяча
        self._last_ball_position: Optional[Point] = None
        self._last_ball_velocity: Optional[Point] = None
        
    def _setup_logging(self) -> logging.Logger:
        """
        Настраивает и возвращает логгер для экземпляра AICoordinator.
        
        Returns:
            Настроенный логгер для этого экземпляра
        """
        logger = logging.getLogger(f"{__name__}.AICoordinator")
        
        # Настраиваем уровень логирования
        from ..logging_config import get_log_level
        log_level = get_log_level()
        logger.setLevel(log_level)
        
        # Убеждаемся, что root logger тоже настроен правильно
        root_logger = logging.getLogger()
        if root_logger.level > log_level:
            root_logger.setLevel(log_level)
            for root_handler in root_logger.handlers:
                if root_handler.level > log_level:
                    root_handler.setLevel(log_level)
        
        return logger
    
    def activate(self) -> None:
        """
        Активирует AI координатор для управления игрой.
        """
        self.is_active = True
        self.movement_engine.activate()
        self.decision_maker.activate()
        self._logger.info("AICoordinator активирован. Начинаем управление игрой...")
    
    def deactivate(self) -> None:
        """
        Деактивирует AI координатор.
        """
        self.is_active = False
        self.movement_engine.deactivate()
        self.decision_maker.deactivate()
        self._logger.info("AICoordinator деактивирован.")
    
    def update_game_state(
        self,
        ball: Any,
        paddle: Any,
        bricks: Any,
        score: int,
        start_time: int,
    ) -> None:
        """
        Обновляет состояние игры для AI-системы.
        
        Args:
            ball: Объект мяча из игры.
            paddle: Объект платформы из игры.
            bricks: Список оставшихся кубиков.
            score: Текущий счёт игрока.
            start_time: Время начала игры.
        """
        # Создаём новое состояние игры
        self.current_game_state = GameState.create_from_game_objects(
            ball, paddle, bricks, score, start_time
        )
        
        # Обновляем компоненты
        self.trajectory_engine.update_game_state(self.current_game_state)
        self.collision_detector.update_game_state(self.current_game_state)
        self.pattern_analyzer.update_game_state(self.current_game_state)
        self.strategy_optimizer.update_game_state(self.current_game_state)
        self.movement_engine.update_game_state(self.current_game_state)
        self.decision_maker.update_game_state(self.current_game_state)
        
        # Инициализируем статистику игры, если это новая игра
        if self.current_game_stats["start_time"] is None:
            self.current_game_stats["start_time"] = start_time
            self.performance_logger.log_game_start(self.current_game_state)
        
        # Обновляем время последнего расчета
        self._last_calculation_time = time.time()
    
    def get_optimal_paddle_position(self) -> int:
        """
        Получает оптимальную позицию центра платформы.
        
        Returns:
            Оптимальная X-координата центра платформы.
        """
        if not self.current_game_state or not self.is_active:
            return self.screen_width // 2
        
        return self.decision_maker.get_optimal_paddle_position()
    
    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции.
        
        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
        
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        return self.movement_engine.move_paddle_towards(current_x, paddle_speed)
    
    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI-систему на основе результата последнего действия.
        
        Args:
            action_result: Словарь с информацией о результате (hit/miss, счёт и т.д.).
        """
        self.decision_maker.learn_from_result(action_result)
        self.movement_engine.learn_from_result(action_result)
        self.pattern_analyzer.learn_from_result(action_result)
        self.strategy_optimizer.learn_from_result(action_result)
    
    def on_game_end(self, success: bool, final_score: int, training_mode: bool = False) -> None:
        """
        Обрабатывает окончание игры.
        
        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
            training_mode: True, если это режим обучения.
        """
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
        learning_progress = self.strategy_optimizer.get_learning_progress()
        if isinstance(learning_progress, dict):
            success_rate = learning_progress.get("success_rate", 0.0)
            self.performance_metrics["learning_progress"] = (
                self.performance_metrics["learning_progress"] * 0.9
                + success_rate * 0.1
            )
        
        # Логирование окончания игры
        self.performance_logger.log_game_end(self.current_game_state, success, final_score)
        
        # В режиме обучения обрабатываем результаты матча
        if training_mode:
            self._process_training_match(success, final_score)
        
        # Сохраняем данные по сессии
        self._save_session_metrics(success, final_score)
        
        # Сбрасываем статистику текущей игры
        self._reset_current_game_stats()
        
        # Сбрасываем состояние игры
        self.current_game_state = None
    
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
    
    def _save_session_metrics(self, success: bool, final_score: int) -> None:
        """Сохраняет агрегированные метрики по завершённой игре в список сессий."""
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
    
    def _process_training_match(self, success: bool, final_score: int) -> None:
        """Обрабатывает результаты матча в режиме обучения."""
        match_data = {
            "success": success,
            "score": final_score,
            "ball_speed": self.training_parameters["ball_speed"],
            "paddle_speed_multiplier": self.training_parameters["paddle_speed_multiplier"],
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
        self.strategy_optimizer.learn_from_match_results(match_data)
    
    def update_training_stats(
        self, bricks_destroyed: int, time_elapsed: float, lives_lost: int
    ) -> None:
        """Обновляет статистику обучения во время игры."""
        self.training_parameters["total_bricks_destroyed"] = bricks_destroyed
        self.training_parameters["total_time"] = time_elapsed
        self.training_parameters["lives_lost"] = lives_lost
    
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
