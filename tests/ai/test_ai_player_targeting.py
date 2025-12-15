"""
Тесты для модуля ai_player_targeting.py
"""

import pytest
import pygame
from unittest.mock import Mock
from ai.ai_player_targeting import AIPlayerTargetingMixin
from ai.game_state import GameState, Point
from ai.ai_player_models import TargetingSystem


class TestAIPlayerTargetingMixin:
    """Тесты для миксина AIPlayerTargetingMixin."""
    
    def test_generate_brick_cache_key_no_bricks(self):
        """Тест генерации ключа кэша без кирпичей."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        key = player._generate_brick_cache_key()
        
        assert key == ""
    
    def test_generate_brick_cache_key_with_bricks(self):
        """Тест генерации ключа кэша с кирпичами."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[
                        pygame.Rect(100, 50, 60, 20),
                        pygame.Rect(200, 50, 60, 20)
                    ],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.config = Mock()
                self.config.brick = Mock()
                self.config.brick.default_width = 60
        
        player = TestPlayer()
        key = player._generate_brick_cache_key()
        
        assert isinstance(key, str)
        assert len(key) > 0
        assert "100" in key or "200" in key
    
    def test_update_brick_map_no_bricks(self):
        """Тест обновления карты кирпичей без кирпичей."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.targeting_system = TargetingSystem()
                self._brick_map_cache = None
        
        player = TestPlayer()
        player._invalidate_trajectory_cache = Mock()
        player._update_visible_targets = Mock()
        
        player._update_brick_map()
        
        assert len(player.targeting_system.brick_map) == 0
        assert len(player.targeting_system.brick_coordinates) == 0
    
    def test_update_brick_map_with_bricks(self):
        """Тест обновления карты кирпичей с кирпичами."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[
                        pygame.Rect(100, 50, 60, 20),
                        pygame.Rect(200, 50, 60, 20)
                    ],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.targeting_system = TargetingSystem()
                self._brick_map_cache = None
                self._brick_cache_stats = {"hits": 0, "misses": 0}
                self.config = Mock()
                self.config.brick = Mock()
                self.config.brick.default_width = 60
                self.config.brick.default_height = 20
        
        player = TestPlayer()
        player._invalidate_trajectory_cache = Mock()
        player._update_visible_targets = Mock()
        
        player._update_brick_map()
        
        assert len(player.targeting_system.brick_map) > 0
        assert len(player.targeting_system.brick_coordinates) > 0
    
    def test_update_brick_map_cache_hit(self):
        """Тест использования кэша при обновлении карты."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                bricks = [pygame.Rect(100, 50, 60, 20)]
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=bricks,
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
                self.targeting_system = TargetingSystem()
                self._brick_cache_stats = {"hits": 0, "misses": 0}
                self._brick_map_cache = None
                self.config = Mock()
                self.config.brick = Mock()
                self.config.brick.default_width = 60
                self.config.brick.default_height = 20
        
        player = TestPlayer()
        player._invalidate_trajectory_cache = Mock()
        player._update_visible_targets = Mock()
        
        # Первый вызов - создает кэш
        player._update_brick_map()
        first_misses = player._brick_cache_stats["misses"]
        
        # Второй вызов - использует кэш
        player._update_brick_map()
        
        assert player._brick_cache_stats["hits"] > 0
    
    def test_record_hit_result(self):
        """Тест записи результата удара."""
        class TestPlayer(AIPlayerTargetingMixin):
            def __init__(self):
                self.targeting_system = TargetingSystem()
                self._logger = Mock()
                self.current_game_state = GameState(
                    ball_position=Point(400, 300),
                    ball_velocity=Point(5, -5),
                    paddle_position=Point(400, 550),
                    paddle_width=120,
                    remaining_bricks=[],
                    game_score=0,
                    game_time=0,
                    ball_speed=5,
                )
        
        player = TestPlayer()
        
        mock_brick = Mock()
        mock_brick.x = 100
        mock_brick.y = 50
        
        player.record_hit_result(mock_brick, paddle_offset=0.0, success=True)
        
        assert len(player.targeting_system.successful_hits) > 0

