"""
Анализ паттернов.

Отвечает за:
- Обнаружение повторяющихся паттернов в игре
- Анализ успешных и неуспешных действий
- Статистический анализ игровых ситуаций
"""

import time
from typing import List, Optional, Dict, Any

from ..game_state import GameState


class PatternAnalyzer:
    """
    Анализ паттернов.
    
    Отвечает за:
    - Обнаружение повторяющихся паттернов в игре
    - Анализ успешных и неуспешных действий
    - Статистический анализ игровых ситуаций
    """

    def __init__(self):
        """Инициализация PatternAnalyzer."""
        # История действий
        self.action_history: List[Dict[str, Any]] = []
        
        # Статистика паттернов
        self.pattern_stats: Dict[str, Dict[str, Any]] = {}
        
        # Состояние игры
        self.current_game_state: Optional[GameState] = None
    
    def update_game_state(self, game_state: GameState) -> None:
        """Обновляет состояние игры."""
        self.current_game_state = game_state
    
    def record_action(self, action: Dict[str, Any]) -> None:
        """
        Записывает действие в историю.
        
        Args:
            action: Словарь с информацией о действии.
        """
        action["timestamp"] = time.time()
        self.action_history.append(action)
        
        # Ограничиваем историю последними 100 действиями
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """
        Анализирует паттерны в истории действий.
        
        Returns:
            Словарь с статистикой паттернов.
        """
        if not self.action_history:
            return {}
        
        # Анализируем успешность различных стратегий
        strategy_success = {}
        for action in self.action_history:
            strategy = action.get("strategy", "unknown")
            success = action.get("success", False)
            
            if strategy not in strategy_success:
                strategy_success[strategy] = {"total": 0, "success": 0}
            
            strategy_success[strategy]["total"] += 1
            if success:
                strategy_success[strategy]["success"] += 1
        
        # Анализируем паттерны позиционирования
        position_patterns = self._analyze_position_patterns()
        
        return {
            "strategy_success": strategy_success,
            "position_patterns": position_patterns,
        }
    
    def _analyze_position_patterns(self) -> Dict[str, Any]:
        """
        Анализирует паттерны позиционирования платформы.
        
        Returns:
            Словарь с статистикой позиционирования.
        """
        position_stats = {}
        
        for action in self.action_history:
            if "paddle_position" in action:
                position = action["paddle_position"]
                success = action.get("success", False)
                
                if position not in position_stats:
                    position_stats[position] = {"total": 0, "success": 0}
                
                position_stats[position]["total"] += 1
                if success:
                    position_stats[position]["success"] += 1
        
        return position_stats
    
    def get_success_rate(self, strategy: str) -> float:
        """
        Получает процент успешности стратегии.
        
        Args:
            strategy: Название стратегии.
            
        Returns:
            Процент успешности (0.0-1.0).
        """
        if not self.action_history:
            return 0.0
        
        total = 0
        success = 0
        
        for action in self.action_history:
            if action.get("strategy") == strategy:
                total += 1
                if action.get("success", False):
                    success += 1
        
        return success / total if total > 0 else 0.0
    
    def find_similar_situations(self, current_situation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Находит похожие ситуации в истории.
        
        Args:
            current_situation: Текущая игровая ситуация.
            
        Returns:
            Список похожих ситуаций из истории.
        """
        similar_situations = []
        
        for action in self.action_history:
            situation = action.get("situation", {})
            similarity = self._calculate_situation_similarity(current_situation, situation)
            
            if similarity > 0.7:
                similar_situations.append(action)
        
        return similar_situations
    
    def _calculate_situation_similarity(self, situation1: Dict[str, Any], situation2: Dict[str, Any]) -> float:
        """
        Вычисляет степень сходства двух ситуаций.
        
        Args:
            situation1: Первая ситуация.
            situation2: Вторая ситуация.
            
        Returns:
            Степень сходства (0.0-1.0).
        """
        if not situation1 or not situation2:
            return 0.0
        
        keys = set(situation1.keys()) & set(situation2.keys())
        if not keys:
            return 0.0
        
        total_diff = 0.0
        for key in keys:
            val1 = situation1[key]
            val2 = situation2[key]
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                diff = abs(val1 - val2)
                max_val = max(abs(val1), abs(val2), 1)
                total_diff += diff / max_val
        
        return 1.0 - (total_diff / len(keys) if keys else 0.0)
    
    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучается на основе результата действия.
        
        Args:
            action_result: Результат действия.
        """
        # Добавляем результат к истории
        self.record_action(action_result)
        
        # Обновляем статистику паттернов
        self._update_pattern_stats(action_result)
    
    def _update_pattern_stats(self, action_result: Dict[str, Any]) -> None:
        """
        Обновляет статистику паттернов.
        
        Args:
            action_result: Результат действия.
        """
        strategy = action_result.get("strategy", "unknown")
        success = action_result.get("success", False)
        
        if strategy not in self.pattern_stats:
            self.pattern_stats[strategy] = {
                "total": 0,
                "success": 0,
                "last_updated": time.time(),
            }
        
        self.pattern_stats[strategy]["total"] += 1
        if success:
            self.pattern_stats[strategy]["success"] += 1
        self.pattern_stats[strategy]["last_updated"] = time.time()
    
    def get_learning_progress(self) -> Dict[str, Any]:
        """
        Получает прогресс обучения.
        
        Returns:
            Словарь с метриками обучения.
        """
        if not self.pattern_stats:
            return {"message": "Недостаточно данных для обучения"}
        
        total_actions = sum(stat["total"] for stat in self.pattern_stats.values())
        total_success = sum(stat["success"] for stat in self.pattern_stats.values())
        success_rate = total_success / total_actions if total_actions > 0 else 0.0
        
        return {
            "total_actions": total_actions,
            "success_rate": success_rate,
            "strategies_count": len(self.pattern_stats),
        }
