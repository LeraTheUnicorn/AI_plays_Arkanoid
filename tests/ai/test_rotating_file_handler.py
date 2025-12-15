"""
Тесты для модуля rotating_file_handler.py
"""

import pytest
import tempfile
import os
import logging
from ai.rotating_file_handler import RotatingLinesFileHandler


class TestRotatingLinesFileHandler:
    """Тесты для класса RotatingLinesFileHandler."""
    
    def test_init(self):
        """Тест инициализации handler."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            base_filename = f.name
        
        try:
            handler = RotatingLinesFileHandler(base_filename, max_lines=10)
            
            assert handler.base_filename == base_filename
            assert handler.max_lines == 10
            assert handler.current_file_number == 1
            assert handler.current_line_count == 0
            
            handler.close()
        finally:
            if os.path.exists(base_filename):
                os.unlink(base_filename)
    
    def test_get_current_filename(self):
        """Тест получения имени текущего файла."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            base_filename = f.name
        
        try:
            handler = RotatingLinesFileHandler(base_filename, max_lines=10)
            
            filename = handler._get_current_filename()
            
            assert "_1.log" in filename or "_1" in filename
            assert base_filename.split('.')[0] in filename
            
            handler.close()
        finally:
            if os.path.exists(base_filename):
                os.unlink(base_filename)
    
    def test_emit_single_line(self):
        """Тест записи одной строки."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            base_filename = f.name
        
        try:
            handler = RotatingLinesFileHandler(base_filename, max_lines=10)
            logger = logging.getLogger("test")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            logger.info("Test message")
            
            assert handler.current_line_count == 1
            
            handler.close()
            logger.removeHandler(handler)
        finally:
            if os.path.exists(base_filename):
                os.unlink(base_filename)
    
    def test_rotate_file(self):
        """Тест ротации файла."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            base_filename = f.name
        
        try:
            handler = RotatingLinesFileHandler(base_filename, max_lines=2)
            logger = logging.getLogger("test")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            # Записываем больше строк, чем max_lines
            logger.info("Message 1")
            logger.info("Message 2")
            logger.info("Message 3")  # Должна произойти ротация
            
            assert handler.current_file_number >= 2
            
            handler.close()
            logger.removeHandler(handler)
        finally:
            # Удаляем все созданные файлы
            base = base_filename.rsplit('.', 1)[0]
            for i in range(1, 5):
                filename = f"{base}_{i}.log"
                if os.path.exists(filename):
                    os.unlink(filename)

