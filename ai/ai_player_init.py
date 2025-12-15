"""
Модуль инициализации AIPlayer.

Содержит методы инициализации, валидации и настройки логирования.
"""

import os
import logging
from typing import Optional

from .logging_config import get_log_level, setup_root_logger
from .platform_utils import is_frozen, get_ai_directory
from .rotating_file_handler import RotatingLinesFileHandler


class AIPlayerInitMixin:
    """Миксин для методов инициализации AIPlayer."""

    _instance_counter = 0  # Счетчик для создания уникальных имен логгеров

    def _validate_dimensions(self, screen_width: int, screen_height: int) -> None:
        """
        Валидирует размеры экрана.
        
        Args:
            screen_width: Ширина экрана для валидации.
            screen_height: Высота экрана для валидации.
        
        Raises:
            TypeError: Если типы данных некорректны.
            ValueError: Если размеры некорректны.
        """
        if not isinstance(screen_width, int):
            raise TypeError(
                f"screen_width должен быть целым числом, получено: {type(screen_width).__name__}"
            )
        if not isinstance(screen_height, int):
            raise TypeError(
                f"screen_height должен быть целым числом, получено: {type(screen_height).__name__}"
            )
        if screen_width <= 0:
            raise ValueError(
                f"screen_width должен быть положительным, получено: {screen_width}"
            )
        if screen_height <= 0:
            raise ValueError(
                f"screen_height должен быть положительным, получено: {screen_height}"
            )
        if screen_width < 400 or screen_height < 300:
            raise ValueError(
                f"Минимальные размеры экрана: 400x300, получено: {screen_width}x{screen_height}"
            )

    @staticmethod
    def _get_env_bool(key: str, default: bool = True) -> bool:
        """
        Безопасно получает булево значение из переменной окружения.
        
        Args:
            key: Имя переменной окружения
            default: Значение по умолчанию
        
        Returns:
            Булево значение
        """
        try:
            value = os.getenv(key, "").strip().lower()
            if not value:
                return default
            return value in ("1", "true", "yes", "on")
        except (AttributeError, TypeError) as e:
            # В случае ошибки возвращаем значение по умолчанию
            # Используем модульный логгер, так как это статический метод
            # Root logger уже настроен через setup_root_logger(), используем его
            logger = logging.getLogger(__name__)
            logger.setLevel(get_log_level())  # Убеждаемся что уровень установлен
            logger.debug(f"Ошибка при чтении переменной окружения {key}: {e}", exc_info=True)
            return default

    @classmethod
    def _cleanup_old_logs(cls, logs_dir: str) -> None:
        """
        Очищает старые логи при запуске программы.
        Удаляет папки с датами, если в настройках установлен флаг delete_ai_logs_on_start.
        
        Args:
            logs_dir: Базовая директория с логами (logs/)
        """
        try:
            # Проверяем настройку удаления логов
            should_delete = True  # По умолчанию удаляем
            try:
                from ..game.settings import SettingsManager
                settings_manager = SettingsManager(lazy_load=False)
                should_delete = settings_manager.get_delete_ai_logs_on_start()
            except Exception as e:
                # Если не удалось загрузить настройки, используем значение по умолчанию
                if not is_frozen():
                    print(f"[LOG] Не удалось загрузить настройки для очистки логов: {e}, используем значение по умолчанию (удалять)")
            
            if not should_delete:
                if not is_frozen():
                    print("[LOG] Удаление логов при старте отключено в настройках")
                return
            
            if not os.path.exists(logs_dir):
                return
            
            # Удаляем все папки с датами (формат: YYYY-MM-DD_HH-MM-SS)
            import re
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$')
            
            deleted_count = 0
            for item in os.listdir(logs_dir):
                item_path = os.path.join(logs_dir, item)
                # Проверяем, является ли это папкой с датой
                if os.path.isdir(item_path) and date_pattern.match(item):
                    try:
                        import shutil
                        shutil.rmtree(item_path)
                        deleted_count += 1
                        if not is_frozen():
                            print(f"[LOG] Удалена папка с логами: {item}")
                    except Exception as e:
                        if not is_frozen():
                            print(f"[LOG] Не удалось удалить папку {item_path}: {e}")
            
            if deleted_count > 0 and not is_frozen():
                print(f"[LOG] Удалено папок с логами: {deleted_count}")
        except Exception as e:
            # Не блокируем выполнение при ошибке очистки
            if not is_frozen():
                print(f"[LOG] Ошибка при очистке старых логов: {e}")
    
    @classmethod
    def _setup_logging(cls) -> logging.Logger:
        """
        Настраивает и возвращает логгер для экземпляра AIPlayer.
        Логи записываются в файл с ротацией по 500 строк в папке с полной датой.
        
        Уровень логирования определяется ТОЛЬКО в logging_config.py через LOG_LEVEL.
        НЕ зависит от параметра debug_mode при создании AIPlayer.
        
        Returns:
            Настроенный логгер для этого экземпляра
        """
        # Создаем уникальный логгер для каждого экземпляра
        cls._instance_counter += 1
        logger_name = f"{__name__}.instance_{cls._instance_counter}"
        logger = logging.getLogger(logger_name)
        
        # Настраиваем handler только если еще не настроен
        if not logger.handlers:
            # Создаем базовую директорию для логов если её нет
            ai_dir = get_ai_directory()
            base_logs_dir = os.path.join(ai_dir, "logs")
            try:
                os.makedirs(base_logs_dir, exist_ok=True)
            except (OSError, PermissionError):
                base_logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
                os.makedirs(base_logs_dir, exist_ok=True)
            
            # Очищаем старые логи при первом запуске (когда создается первый экземпляр)
            if cls._instance_counter == 1:
                cls._cleanup_old_logs(base_logs_dir)
            
            # Создаем папку с полной датой для текущей сессии
            # Если папка с такой датой уже существует, добавляем 4-значный номер
            from datetime import datetime
            import re
            base_date_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logs_dir = os.path.join(base_logs_dir, base_date_folder)
            
            # Проверяем, существует ли папка с такой датой
            if os.path.exists(logs_dir):
                # Ищем все папки с таким же префиксом даты
                pattern = re.compile(r'^' + re.escape(base_date_folder) + r'_(\d{4})$')
                max_number = 0
                try:
                    for item in os.listdir(base_logs_dir):
                        item_path = os.path.join(base_logs_dir, item)
                        if os.path.isdir(item_path):
                            match = pattern.match(item)
                            if match:
                                number = int(match.group(1))
                                max_number = max(max_number, number)
                except Exception:
                    pass
                
                # Создаем папку с увеличенным номером
                date_folder = f"{base_date_folder}_{max_number + 1:04d}"
                logs_dir = os.path.join(base_logs_dir, date_folder)
            
            try:
                os.makedirs(logs_dir, exist_ok=True)
            except (OSError, PermissionError):
                # Fallback: используем базовую директорию
                logs_dir = base_logs_dir
            
            # Создаем ротирующий handler с инкрементными номерами файлов
            # ✅ ИСПРАВЛЕНО: Увеличено max_lines до 5000 для уменьшения частоты ротации
            # и предотвращения фризов из-за синхронной ротации файлов
            base_log_file = os.path.join(logs_dir, "ai_player.log")
            file_handler = RotatingLinesFileHandler(
                base_log_file,
                max_lines=5000,  # Увеличено с 500 до 5000 для уменьшения частоты ротации
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Получаем уровень логирования из централизованной конфигурации
            # ВАЖНО: уровень логирования настраивается ТОЛЬКО в logging_config.py
            log_level = get_log_level()
            
            # ✅ НОВОЕ: Используем асинхронное логирование для предотвращения фризов
            # Логи записываются в очередь и обрабатываются в отдельном потоке
            from .async_logging_handler import get_async_logging_setup
            async_setup = get_async_logging_setup()
            # Настраиваем асинхронное логирование (QueueHandler будет добавлен к logger)
            async_setup.setup_async_logging(file_handler, log_level, logger)
            
            # НЕ добавляем file_handler напрямую к logger - он используется через QueueListener
            # QueueHandler уже добавлен в setup_async_logging
            # Предотвращаем дублирование сообщений через родительские логгеры
            logger.propagate = False
        
        # Устанавливаем уровень логирования для этого экземпляра и handler
        # Используем централизованную конфигурацию из logging_config.py
        # ВАЖНО: уровень логирования настраивается ТОЛЬКО в logging_config.py
        log_level = get_log_level()
        
        # КРИТИЧНО: Устанавливаем уровень для логгера
        logger.setLevel(log_level)
        
        # КРИТИЧНО: Устанавливаем уровень для всех handlers этого логгера
        # Это обязательно - handler может иметь свой собственный уровень
        for handler in logger.handlers:  # type: ignore[assignment]
            handler.setLevel(log_level)
        
        # КРИТИЧНО: Убеждаемся, что root logger тоже настроен правильно
        root_logger = logging.getLogger()
        if root_logger.level > log_level:
            root_logger.setLevel(log_level)
            for root_handler in root_logger.handlers:
                if root_handler.level > log_level:
                    root_handler.setLevel(log_level)
        
        # Логируем установленный уровень для диагностики (только один раз при создании)
        logger.info(f"[LOGGING CONFIG] Уровень логирования установлен: {logging.getLevelName(log_level)} ({log_level}), logger.level={logger.level}, handler.level={[h.level for h in logger.handlers]}")
        
        return logger
