"""
Тесты для модуля logging_config.py
"""

import pytest
import logging
from unittest.mock import patch
from ai.logging_config import (
    get_log_level,
    get_log_level_name,
    get_logger,
    setup_root_logger,
    LOG_LEVEL,
)


class TestLoggingConfig:
    """Тесты для конфигурации логирования."""
    
    def test_get_log_level(self):
        """Тест получения уровня логирования."""
        level = get_log_level()
        assert isinstance(level, int)
        assert level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]
    
    def test_get_log_level_name(self):
        """Тест получения имени уровня логирования."""
        name = get_log_level_name()
        assert isinstance(name, str)
        assert name in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert name == LOG_LEVEL
    
    def test_get_logger(self):
        """Тест получения логгера."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.level == get_log_level()
    
    def test_setup_root_logger(self):
        """Тест настройки root логгера."""
        # Сохраняем текущее состояние
        root_logger = logging.getLogger()
        original_level = root_logger.level
        
        try:
            setup_root_logger()
            assert root_logger.level == get_log_level()
        finally:
            # Восстанавливаем оригинальный уровень
            root_logger.setLevel(original_level)
    
    def test_log_level_mapping(self):
        """Тест соответствия уровней логирования."""
        # Проверяем что текущий уровень логирования валиден
        level = get_log_level()
        assert level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]
        
        # Проверяем что имя уровня соответствует ожидаемому формату
        level_name = get_log_level_name()
        assert level_name in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

