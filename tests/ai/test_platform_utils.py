"""
Тесты для модуля platform_utils.py
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
from ai.platform_utils import is_frozen, get_ai_directory


class TestIsFrozen:
    """Тесты для функции is_frozen."""
    
    def test_is_frozen_false_by_default(self):
        """Тест что по умолчанию is_frozen возвращает False."""
        # Сохраняем оригинальные значения
        original_frozen = getattr(sys, 'frozen', None)
        original_meipass = getattr(sys, '_MEIPASS', None)
        original_frozendllhandle = getattr(sys, 'frozendllhandle', None)
        
        try:
            # Удаляем атрибуты если они есть
            if hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')
            if hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')
            if hasattr(sys, 'frozendllhandle'):
                delattr(sys, 'frozendllhandle')
            
            assert is_frozen() is False
        finally:
            # Восстанавливаем оригинальные значения
            if original_frozen is not None:
                sys.frozen = original_frozen
            if original_meipass is not None:
                sys._MEIPASS = original_meipass
            if original_frozendllhandle is not None:
                sys.frozendllhandle = original_frozendllhandle
    
    def test_is_frozen_with_sys_frozen(self):
        """Тест is_frozen когда sys.frozen установлен."""
        original_frozen = getattr(sys, 'frozen', None)
        try:
            sys.frozen = True
            assert is_frozen() is True
        finally:
            if original_frozen is not None:
                sys.frozen = original_frozen
            elif hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')
    
    def test_is_frozen_with_meipass(self):
        """Тест is_frozen когда sys._MEIPASS установлен."""
        original_meipass = getattr(sys, '_MEIPASS', None)
        try:
            sys._MEIPASS = "/some/path"
            assert is_frozen() is True
        finally:
            if original_meipass is not None:
                sys._MEIPASS = original_meipass
            elif hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')


class TestGetAIDirectory:
    """Тесты для функции get_ai_directory."""
    
    @patch('ai.platform_utils.is_frozen')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_get_ai_directory_not_frozen(self, mock_abspath, mock_dirname, mock_is_frozen):
        """Тест get_ai_directory когда приложение не заморожено."""
        mock_is_frozen.return_value = False
        mock_abspath.return_value = "/project/ai/platform_utils.py"
        mock_dirname.side_effect = lambda x: {
            "/project/ai/platform_utils.py": "/project/ai",
            "/project/ai": "/project",
        }.get(x, x)
        
        import os
        with patch('os.path.join', side_effect=os.path.join):
            result = get_ai_directory()
            assert "ai" in result
    
    @patch('ai.platform_utils.is_frozen')
    @patch('os.environ.get')
    @patch('os.path.join')
    @patch('os.makedirs')
    def test_get_ai_directory_frozen_with_localappdata(
        self, mock_makedirs, mock_join, mock_getenv, mock_is_frozen
    ):
        """Тест get_ai_directory когда приложение заморожено и есть LOCALAPPDATA."""
        mock_is_frozen.return_value = True
        mock_getenv.return_value = "/Users/AppData/Local"
        mock_join.side_effect = lambda *args: "/".join(args)
        
        result = get_ai_directory()
        assert result is not None

