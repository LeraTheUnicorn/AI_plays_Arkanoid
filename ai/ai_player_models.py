"""
Модели данных для AIPlayer.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class BrickInfo:
    """Информация о кирпиче."""

    x: float
    y: float
    width: int
    height: int
    center_x: float
    center_y: float
    row: int
    col: int

    @property
    def key(self) -> str:
        """Возвращает ключ для карты кирпичей."""
        return f"{self.col}_{self.row}"


@dataclass
class TargetingSystem:
    """Система прицельного отбивания."""

    target_brick: Optional[Any] = None
    optimal_offset: float = 0.0
    successful_hits: List[Dict[str, Any]] = field(default_factory=list)
    brick_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    trajectory_targets: List[Any] = field(default_factory=list)
    hit_patterns: Dict[str, Any] = field(default_factory=dict)
    brick_coordinates: List[Dict[str, Any]] = field(default_factory=list)
    visible_targets: List[Dict[str, Any]] = field(default_factory=list)
    recent_target_positions: List[float] = field(default_factory=list)

    def reset(self) -> None:
        """Сбрасывает состояние системы."""
        self.target_brick = None
        self.optimal_offset = 0.0
        self.successful_hits.clear()
        self.brick_map.clear()
        self.trajectory_targets.clear()
        self.hit_patterns.clear()
        self.brick_coordinates.clear()
        self.visible_targets.clear()
        self.recent_target_positions.clear()


@dataclass
class SeparationZoneTracker:
    """Отслеживание зоны разделения."""

    ball_entered_separation_zone: bool = False
    target_position_set: bool = False
    target_position: Optional[float] = None
    separation_zone_start: int = 226
    paddle_zone_start: int = 540
    paddle_moved_after_set: bool = False
    paddle_reached_target: bool = False
    last_movement_frame: int = 0
    frames_since_target_set: int = 0
    saved_ball_vel_x: Optional[float] = None
    game_restart_required: bool = False
    last_ball_vel_y: Optional[float] = (
        None  # КРИТИЧНО: Отслеживание предыдущего направления мяча
    )
    ball_moving_downward_last_frame: bool = (
        False  # КРИТИЧНО: Флаг движения мяча вниз на предыдущем кадре
    )

    def reset(self) -> None:
        """Сбрасывает состояние."""
        self.ball_entered_separation_zone = False
        self.target_position_set = False
        self.target_position = None
        self.paddle_moved_after_set = False
        self.paddle_reached_target = False
        self.last_movement_frame = 0
        self.frames_since_target_set = 0
        self.saved_ball_vel_x = None
        self.game_restart_required = False
        self.last_ball_vel_y = None
        self.ball_moving_downward_last_frame = False
