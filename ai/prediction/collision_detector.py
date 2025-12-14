"""
Детектор столкновений.

Отвечает за:
- Обнаружение столкновений мяча с кубиками
- Проверку пересечения траектории с объектами
- Анализ возможных столкновений
"""

import math
from typing import List, Optional, Any, Tuple

from ..game_state import GameState, Point
from ..config import AIConfig


class CollisionDetector:
    """
    Детектор столкновений.
    
    Отвечает за:
    - Обнаружение столкновений мяча с кубиками
    - Проверку пересечения траектории с объектами
    - Анализ возможных столкновений
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Инициализация CollisionDetector.
        
        Args:
            screen_width: Ширина игрового экрана.
            screen_height: Высота игрового экрана.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = AIConfig()
        
        # Состояние игры
        self.current_game_state: Optional[GameState] = None
    
    def update_game_state(self, game_state: GameState) -> None:
        """Обновляет состояние игры."""
        self.current_game_state = game_state
    
    def check_ball_brick_collision(self, ball_x: float, ball_y: float, ball_radius: float, brick: Any) -> bool:
        """
        Проверяет столкновение мяча с кубиком.
        
        Args:
            ball_x: X-координата мяча.
            ball_y: Y-координата мяча.
            ball_radius: Радиус мяча.
            brick: Объект кубика.
            
        Returns:
            True, если столкновение обнаружено, False иначе.
        """
        brick_x = getattr(brick, "x", 0)
        brick_y = getattr(brick, "y", 0)
        brick_width = getattr(brick, "width", self.config.brick.default_width)
        brick_height = getattr(brick, "height", 20)
        
        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height
        
        closest_x = max(brick_left, min(ball_x, brick_right))
        closest_y = max(brick_top, min(ball_y, brick_bottom))
        distance_x = ball_x - closest_x
        distance_y = ball_y - closest_y
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2)
        
        return distance <= ball_radius
    
    def check_trajectory_brick_collision(self, trajectory: List[Point], brick: Any) -> bool:
        """
        Проверяет столкновение траектории с кубиком.
        
        Args:
            trajectory: Траектория мяча.
            brick: Объект кубика.
            
        Returns:
            True, если столкновение обнаружено, False иначе.
        """
        if not trajectory:
            return False
        
        brick_x = getattr(brick, "x", 0)
        brick_y = getattr(brick, "y", 0)
        brick_width = getattr(brick, "width", self.config.brick.default_width)
        brick_height = getattr(brick, "height", 20)
        ball_radius = self.config.ball.radius
        
        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
            
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
                    return True
        
        return False
    
    def find_closest_brick(self, ball_x: float, ball_y: float) -> Optional[Tuple[Any, float]]:
        """
        Находит ближайший кубик к мячу.
        
        Args:
            ball_x: X-координата мяча.
            ball_y: Y-координата мяча.
            
        Returns:
            Кортеж (ближайший кубик, расстояние) или None, если кубиков нет.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        closest_brick = None
        min_distance = float('inf')
        
        for brick in self.current_game_state.remaining_bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            
            brick_center_x = brick_x + brick_width / 2
            brick_center_y = brick_y + brick_height / 2
            
            distance = math.sqrt(
                (ball_x - brick_center_x) ** 2 + (ball_y - brick_center_y) ** 2
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_brick = brick
        
        return (closest_brick, min_distance) if closest_brick else None
    
    def find_bricks_in_trajectory(self, trajectory: List[Point]) -> List[Any]:
        """
        Находит все кубики, которые пересекает траектория.
        
        Args:
            trajectory: Траектория мяча.
            
        Returns:
            Список кубиков, которые пересекает траектория.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks or not trajectory:
            return []
        
        hit_bricks = []
        ball_radius = self.config.ball.radius
        
        for brick in self.current_game_state.remaining_bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            
            brick_left = brick_x
            brick_right = brick_x + brick_width
            brick_top = brick_y
            brick_bottom = brick_y + brick_height
            
            for point in trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue
                
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
                        hit_bricks.append(brick)
                        break
        
        return hit_bricks
    
    def predict_collision_point(self, ball_x: float, ball_y: float, vel_x: float, vel_y: float, brick: Any) -> Optional[Point]:
        """
        Предсказывает точку столкновения мяча с кубиком.
        
        Args:
            ball_x: X-координата мяча.
            ball_y: Y-координата мяча.
            vel_x: X-скорость мяча.
            vel_y: Y-скорость мяча.
            brick: Объект кубика.
            
        Returns:
            Точка столкновения или None, если столкновение невозможно.
        """
        brick_x = getattr(brick, "x", 0)
        brick_y = getattr(brick, "y", 0)
        brick_width = getattr(brick, "width", self.config.brick.default_width)
        brick_height = getattr(brick, "height", 20)
        ball_radius = self.config.ball.radius
        
        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height
        
        if vel_y == 0:
            return None
        
        time_to_top = (brick_top - ball_radius - ball_y) / vel_y if vel_y < 0 else float('inf')
        time_to_bottom = (brick_bottom + ball_radius - ball_y) / vel_y if vel_y > 0 else float('inf')
        time_to_left = (brick_left - ball_radius - ball_x) / vel_x if vel_x < 0 else float('inf')
        time_to_right = (brick_right + ball_radius - ball_x) / vel_x if vel_x > 0 else float('inf')
        
        min_time = min(time_to_top, time_to_bottom, time_to_left, time_to_right)
        
        if min_time < 0:
            return None
        
        collision_x = ball_x + vel_x * min_time
        collision_y = ball_y + vel_y * min_time
        
        if (
            brick_left - ball_radius <= collision_x <= brick_right + ball_radius
            and brick_top - ball_radius <= collision_y <= brick_bottom + ball_radius
        ):
            return Point(collision_x, collision_y)
        
        return None
    
    def check_wall_collision(self, ball_x: float, ball_y: float, vel_x: float, vel_y: float) -> Optional[str]:
        """
        Проверяет столкновение мяча со стенами.
        
        Args:
            ball_x: X-координата мяча.
            ball_y: Y-координата мяча.
            vel_x: X-скорость мяча.
            vel_y: Y-скорость мяча.
            
        Returns:
            Направление столкновения ('left', 'right', 'top', 'bottom') или None, если столкновения нет.
        """
        ball_radius = self.config.ball.radius
        
        if ball_x - ball_radius < 0 and vel_x < 0:
            return 'left'
        if ball_x + ball_radius > self.screen_width and vel_x > 0:
            return 'right'
        if ball_y - ball_radius < 0 and vel_y < 0:
            return 'top'
        if ball_y + ball_radius > self.screen_height and vel_y > 0:
            return 'bottom'
        
        return None
