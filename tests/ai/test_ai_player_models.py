"""
Тесты для модуля ai_player_models.py
"""

import pytest
from unittest.mock import Mock
from ai.ai_player_models import BrickInfo, TargetingSystem, SeparationZoneTracker


class TestBrickInfo:
    """Тесты для класса BrickInfo."""
    
    def test_brick_info_creation(self):
        """Тест создания BrickInfo."""
        brick = BrickInfo(
            x=100.0,
            y=50.0,
            width=60,
            height=20,
            center_x=130.0,
            center_y=60.0,
            row=0,
            col=1
        )
        
        assert brick.x == 100.0
        assert brick.y == 50.0
        assert brick.width == 60
        assert brick.height == 20
        assert brick.center_x == 130.0
        assert brick.center_y == 60.0
        assert brick.row == 0
        assert brick.col == 1
    
    def test_brick_info_key(self):
        """Тест свойства key."""
        brick = BrickInfo(
            x=100.0,
            y=50.0,
            width=60,
            height=20,
            center_x=130.0,
            center_y=60.0,
            row=2,
            col=3
        )
        
        assert brick.key == "3_2"
    
    def test_brick_info_key_unique(self):
        """Тест уникальности ключей."""
        brick1 = BrickInfo(0, 0, 60, 20, 30, 10, 0, 0)
        brick2 = BrickInfo(0, 0, 60, 20, 30, 10, 1, 0)
        brick3 = BrickInfo(0, 0, 60, 20, 30, 10, 0, 1)
        
        assert brick1.key != brick2.key
        assert brick1.key != brick3.key
        assert brick2.key != brick3.key


class TestTargetingSystem:
    """Тесты для класса TargetingSystem."""
    
    def test_targeting_system_creation(self):
        """Тест создания TargetingSystem."""
        system = TargetingSystem()
        
        assert system.target_brick is None
        assert system.optimal_offset == 0.0
        assert len(system.successful_hits) == 0
        assert len(system.brick_map) == 0
        assert len(system.trajectory_targets) == 0
    
    def test_targeting_system_reset(self):
        """Тест сброса TargetingSystem."""
        system = TargetingSystem()
        system.target_brick = Mock()
        system.optimal_offset = 10.5
        system.successful_hits.append({"test": "data"})
        system.brick_map["key"] = {"data": "value"}
        
        system.reset()
        
        assert system.target_brick is None
        assert system.optimal_offset == 0.0
        assert len(system.successful_hits) == 0
        assert len(system.brick_map) == 0
        assert len(system.trajectory_targets) == 0
        assert len(system.hit_patterns) == 0
        assert len(system.brick_coordinates) == 0
        assert len(system.visible_targets) == 0
        assert len(system.recent_target_positions) == 0
    
    def test_targeting_system_with_data(self):
        """Тест TargetingSystem с данными."""
        system = TargetingSystem()
        system.target_brick = {"x": 100, "y": 50}
        system.optimal_offset = 5.0
        system.successful_hits = [{"hit": 1}, {"hit": 2}]
        
        assert system.target_brick == {"x": 100, "y": 50}
        assert system.optimal_offset == 5.0
        assert len(system.successful_hits) == 2


class TestSeparationZoneTracker:
    """Тесты для класса SeparationZoneTracker."""
    
    def test_separation_zone_tracker_creation(self):
        """Тест создания SeparationZoneTracker."""
        tracker = SeparationZoneTracker()
        
        assert tracker.ball_entered_separation_zone is False
        assert tracker.target_position_set is False
        assert tracker.target_position is None
        assert tracker.separation_zone_start == 226
        assert tracker.paddle_zone_start == 540
    
    def test_separation_zone_tracker_reset(self):
        """Тест сброса SeparationZoneTracker."""
        tracker = SeparationZoneTracker()
        tracker.ball_entered_separation_zone = True
        tracker.target_position_set = True
        tracker.target_position = 400.0
        tracker.paddle_moved_after_set = True
        tracker.paddle_reached_target = True
        tracker.last_movement_frame = 100
        tracker.frames_since_target_set = 50
        tracker.saved_ball_vel_x = 5.0
        tracker.game_restart_required = True
        tracker.last_ball_vel_y = -5.0
        tracker.ball_moving_downward_last_frame = True
        
        tracker.reset()
        
        assert tracker.ball_entered_separation_zone is False
        assert tracker.target_position_set is False
        assert tracker.target_position is None
        assert tracker.paddle_moved_after_set is False
        assert tracker.paddle_reached_target is False
        assert tracker.last_movement_frame == 0
        assert tracker.frames_since_target_set == 0
        assert tracker.saved_ball_vel_x is None
        assert tracker.game_restart_required is False
        assert tracker.last_ball_vel_y is None
        assert tracker.ball_moving_downward_last_frame is False
    
    def test_separation_zone_tracker_with_data(self):
        """Тест SeparationZoneTracker с данными."""
        tracker = SeparationZoneTracker()
        tracker.target_position = 350.0
        tracker.ball_entered_separation_zone = True
        
        assert tracker.target_position == 350.0
        assert tracker.ball_entered_separation_zone is True

