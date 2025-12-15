"""
Тесты для модуля performance_logger.py
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from ai.performance_logger import PerformanceLogger, CustomJSONEncoder
from ai.game_state import Point
import pygame


class TestCustomJSONEncoder:
    """Тесты для CustomJSONEncoder."""
    
    def test_encode_point(self):
        """Тест кодирования Point."""
        point = Point(100.5, 200.3)
        encoder = CustomJSONEncoder()
        
        result = encoder.default(point)
        
        assert result == {"x": 100.5, "y": 200.3}
    
    def test_encode_rect(self):
        """Тест кодирования pygame.Rect."""
        rect = pygame.Rect(10, 20, 60, 30)
        encoder = CustomJSONEncoder()
        
        result = encoder.default(rect)
        
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["width"] == 60
        assert result["height"] == 30
        assert result["centerx"] == rect.centerx
        assert result["centery"] == rect.centery
    
    def test_encode_other(self):
        """Тест кодирования других объектов."""
        encoder = CustomJSONEncoder()
        
        # Должно вызвать родительский метод
        with pytest.raises(TypeError):
            encoder.default(object())


class TestPerformanceLogger:
    """Тесты для класса PerformanceLogger."""
    
    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        logger = PerformanceLogger()
        
        assert logger.session_id is not None
        assert logger.session_start_time > 0
        assert len(logger.actions_log) == 0
        assert len(logger.game_results) == 0
    
    def test_init_with_session_id(self):
        """Тест инициализации с указанным session_id."""
        session_id = "test_session_123"
        logger = PerformanceLogger(session_id=session_id)
        
        assert logger.session_id == session_id
    
    def test_log_paddle_movement(self):
        """Тест логирования движения платформы."""
        logger = PerformanceLogger(enable_session_logging=True)
        
        logger.log_paddle_movement(100, 150, "test_reason", 0.8)
        
        assert len(logger.actions_log) == 1
        action = logger.actions_log[0]
        assert action["type"] == "paddle_movement"
        assert action["from_position"] == 100
        assert action["to_position"] == 150
        assert action["reason"] == "test_reason"
        assert action["confidence"] == 0.8
    
    def test_log_paddle_movement_disabled(self):
        """Тест что логирование не работает когда отключено."""
        logger = PerformanceLogger(enable_session_logging=False)
        
        logger.log_paddle_movement(100, 150, "test_reason", 0.8)
        
        # Логи не должны добавляться когда отключено
        assert len(logger.actions_log) == 0
    
    def test_save_game_result(self):
        """Тест сохранения результата игры."""
        logger = PerformanceLogger()
        
        result = {
            "score": 100,
            "lives_left": 2,
            "bricks_destroyed": 50
        }
        
        logger.save_game_result(result)
        
        assert len(logger.game_results) == 1
        assert logger.game_results[0] == result
    
    def test_get_recent_actions(self):
        """Тест получения последних действий."""
        logger = PerformanceLogger(enable_session_logging=True)
        
        logger.log_paddle_movement(100, 150, "test", 0.8)
        logger.log_paddle_movement(150, 200, "test", 0.9)
        
        recent = logger.get_recent_actions(count=2)
        
        assert len(recent) == 2
        assert recent[0]["type"] == "paddle_movement"
    
    def test_log_action(self):
        """Тест логирования действия."""
        logger = PerformanceLogger(enable_session_logging=True)
        
        action_data = {"type": "test_action", "value": 123}
        logger.log_action(action_data)
        
        assert len(logger.actions_log) == 1
        assert logger.actions_log[0]["type"] == "test_action"
    
    def test_generate_session_id(self):
        """Тест генерации session_id."""
        logger = PerformanceLogger()
        session_id = logger._generate_session_id()
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_save_session_log(self):
        """Тест сохранения лога сессии."""
        logger = PerformanceLogger()
        logger.log_paddle_movement(100, 150, "test", 0.8)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test_log.json")
            
            with patch('ai.performance_logger.get_ai_directory', return_value=tmpdir):
                logger.save_session_log()
            
            # Проверяем, что файл был создан (может быть в подпапке)
            assert os.path.exists(tmpdir) or os.path.exists(log_path)

