"""
Модуль для мониторинга производительности AI системы.
Отслеживает метрики времени выполнения операций, использование памяти, кэш и т.д.
"""

import time
import functools
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricEntry:
    """Запись метрики производительности"""

    operation_name: str
    duration: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Мониторинг производительности AI системы.
    Собирает метрики времени выполнения операций, использование кэша, память и т.д.
    """

    def __init__(self, max_history: int = 1000):
        """
        Инициализация монитора производительности.

        Args:
            max_history: Максимальное количество записей в истории для каждой метрики
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.Lock()

        # Специальные метрики
        self.cache_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"hits": 0, "misses": 0, "size": 0}
        )

        self.frame_times: deque = deque(maxlen=60)  # Последние 60 кадров
        self.memory_usage: List[float] = []

    def record_metric(
        self,
        operation_name: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Записывает метрику производительности.

        Args:
            operation_name: Название операции
            duration: Время выполнения в секундах
            metadata: Дополнительные данные
        """
        with self._lock:
            entry = MetricEntry(
                operation_name=operation_name,
                duration=duration,
                timestamp=time.time(),
                metadata=metadata or {},
            )
            self.metrics[operation_name].append(entry)

    def measure_time(
        self,
        operation_name: Optional[str] = None,
        include_args: bool = False,
        include_result: bool = False,
    ) -> Callable:
        """
        Декоратор для измерения времени выполнения функции.

        Args:
            operation_name: Имя операции (если None, используется имя функции)
            include_args: Включать ли аргументы в метаданные
            include_result: Включать ли результат в метаданные (может быть тяжелым)

        Returns:
            Декоратор функции
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    metadata: Dict[str, Any] = {}
                    if include_args:
                        metadata["args_count"] = len(args)
                        metadata["kwargs_count"] = len(kwargs)
                    if include_result:
                        metadata["result_type"] = type(result).__name__
                        if hasattr(result, "__len__"):
                            metadata["result_length"] = len(result)

                    self.record_metric(op_name, duration, metadata)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.record_metric(
                        op_name,
                        duration,
                        {"error": str(e), "error_type": type(e).__name__},
                    )
                    raise

            return wrapper

        return decorator

    def record_cache_hit(self, cache_name: str) -> None:
        """Записывает попадание в кэш"""
        with self._lock:
            self.cache_stats[cache_name]["hits"] += 1

    def record_cache_miss(self, cache_name: str) -> None:
        """Записывает промах кэша"""
        with self._lock:
            self.cache_stats[cache_name]["misses"] += 1

    def update_cache_size(self, cache_name: str, size: int) -> None:
        """Обновляет размер кэша"""
        with self._lock:
            self.cache_stats[cache_name]["size"] = size

    def record_frame_time(self, frame_time: float) -> None:
        """Записывает время обработки кадра"""
        with self._lock:
            self.frame_times.append(frame_time)

    def get_statistics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает статистику по метрикам.

        Args:
            operation_name: Имя операции (если None, возвращает общую статистику)

        Returns:
            Словарь со статистикой
        """
        with self._lock:
            if operation_name:
                if operation_name not in self.metrics:
                    return {}

                entries = list(self.metrics[operation_name])
                if not entries:
                    return {}

                durations = [e.duration for e in entries]
                return {
                    "operation": operation_name,
                    "count": len(entries),
                    "total_time": sum(durations),
                    "avg_time": sum(durations) / len(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                    "last_time": durations[-1] if durations else 0,
                }
            else:
                # Общая статистика
                stats = {}
                for op_name in self.metrics:
                    stats[op_name] = self.get_statistics(op_name)

                # Статистика кэша
                cache_stats = {}
                for cache_name, cache_data in self.cache_stats.items():
                    hits = cache_data["hits"]
                    misses = cache_data["misses"]
                    total = hits + misses
                    cache_stats[cache_name] = {
                        "hits": hits,
                        "misses": misses,
                        "hit_rate": hits / total if total > 0 else 0.0,
                        "size": cache_data["size"],
                    }

                # Статистика кадров
                frame_stats = {}
                if self.frame_times:
                    frame_times_list = list(self.frame_times)
                    frame_stats = {
                        "avg_frame_time": sum(frame_times_list) / len(frame_times_list),
                        "min_frame_time": min(frame_times_list),
                        "max_frame_time": max(frame_times_list),
                        "fps": (
                            1.0 / (sum(frame_times_list) / len(frame_times_list))
                            if frame_times_list
                            else 0
                        ),
                    }

                return {
                    "operations": stats,
                    "cache": cache_stats,
                    "frames": frame_stats,
                }

    def get_cache_hit_rate(self, cache_name: str) -> float:
        """
        Получает процент попаданий в кэш.

        Args:
            cache_name: Имя кэша

        Returns:
            Процент попаданий (0.0 - 1.0)
        """
        with self._lock:
            stats = self.cache_stats.get(cache_name, {"hits": 0, "misses": 0})
            total = stats["hits"] + stats["misses"]
            return stats["hits"] / total if total > 0 else 0.0

    def reset(self) -> None:
        """Сбрасывает все метрики"""
        with self._lock:
            self.metrics.clear()
            self.cache_stats.clear()
            self.frame_times.clear()
            self.memory_usage.clear()

    def get_summary(self) -> str:
        """
        Получает текстовую сводку производительности.

        Returns:
            Строка с краткой сводкой
        """
        stats = self.get_statistics()
        lines = ["=== Performance Monitor Summary ==="]

        # Операции
        if stats.get("operations"):
            lines.append("\nOperations:")
            for op_name, op_stats in stats["operations"].items():
                if op_stats:
                    lines.append(
                        f"  {op_name}: "
                        f"avg={op_stats['avg_time']*1000:.2f}ms, "
                        f"count={op_stats['count']}, "
                        f"total={op_stats['total_time']:.3f}s"
                    )

        # Кэш
        if stats.get("cache"):
            lines.append("\nCache:")
            for cache_name, cache_stats in stats["cache"].items():
                lines.append(
                    f"  {cache_name}: "
                    f"hit_rate={cache_stats['hit_rate']*100:.1f}%, "
                    f"hits={cache_stats['hits']}, "
                    f"misses={cache_stats['misses']}, "
                    f"size={cache_stats['size']}"
                )

        # Кадры
        if stats.get("frames"):
            frame_stats = stats["frames"]
            lines.append("\nFrames:")
            lines.append(
                f"  avg_frame_time={frame_stats['avg_frame_time']*1000:.2f}ms, "
                f"fps={frame_stats['fps']:.1f}"
            )

        return "\n".join(lines)


# Глобальный экземпляр монитора
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Получает глобальный экземпляр PerformanceMonitor (Singleton).

    Returns:
        Экземпляр PerformanceMonitor
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_global_monitor() -> None:
    """Сбрасывает глобальный монитор (для тестирования)"""
    global _global_monitor
    _global_monitor = None
