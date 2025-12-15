"""
Модуль первой части методов выбора целей для AIPlayer.

Содержит методы для поиска оптимального угла удара и анализа траекторий.
"""

import math
from typing import List, Optional, Any

from .game_state import Point


class AIPlayerTargetSelectionPart1Mixin:
    """
    Миксин для первой части методов выбора целей.
    Добавляет методы поиска оптимального угла удара и анализа траекторий.
    """

    def _find_optimal_angle_for_max_destruction(self) -> Optional[Any]:
        """
        Находит оптимальный угол удара для максимизации количества разрушенных блоков.
        Используется на поздних этапах игры (<= 15 блоков).
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        landing_x = self._predict_exact_landing_position()
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_destruction_count = 0
        best_target_brick = None
        
        for offset in test_offsets:
            bounce_x = landing_x - (offset * paddle_half_width)
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state, paddle_y
            )
            
            if intersection_point is None:
                continue
            
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                first_hit_brick = self._find_first_brick_in_trajectory(
                    after_bounce_trajectory, self.current_game_state.remaining_bricks
                )
                if first_hit_brick:
                    best_target_brick = first_hit_brick
        
        if best_target_brick:
            return best_target_brick
        
        return self._find_best_target_for_few_bricks(
            self.current_game_state.remaining_bricks,
            paddle_y,
            self.current_game_state.ball_position.x,
        )

    def _count_bricks_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> int:
        """Подсчитывает количество блоков, которые будут разрушены траекторией."""
        if not trajectory or not bricks:
            return 0
        
        destroyed_bricks = set()
        ball_radius = self.config.ball.radius
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                brick_id = id(brick)
                if brick_id in destroyed_bricks:
                    continue
                
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        destroyed_bricks.add(brick_id)
        
        return len(destroyed_bricks)

    def _find_first_brick_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> Optional[Any]:
        """Находит первый блок, который будет разрушен траекторией."""
        if not trajectory or not bricks:
            return None
        
        ball_radius = self.config.ball.radius
        min_distance = float("inf")
        first_brick = None
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        distance = math.sqrt(
                            (point.x - trajectory[0].x) ** 2
                            + (point.y - trajectory[0].y) ** 2
                        )
                        
                        if distance < min_distance:
                            min_distance = distance
                            first_brick = brick
                            break
        
        return first_brick
