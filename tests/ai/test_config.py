"""
Тесты для модуля config.py
"""

import pytest
from ai.config import AIConfig, GameZones, PaddleConfig, BrickConfig, BallConfig


class TestGameZones:
    """Тесты для класса GameZones."""
    
    def test_game_zones_creation(self):
        """Тест создания конфигурации зон."""
        zones = GameZones()
        assert zones.bricks_zone_end == 210
        assert zones.ball_diameter == 16
        assert zones.paddle_zone_offset == 60
        assert zones.ball_reset_height == 50
    
    def test_separation_zone_start(self):
        """Тест вычисления начала зоны разделения."""
        zones = GameZones()
        expected = zones.bricks_zone_end + zones.ball_diameter
        assert zones.separation_zone_start == expected
    
    def test_paddle_zone_start(self):
        """Тест вычисления начала зоны платформы."""
        zones = GameZones()
        screen_height = 600
        expected = screen_height - zones.paddle_zone_offset
        assert zones.paddle_zone_start(screen_height) == expected


class TestPaddleConfig:
    """Тесты для класса PaddleConfig."""
    
    def test_paddle_config_creation(self):
        """Тест создания конфигурации платформы."""
        config = PaddleConfig()
        assert config.width == 120
        assert config.safe_margin == 30
        assert config.min_movement_distance == 5
        assert config.zone_size == 40
        assert config.zone_half == 20
        assert config.edge_proximity_threshold == 40


class TestBrickConfig:
    """Тесты для класса BrickConfig."""
    
    def test_brick_config_creation(self):
        """Тест создания конфигурации кирпичей."""
        config = BrickConfig()
        assert config.default_width == 60
        assert config.default_height == 30
        assert config.precision_targeting_threshold == 10


class TestBallConfig:
    """Тесты для класса BallConfig."""
    
    def test_ball_config_creation(self):
        """Тест создания конфигурации мяча."""
        config = BallConfig()
        assert config.diameter == 16
        assert config.radius == 8
        assert config.default_speed == 5
        assert config.velocity_tolerance == 0.1


class TestAIConfig:
    """Тесты для класса AIConfig."""
    
    def test_ai_config_creation(self):
        """Тест создания основной конфигурации AI."""
        config = AIConfig()
        assert isinstance(config.zones, GameZones)
        assert isinstance(config.paddle, PaddleConfig)
        assert isinstance(config.brick, BrickConfig)
        assert isinstance(config.ball, BallConfig)
        assert config.debug_log_interval == 100
        assert config.loop_detection_threshold == 5
        assert config.max_empty_bounces == 1
        assert config.precision_priority_threshold == 10
        assert config.success_probability_threshold == 0.5
        assert config.low_success_probability_threshold == 0.2
        assert config.confidence_default == 0.7
        assert config.debug_log_chance == 0.1
        assert config.recent_targets_max == 5
        assert config.successful_hits_max == 100
        assert config.successful_hits_keep == 50
    
    def test_ai_config_immutability(self):
        """Тест неизменяемости конфигурации (frozen dataclass)."""
        config = AIConfig()
        with pytest.raises(Exception):  # frozen dataclass не позволяет изменять поля
            config.debug_log_interval = 200

