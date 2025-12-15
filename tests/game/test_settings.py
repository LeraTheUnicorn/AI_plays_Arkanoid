"""
Тесты для модуля settings.py
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from game.settings import SettingsManager, SettingsConstants, SettingsValidator


class TestSettingsConstants:
    """Тесты для SettingsConstants."""
    
    def test_default_ball_speed(self):
        """Тест константы скорости мяча по умолчанию."""
        assert SettingsConstants.DEFAULT_BALL_SPEED == 8
        assert SettingsConstants.MIN_BALL_SPEED == 1
        assert SettingsConstants.MAX_BALL_SPEED == 10
    
    def test_get_max_ball_speed(self):
        """Тест метода get_max_ball_speed."""
        assert SettingsConstants.get_max_ball_speed() == 10
    
    def test_validate_ball_speed_range(self):
        """Тест валидации диапазона скорости."""
        assert SettingsConstants.validate_ball_speed_range(5) is True
        assert SettingsConstants.validate_ball_speed_range(1) is True
        assert SettingsConstants.validate_ball_speed_range(10) is True
        assert SettingsConstants.validate_ball_speed_range(0) is False
        assert SettingsConstants.validate_ball_speed_range(11) is False


class TestSettingsValidator:
    """Тесты для SettingsValidator."""
    
    def test_validate_ball_speed_valid(self):
        """Тест валидации валидной скорости."""
        speed = SettingsValidator.validate_ball_speed(7)
        assert speed == 7
    
    def test_validate_ball_speed_invalid_type(self):
        """Тест валидации некорректного типа."""
        speed = SettingsValidator.validate_ball_speed("invalid")
        assert speed == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_validate_ball_speed_out_of_range(self):
        """Тест валидации скорости вне диапазона."""
        speed = SettingsValidator.validate_ball_speed(20)
        assert speed == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_validate_settings(self):
        """Тест валидации настроек."""
        settings = {
            "ball_speed": 6,
            "delete_ai_logs_on_start": True
        }
        validated = SettingsValidator.validate_settings(settings)
        
        assert validated["ball_speed"] == 6
        assert validated["delete_ai_logs_on_start"] is True


class TestSettingsManager:
    """Тесты для класса SettingsManager."""
    
    def test_init_lazy_load(self):
        """Тест инициализации с lazy_load."""
        manager = SettingsManager(lazy_load=True)
        
        assert manager is not None
    
    def test_get_ball_speed(self):
        """Тест получения скорости мяча."""
        manager = SettingsManager(lazy_load=True)
        speed = manager.get_ball_speed()
        
        assert isinstance(speed, int)
        assert 1 <= speed <= 10
    
    def test_set_ball_speed(self):
        """Тест установки скорости мяча."""
        manager = SettingsManager(lazy_load=True)
        
        manager.set_ball_speed(7)
        speed = manager.get_ball_speed()
        
        assert speed == 7
    
    def test_get_delete_ai_logs_on_start(self):
        """Тест получения настройки удаления логов."""
        manager = SettingsManager(lazy_load=True)
        should_delete = manager.get_delete_ai_logs_on_start()
        
        assert isinstance(should_delete, bool)
    
    def test_set_delete_ai_logs_on_start(self):
        """Тест установки настройки удаления логов."""
        manager = SettingsManager(lazy_load=True)
        
        manager.set_delete_ai_logs_on_start(False)
        should_delete = manager.get_delete_ai_logs_on_start()
        
        assert should_delete is False

