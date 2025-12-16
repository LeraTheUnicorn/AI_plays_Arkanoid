"""
Модуль кэширования AIPlayer.

Содержит методы работы с кэшем кирпичей и статистикой кэша.
"""

from typing import Dict, Any


class AIPlayerCacheMixin:
    """Миксин для методов кэширования AIPlayer."""

    # Аннотация типа для статического анализатора
    _brick_cache_stats: Dict[str, int]

    def get_brick_cache_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования кэша карты кирпичей.

        Returns:
            Словарь со статистикой: hits, misses, hit_rate
        """
        total = self._brick_cache_stats["hits"] + self._brick_cache_stats["misses"]
        hit_rate = self._brick_cache_stats["hits"] / total if total > 0 else 0.0
        return {
            "hits": self._brick_cache_stats["hits"],
            "misses": self._brick_cache_stats["misses"],
            "total": total,
            "hit_rate": hit_rate,
        }
