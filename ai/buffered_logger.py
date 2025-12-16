"""
Буферизованный логгер для оптимизации производительности.

Этот модуль предоставляет BufferedLogger, который накапливает сообщения
в буфере и записывает их в файл за один раз, уменьшая количество операций
ввода-вывода и улучшая производительность.
"""

import logging
from typing import List, Optional


class BufferedLogger:
    """
    Буферизованный логгер для оптимизации производительности.

    Накапливает сообщения в буфере и записывает их в файл за один раз,
    уменьшая количество операций ввода-вывода.

    Args:
        buffer_size: Размер буфера (количество сообщений перед сбросом)
        max_buffer_size: Максимальный размер буфера (защита от переполнения)
    """

    def __init__(self, buffer_size: int = 100, max_buffer_size: int = 1000):
        """Инициализация буферизованного логгера."""
        self.buffer: List[str] = []
        self.buffer_size = buffer_size
        self.max_buffer_size = max_buffer_size
        self._logger: Optional[logging.Logger] = None
        self._handler: Optional[logging.Handler] = None

    def set_logger(self, logger: logging.Logger, handler: logging.Handler) -> None:
        """Устанавливает логгер и handler для записи."""
        self._logger = logger
        self._handler = handler

    def log(self, level: int, message: str, *args, **kwargs) -> None:
        """
        Добавляет сообщение в буфер.

        Args:
            level: Уровень логирования (logging.DEBUG, logging.INFO, etc.)
            message: Сообщение для логирования
            *args: Дополнительные аргументы
            **kwargs: Дополнительные ключевые аргументы
        """
        if self._logger is None:
            return

        # Форматируем сообщение
        formatted_message = self._logger._log.format(
            self._logger, level, message, args, **kwargs
        )

        # Добавляем в буфер
        self.buffer.append(formatted_message)

        # Проверяем, нужно ли сбросить буфер
        if len(self.buffer) >= self.buffer_size:
            self.flush()

        # Защита от переполнения буфера
        if len(self.buffer) > self.max_buffer_size:
            self.flush()

    def flush(self) -> None:
        """Записывает весь буфер в файл за один раз."""
        if not self.buffer or self._handler is None:
            return

        try:
            # Записываем все сообщения из буфера
            for message in self.buffer:
                self._handler.emit(
                    logging.LogRecord(
                        name=self._logger.name,
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=message,
                        args=(),
                        exc_info=None,
                    )
                )

            # Очищаем буфер
            self.buffer.clear()

        except Exception as e:
            # В случае ошибки очищаем буфер, чтобы избежать потери данных
            self.buffer.clear()
            if self._logger is not None:
                self._logger.error(
                    f"Ошибка при сбросе буферизованного логгера: {e}", exc_info=True
                )

    def debug(self, message: str, *args, **kwargs) -> None:
        """Логирует отладочное сообщение."""
        self.log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Логирует информационное сообщение."""
        self.log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Логирует предупреждение."""
        self.log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Логирует ошибку."""
        self.log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Логирует критическую ошибку."""
        self.log(logging.CRITICAL, message, *args, **kwargs)

    def __del__(self) -> None:
        """Деструктор - сбрасывает буфер при уничтожении объекта."""
        self.flush()


class BufferedLoggerAdapter(logging.LoggerAdapter):
    """
    Адаптер логгера, который перенаправляет вызовы в BufferedLogger.

    Используется для интеграции BufferedLogger с существующим кодом,
    который ожидает стандартный logging.Logger.
    """

    def __init__(self, logger: logging.Logger, buffered_logger: BufferedLogger):
        """Инициализация адаптера."""
        super().__init__(logger, {})
        self.buffered_logger = buffered_logger

    def debug(self, msg, *args, **kwargs) -> None:
        """Логирует отладочное сообщение."""
        self.buffered_logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs) -> None:
        """Логирует информационное сообщение."""
        self.buffered_logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs) -> None:
        """Логирует предупреждение."""
        self.buffered_logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs) -> None:
        """Логирует ошибку."""
        self.buffered_logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs) -> None:
        """Логирует критическую ошибку."""
        self.buffered_logger.critical(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs) -> None:
        """Логирует сообщение с указанным уровнем."""
        self.buffered_logger.log(level, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs) -> None:
        """Логирует исключение."""
        self.buffered_logger.error(msg, *args, **kwargs, exc_info=True)
