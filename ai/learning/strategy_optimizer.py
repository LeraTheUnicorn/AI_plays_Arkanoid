"""
Оптимизация стратегий.

Отвечает за:
- Выбор оптимальной стратегии
- Анализ эффективности стратегий
- Оптимизацию параметров игры
- Предсказание успешности действий
"""

import time
from typing import List, Optional, Dict, Any

from ..game_state import GameState


class StrategyOptimizer:
    """
    Оптимизация стратегий.
    
    Отвечает за:
    - Выбор оптимальной стратегии
    - Анализ эффективности стратегий
    - Оптимизацию параметров игры
    - Предсказание успешности действий
    """

    def __init__(self):
        """Инициализация StrategyOptimizer."""
        # История стратегий
        self.strategy_history: List[Dict[str, Any]] = []
        
        # Веса стратегий
        self.strategy_weights: Dict[str, float] = {
            "center_focus": 0.3,
            "edge_focus": 0.3,
            "predictive_targeting": 0.4,
        }
        
        # Статистика стратегий
        self.strategy_stats: Dict[str, Dict[str, Any]] = {}
        
        # Состояние игры
        self.current_game_state: Optional[GameState] = None
        
        # Данные для обучения
        self.learning_data: Dict[str, Any] = {
            "success_factors": {},
            "position_preferences": {},
            "total_iterations": 0,
        }
    
    def update_game_state(self, game_state: GameState) -> None:
        """Обновляет состояние игры."""
        self.current_game_state = game_state
    
    def get_strategy_recommendation(self, situation: Dict[str, Any]) -> Dict[str, float]:
        """
        Получает рекомендацию по стратегии.
        
        Args:
            situation: Текущая игровая ситуация.
            
        Returns:
            Словарь с весами стратегий.
        """
        bricks_remaining = situation.get("bricks_remaining", 0)
        ball_speed = situation.get("ball_speed", 5)
        time_pressure = situation.get("time_pressure", False)
        
        weights = self.strategy_weights.copy()
        
        # Анализируем ситуацию и корректируем веса
        if bricks_remaining <= 5:
            # Мало блоков - используем точное прицеливание
            weights["predictive_targeting"] = 0.6
            weights["center_focus"] = 0.2
            weights["edge_focus"] = 0.2
        elif bricks_remaining <= 15:
            # Среднее количество блоков - баланс между стратегиями
            weights["predictive_targeting"] = 0.5
            weights["center_focus"] = 0.3
            weights["edge_focus"] = 0.2
        else:
            # Много блоков - используем стратегию coverage
            weights["center_focus"] = 0.4
            weights["edge_focus"] = 0.3
            weights["predictive_targeting"] = 0.3
        
        if ball_speed >= 8:
            # Высокая скорость - нужно больше предсказаний
            weights["predictive_targeting"] *= 1.2
        
        if time_pressure:
            # Давление по времени - используем более агрессивные стратегии
            weights["edge_focus"] *= 1.2
        
        # Нормализуем веса
        total = sum(weights.values())
        if total > 0:
            for strategy in weights:
                weights[strategy] /= total
        
        return weights
    
    def apply_user_prompt_rules(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применяет пользовательские правила из промпта.
        
        Args:
            situation: Текущая игровая ситуация.
            
        Returns:
            Словарь с правилами.
        """
        bricks_remaining = situation.get("bricks_remaining", 0)
        ball_speed = situation.get("ball_speed", 5)
        time_pressure = situation.get("time_pressure", False)
        
        rules = {
            "precision_priority": False,
            "destruction_priority": False,
            "use_movement_log": True,
        }
        
        # Правила из промпта
        if bricks_remaining <= 10:
            rules["precision_priority"] = True
        
        if time_pressure and bricks_remaining <= 20:
            rules["destruction_priority"] = True
        
        return rules
    
    def predict_success_probability(self, action_plan: Dict[str, Any]) -> float:
        """
        Предсказывает вероятность успеха действия.
        
        Args:
            action_plan: План действия.
            
        Returns:
            Вероятность успеха (0.0-1.0).
        """
        ball_speed = action_plan.get("ball_speed", 5)
        movement_distance = action_plan.get("movement_distance", 0)
        confidence = action_plan.get("confidence", 0.5)
        
        # Базовая вероятность успеха
        success_prob = confidence
        
        # Корректируем на основе скорости мяча
        if ball_speed >= 8:
            success_prob *= 0.8
        elif ball_speed <= 3:
            success_prob *= 1.2
        
        # Корректируем на основе расстояния движения
        if movement_distance > 100:
            success_prob *= 0.7
        elif movement_distance > 50:
            success_prob *= 0.9
        
        return max(0.1, min(1.0, success_prob))
    
    def get_optimal_position_preference(self, position: int) -> float:
        """
        Получает предпочтение позиции.
        
        Args:
            position: X-координата позиции.
            
        Returns:
            Предпочтение позиции (0.0-1.0).
        """
        if position in self.learning_data.get("position_preferences", {}):
            return self.learning_data["position_preferences"][position]
        
        # Базовое предпочтение для новых позиций
        return 0.5
    
    def get_adaptive_paddle_speed(self, ball_speed: int, distance_to_target: float) -> float:
        """
        Получает адаптивную скорость платформы.
        
        Args:
            ball_speed: Скорость мяча.
            distance_to_target: Расстояние до цели.
            
        Returns:
            Множитель скорости платформы.
        """
        # Базовый множитель
        speed_multiplier = 1.0
        
        # Корректируем на основе скорости мяча
        if ball_speed >= 8:
            speed_multiplier = 1.5
        elif ball_speed >= 6:
            speed_multiplier = 1.2
        elif ball_speed <= 3:
            speed_multiplier = 0.8
        
        # Корректируем на основе расстояния
        if distance_to_target > 150:
            speed_multiplier *= 1.3
        elif distance_to_target > 100:
            speed_multiplier *= 1.1
        
        return max(0.5, min(2.0, speed_multiplier))
    
    def update_strategy(self, action_result: Dict[str, Any]) -> None:
        """
        Обновляет стратегию на основе результата действия.
        
        Args:
            action_result: Результат действия.
        """
        strategy = action_result.get("strategy", "unknown")
        success = action_result.get("success", False)
        
        # Записываем результат в историю
        self._record_strategy_result(strategy, success, action_result)
        
        # Обновляем веса стратегий
        self._update_strategy_weights(strategy, success)
        
        # Обновляем факторы успеха
        self._update_success_factors(action_result)
        
        # Увеличиваем счетчик итераций
        self.learning_data["total_iterations"] += 1
    
    def _record_strategy_result(self, strategy: str, success: bool, action_result: Dict[str, Any]) -> None:
        """
        Записывает результат стратегии.
        
        Args:
            strategy: Название стратегии.
            success: Успешность действия.
            action_result: Результат действия.
        """
        result = {
            "strategy": strategy,
            "success": success,
            "timestamp": time.time(),
            "action_result": action_result,
        }
        
        self.strategy_history.append(result)
        
        # Ограничиваем историю последними 100 результатами
        if len(self.strategy_history) > 100:
            self.strategy_history = self.strategy_history[-100:]
    
    def _update_strategy_weights(self, strategy: str, success: bool) -> None:
        """
        Обновляет веса стратегий.
        
        Args:
            strategy: Название стратегии.
            success: Успешность действия.
        """
        if strategy not in self.strategy_weights:
            self.strategy_weights[strategy] = 0.3
        
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {
                "total": 0,
                "success": 0,
                "last_updated": time.time(),
            }
        
        self.strategy_stats[strategy]["total"] += 1
        if success:
            self.strategy_stats[strategy]["success"] += 1
        self.strategy_stats[strategy]["last_updated"] = time.time()
        
        # Обновляем веса на основе успешности
        for strat, stats in self.strategy_stats.items():
            total = stats["total"]
            if total > 0:
                success_rate = stats["success"] / total
                self.strategy_weights[strat] = success_rate
        
        # Нормализуем веса
        total_weight = sum(self.strategy_weights.values())
        if total_weight > 0:
            for strat in self.strategy_weights:
                self.strategy_weights[strat] /= total_weight
    
    def _update_success_factors(self, action_result: Dict[str, Any]) -> None:
        """
        Обновляет факторы успеха.
        
        Args:
            action_result: Результат действия.
        """
        success = action_result.get("success", False)
        
        # Анализируем факторы, которые повлияли на успех
        factors = [
            ("ball_speed", action_result.get("game_state_before", {}).get("ball_speed")),
            ("bricks_remaining", action_result.get("game_state_before", {}).get("bricks_remaining")),
            ("paddle_position", action_result.get("paddle_position")),
            ("strategy", action_result.get("strategy")),
        ]
        
        for factor_name, factor_value in factors:
            if factor_value is None:
                continue
            
            if factor_name not in self.learning_data["success_factors"]:
                self.learning_data["success_factors"][factor_name] = {
                    "total_cases": 0,
                    "successful_cases": 0,
                }
            
            self.learning_data["success_factors"][factor_name]["total_cases"] += 1
            if success:
                self.learning_data["success_factors"][factor_name]["successful_cases"] += 1
    
    def learn_from_match_results(self, match_data: Dict[str, Any]) -> None:
        """
        Обучается на основе результатов матча.
        
        Args:
            match_data: Данные о матче.
        """
        success = match_data.get("success", False)
        bricks_destroyed = match_data.get("bricks_destroyed", 0)
        time_taken = match_data.get("time", 0)
        lives_lost = match_data.get("lives_lost", 0)
        
        # Вычисляем эффективность
        time_penalty = 1.0 + (lives_lost * 0.2)
        efficiency = bricks_destroyed / (time_taken * time_penalty) if time_taken > 0 else 0
        
        # Обновляем параметры на основе эффективности
        current_ball_speed = match_data.get("ball_speed", 8)
        current_paddle_mult = match_data.get("paddle_speed_multiplier", 2.0)
        
        # Сохраняем лучшие параметры
        if not hasattr(self, '_best_performance_params'):
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult,
                'efficiency': efficiency,
            }
        
        # Обновляем лучшие параметры, если текущий результат лучше
        if bricks_destroyed > self._best_performance_params['bricks_destroyed']:
            self._best_performance_params = {
                'bricks_destroyed': bricks_destroyed,
                'ball_speed': current_ball_speed,
                'paddle_speed_multiplier': current_paddle_mult,
                'efficiency': efficiency,
            }
        
        # Проверяем деградацию производительности
        if hasattr(self, '_best_performance_params') and len(self.strategy_history) >= 2:
            recent_games = self.strategy_history[-2:]
            recent_avg_bricks = sum(
                r.get("action_result", {}).get("bricks_destroyed", 0)
                for r in recent_games
                if r.get("action_result")
            ) / len(recent_games) if recent_games else 0
            best_bricks = self._best_performance_params['bricks_destroyed']
            
            if best_bricks > 0 and recent_avg_bricks < best_bricks * 0.5:
                # Деградация производительности - сбрасываем параметры к лучшим значениям
                pass
        
        # Целевое время матча: 5 секунд
        target_time = 5.0
        time_ratio = time_taken / target_time if target_time > 0 else 1.0
        
        # Приоритет 1: Если не сбиты все 50 кубиков
        if bricks_destroyed < 50:
            bricks_remaining = 50 - bricks_destroyed
            
            if bricks_destroyed < 20 or (lives_lost >= 3 and bricks_destroyed < 30):
                # Снижаем скорость только если результат действительно плохой
                if current_ball_speed > 15:
                    min_speed = 15
                    if hasattr(self, '_best_performance_params') and self._best_performance_params['bricks_destroyed'] >= 40:
                        min_speed = max(15, self._best_performance_params['ball_speed'] - 5)
                    
                    # Не снижаем ниже лучших параметров
                    pass
        
        # Приоритет 2: Если все кубики сбиты - можно увеличивать скорость
        elif success and lives_lost <= 1:
            if time_ratio > 1.2:
                pass
            elif efficiency > self._get_average_efficiency() * 1.1:
                pass
        
        # Если это первый матч или мало данных, используем более агрессивную адаптацию
        if len(self.strategy_history) <= 2:
            if bricks_destroyed >= 45 and lives_lost <= 1:
                pass
        else:
            avg_efficiency = self._get_average_efficiency()
            if avg_efficiency > 0 and success:
                if time_ratio > 1.2:
                    pass
                elif efficiency > avg_efficiency * 1.1:
                    pass
    
    def _get_average_efficiency(self) -> float:
        """Вычисляет среднюю эффективность за последние матчи."""
        if not self.strategy_history:
            return 0.0
        
        total_efficiency = 0.0
        count = 0
        
        for result in self.strategy_history:
            action_result = result.get("action_result", {})
            bricks = action_result.get("bricks_destroyed", 0)
            time_taken = action_result.get("time", 1)
            lives_lost = action_result.get("lives_lost", 0)
            
            time_penalty = 1.0 + (lives_lost * 0.2)
            efficiency = bricks / (time_taken * time_penalty) if time_taken > 0 else 0
            total_efficiency += efficiency
            count += 1
        
        return total_efficiency / count if count > 0 else 0.0
    
    def get_learning_progress(self) -> Dict[str, Any]:
        """
        Получает прогресс обучения.
        
        Returns:
            Словарь с метриками обучения.
        """
        if not self.strategy_stats:
            return {"message": "Недостаточно данных для обучения"}
        
        total_actions = sum(stat["total"] for stat in self.strategy_stats.values())
        total_success = sum(stat["success"] for stat in self.strategy_stats.values())
        success_rate = total_success / total_actions if total_actions > 0 else 0.0
        
        return {
            "total_iterations": self.learning_data["total_iterations"],
            "success_rate": success_rate,
            "strategy_weights": self.strategy_weights,
            "strategies_count": len(self.strategy_stats),
        }
    
    def reset_learning_data(self) -> None:
        """Сбрасывает данные обучения."""
        self.strategy_history = []
        self.strategy_weights = {
            "center_focus": 0.3,
            "edge_focus": 0.3,
            "predictive_targeting": 0.4,
        }
        self.strategy_stats = {}
        self.learning_data = {
            "success_factors": {},
            "position_preferences": {},
            "total_iterations": 0,
        }
