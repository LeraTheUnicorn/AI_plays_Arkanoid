"""
Асинхронный обработчик логирования с использованием QueueHandler и QueueListener.

Этот модуль предоставляет настройку логирования в отдельном потоке,
что предотвращает блокировку основного игрового цикла при записи логов.
"""

import logging
import logging.handlers
import queue
import threading
from typing import Optional


class AsyncLoggingSetup:
    """
    Настройка асинхронного логирования с использованием QueueHandler и QueueListener.

    Логи записываются в очередь и обрабатываются в отдельном потоке,
    что предотвращает блокировку основного потока игры.
    """

    def __init__(self):
        self.log_queue: Optional[queue.Queue] = None
        self.queue_handler: Optional[logging.handlers.QueueHandler] = None
        self.queue_listener: Optional[logging.handlers.QueueListener] = None
        self._listener_thread: Optional[threading.Thread] = None

    def setup_async_logging(
        self,
        file_handler: logging.Handler,
        log_level: int = logging.INFO,
        logger: Optional[logging.Logger] = None,
    ) -> logging.Logger:
        """
        Настраивает асинхронное логирование.

        Args:
            file_handler: Handler для записи в файл (например, RotatingLinesFileHandler)
            log_level: Уровень логирования
            logger: Логгер для настройки (если None, используется root logger)

        Returns:
            Настроенный логгер
        """
        # Если уже настроено, не настраиваем повторно
        if self.queue_listener is not None:
            return logger or logging.getLogger()

        # Создаем очередь для логов
        self.log_queue = queue.Queue(-1)  # Неограниченная очередь

        # Создаем QueueHandler, который будет отправлять логи в очередь
        self.queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.queue_handler.setLevel(log_level)

        # Создаем QueueListener, который будет обрабатывать логи в отдельном потоке
        # Он будет использовать file_handler для записи в файл
        self.queue_listener = logging.handlers.QueueListener(
            self.log_queue, file_handler, respect_handler_level=True
        )

        # Запускаем listener в отдельном потоке
        self.queue_listener.start()

        # Используем переданный logger или root logger
        target_logger = logger or logging.getLogger()
        target_logger.setLevel(log_level)

        # Добавляем QueueHandler к логгеру
        target_logger.addHandler(self.queue_handler)

        return target_logger

    def stop(self) -> None:
        """
        Останавливает асинхронное логирование.
        Должен вызываться при завершении программы.
        """
        if self.queue_listener:
            self.queue_listener.stop()
            self.queue_listener = None

        if self.queue_handler:
            self.queue_handler = None

        if self.log_queue:
            # Очищаем очередь
            try:
                while True:
                    self.log_queue.get_nowait()
            except queue.Empty:
                pass
            self.log_queue = None


# Глобальный экземпляр для управления асинхронным логированием
_async_logging_setup: Optional[AsyncLoggingSetup] = None


def get_async_logging_setup() -> AsyncLoggingSetup:
    """
    Получает глобальный экземпляр AsyncLoggingSetup.

    Returns:
        Глобальный экземпляр AsyncLoggingSetup
    """
    global _async_logging_setup
    if _async_logging_setup is None:
        _async_logging_setup = AsyncLoggingSetup()
    return _async_logging_setup


def stop_async_logging() -> None:
    """Останавливает асинхронное логирование."""
    global _async_logging_setup
    if _async_logging_setup:
        _async_logging_setup.stop()
        _async_logging_setup = None
