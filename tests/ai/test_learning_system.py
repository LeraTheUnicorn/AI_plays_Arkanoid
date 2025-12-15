"""
Тесты для модуля learning_system.py
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from ai.learning_system import LearningSystem
from ai.game_state import GameState, Point


class TestLearningSystem:
    """Тесты для класса LearningSystem."""
    
    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            assert system.model_path is not None
            assert system.learning_data is not None
            assert "strategy_weights" in system.learning_data
            assert "position_preferences" in system.learning_data
    
    def test_init_with_model_path(self):
        """Тест инициализации с указанным путем к модели."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            model_path = f.name
        
        try:
            system = LearningSystem(model_path=model_path)
            
            assert system.model_path == model_path
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_update_strategy_success(self):
        """Тест обновления стратегии при успешном действии."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir, \
             patch.object(LearningSystem, 'save_model') as mock_save:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_result = {
                "success": True,
                "action_type": "move",
                "confidence": 0.8,
                "movement_distance": 30,
                "time_taken": 0.05
            }
            
            system.update_strategy(action_result)
            
            mock_save.assert_called_once()
    
    def test_update_strategy_failure(self):
        """Тест обновления стратегии при неуспешном действии."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir, \
             patch.object(LearningSystem, 'save_model') as mock_save:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_result = {
                "success": False,
                "action_type": "move",
                "confidence": 0.6,
                "movement_distance": 20,
                "time_taken": 0.1
            }
            
            system.update_strategy(action_result)
            
            mock_save.assert_called_once()
    
    def test_update_strategy_invalid_input(self):
        """Тест обновления стратегии с некорректными данными."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            with pytest.raises(ValueError):
                system.update_strategy("not a dict")
            
            with pytest.raises(ValueError):
                system.update_strategy({})
    
    def test_determine_strategy_type_aggressive(self):
        """Тест определения агрессивной стратегии."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_result = {
                "movement_distance": 60,
                "time_taken": 0.05
            }
            
            strategy = system._determine_strategy_type(action_result)
            
            assert strategy == "aggressive"
    
    def test_determine_strategy_type_precision(self):
        """Тест определения стратегии точности."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_result = {
                "movement_distance": 5,
                "time_taken": 0.1
            }
            
            strategy = system._determine_strategy_type(action_result)
            
            assert strategy == "precision"
    
    def test_determine_strategy_type_conservative(self):
        """Тест определения консервативной стратегии."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_result = {
                "movement_distance": 25,
                "time_taken": 0.1
            }
            
            strategy = system._determine_strategy_type(action_result)
            
            assert strategy == "conservative"
    
    def test_save_model(self):
        """Тест сохранения модели."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            model_path = f.name
        
        try:
            with patch('ai.learning_system.get_ai_directory') as mock_dir:
                mock_dir.return_value = os.path.dirname(model_path)
                
                system = LearningSystem(model_path=model_path)
                system.learning_data["test_key"] = "test_value"
                
                system.save_model()
                
                assert os.path.exists(model_path)
                with open(model_path, 'r') as f:
                    data = json.load(f)
                    assert data.get("test_key") == "test_value"
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_load_model(self):
        """Тест загрузки модели."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            model_path = f.name
            model_data = {
                "strategy_weights": {"aggressive": 0.7, "conservative": 0.5, "precision": 0.5, "speed": 0.5},
                "position_preferences": {},
                "trajectory_patterns": {},
                "success_factors": {},
                "historical_performance": [],
                "learning_stats": {"total_learning_iterations": 10}
            }
            json.dump(model_data, f)
        
        try:
            with patch('ai.learning_system.get_ai_directory') as mock_dir:
                mock_dir.return_value = os.path.dirname(model_path)
                
                system = LearningSystem(model_path=model_path)
                system.load_model()
                
                assert system.learning_data.get("strategy_weights", {}).get("aggressive") == 0.7
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_get_strategy_recommendation(self):
        """Тест получения рекомендации стратегии."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            situation = {
                "ball_speed": 5,
                "bricks_remaining": 20,
                "distance_to_ball": 100
            }
            
            recommendation = system.get_strategy_recommendation(situation)
            
            assert isinstance(recommendation, dict)
            # Возвращает веса стратегий
            assert "aggressive" in recommendation or "conservative" in recommendation
    
    def test_predict_success_probability(self):
        """Тест предсказания вероятности успеха."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            action_plan = {
                "target_position": 400,
                "distance": 50,
                "time_available": 1.0
            }
            
            probability = system.predict_success_probability(action_plan)
            
            assert isinstance(probability, float)
            assert 0.0 <= probability <= 1.0
    
    def test_reset_learning_data(self):
        """Тест сброса данных обучения."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            system.learning_data["custom_key"] = "custom_value"
            
            system.reset_learning_data()
            
            assert "custom_key" not in system.learning_data
            assert "strategy_weights" in system.learning_data
    
    def test_get_learning_progress_no_iterations(self):
        """Тест получения прогресса обучения без итераций."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            
            progress = system.get_learning_progress()
            
            assert isinstance(progress, dict)
            assert "message" in progress
    
    def test_get_learning_progress_with_iterations(self):
        """Тест получения прогресса обучения с итерациями."""
        with patch('ai.learning_system.get_ai_directory') as mock_dir:
            mock_dir.return_value = tempfile.gettempdir()
            
            system = LearningSystem()
            system.learning_data["learning_stats"]["total_learning_iterations"] = 10
            system.learning_data["learning_stats"]["successful_adaptations"] = 7
            
            progress = system.get_learning_progress()
            
            assert isinstance(progress, dict)
            assert "total_iterations" in progress
            assert progress["total_iterations"] == 10

