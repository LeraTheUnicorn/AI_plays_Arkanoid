"""
Тесты для модуля ai_player_cache.py
"""

import pytest
from unittest.mock import Mock
from ai.ai_player_cache import AIPlayerCacheMixin


class TestAIPlayerCacheMixin:
    """Тесты для миксина AIPlayerCacheMixin."""
    
    def test_get_brick_cache_stats_no_cache(self):
        """Тест получения статистики кэша без использования."""
        class TestPlayer(AIPlayerCacheMixin):
            def __init__(self):
                self._brick_cache_stats = {"hits": 0, "misses": 0}
        
        player = TestPlayer()
        stats = player.get_brick_cache_stats()
        
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0.0
    
    def test_get_brick_cache_stats_with_hits(self):
        """Тест получения статистики кэша с попаданиями."""
        class TestPlayer(AIPlayerCacheMixin):
            def __init__(self):
                self._brick_cache_stats = {"hits": 10, "misses": 5}
        
        player = TestPlayer()
        stats = player.get_brick_cache_stats()
        
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["total"] == 15
        assert stats["hit_rate"] == 10 / 15
    
    def test_get_brick_cache_stats_perfect_hit_rate(self):
        """Тест статистики с идеальным hit rate."""
        class TestPlayer(AIPlayerCacheMixin):
            def __init__(self):
                self._brick_cache_stats = {"hits": 20, "misses": 0}
        
        player = TestPlayer()
        stats = player.get_brick_cache_stats()
        
        assert stats["hit_rate"] == 1.0

