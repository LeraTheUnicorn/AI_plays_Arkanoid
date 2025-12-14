"""
Двигатель расчета траекторий.

Отвечает за:
- Предсказание траектории мяча
- Определение точки пересечения с платформой
- Расчет траектории после отскока
"""

import math
from typing import List, Optional, Any

from ..game_state import GameState, Point
from ..config import AIConfig


class TrajectoryEngine:
    """
    Двигатель расчета траекторий.
    
    Отвечает за:
    - Предсказание траектории мяча
    - Определение точки пересечения с платформой
    - Расчет траектории после отскока
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Инициализация TrajectoryEngine.
        
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
    
    def predict_paddle_intersection(self, game_state: GameState, paddle_y: float) -> Optional[Point]:
        """
        Предсказывает точку пересечения мяча с платформой.
        
        Args:
            game_state: Текущее состояние игры.
            paddle_y: Y-координата платформы.
            
        Returns:
            Точка пересечения или None, если предсказание невозможно.
        """
        if not game_state:
            return None
        
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        if vel_y >= 0:
            return None
        
        ball_radius = self.config.ball.radius
        paddle_height = 15
        paddle_top = paddle_y - paddle_height / 2
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return None
        
        time_to_paddle = distance_y / abs(vel_y)
        predicted_x = ball_x + vel_x * time_to_paddle
        
        min_center_x = ball_radius
        max_center_x = self.screen_width - ball_radius
        
        while predicted_x < min_center_x or predicted_x > max_center_x:
            if predicted_x < min_center_x:
                predicted_x = 2 * min_center_x - predicted_x
                vel_x = abs(vel_x)
            elif predicted_x > max_center_x:
                predicted_x = 2 * max_center_x - predicted_x
                vel_x = -abs(vel_x)
        
        return Point(predicted_x, paddle_top + ball_radius)
    
    def predict_after_bounce_trajectory(
        self, game_state: GameState, intersection_point: Point, bounce_x: float
    ) -> List[Point]:
        """
        Предсказывает траекторию мяча после отскока от платформы.
        
        Args:
            game_state: Текущее состояние игры.
            intersection_point: Точка пересечения с платформой.
            bounce_x: X-координата точки отскока на платформе.
            
        Returns:
            Список точек траектории после отскока.
        """
        if not game_state or not intersection_point:
            return []
        
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        paddle_y = game_state.paddle_position.y
        paddle_height = 15
        paddle_top = paddle_y - paddle_height / 2
        
        trajectory = []
        current_x = intersection_point.x
        current_y = intersection_point.y
        current_vel_x = vel_x
        current_vel_y = -vel_y
        
        ball_radius = self.config.ball.radius
        min_center_x = ball_radius
        max_center_x = self.screen_width - ball_radius
        min_center_y = ball_radius
        max_center_y = self.screen_height - ball_radius
        
        max_points = 100
        for _ in range(max_points):
            trajectory.append(Point(current_x, current_y))
            
            if current_vel_y >= 0 and current_y >= max_center_y:
                current_y = max_center_y
                current_vel_y = -current_vel_y
                trajectory.append(Point(current_x, current_y))
                continue
            
            if current_vel_x != 0:
                time_to_wall_x = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else (current_x - min_center_x) / abs(current_vel_x)
            else:
                time_to_wall_x = float('inf')
            
            if current_vel_y != 0:
                time_to_wall_y = (max_center_y - current_y) / current_vel_y if current_vel_y > 0 else (current_y - min_center_y) / abs(current_vel_y)
            else:
                time_to_wall_y = float('inf')
            
            time_to_wall = min(time_to_wall_x, time_to_wall_y)
            
            if time_to_wall <= 0:
                break
            
            new_x = current_x + current_vel_x * time_to_wall
            new_y = current_y + current_vel_y * time_to_wall
            
            if new_x < min_center_x or new_x > max_center_x:
                current_x = new_x
                current_vel_x = -current_vel_x
                if new_x < min_center_x:
                    current_x = min_center_x
                else:
                    current_x = max_center_x
            elif new_y < min_center_y or new_y > max_center_y:
                current_y = new_y
                current_vel_y = -current_vel_y
                if new_y < min_center_y:
                    current_y = min_center_y
                else:
                    current_y = max_center_y
            else:
                current_x = new_x
                current_y = new_y
                break
        
        return trajectory
    
    def get_optimized_trajectory(self, game_state: GameState, max_relevant_points: int = 50) -> List[Point]:
        """
        Получает оптимизированную траекторию мяча.
        
        Args:
            game_state: Текущее состояние игры.
            max_relevant_points: Максимальное количество точек траектории.
            
        Returns:
            Список точек оптимизированной траектории.
        """
        if not game_state:
            return []
        
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        if vel_y >= 0:
            return []
        
        ball_radius = self.config.ball.radius
        paddle_y = game_state.paddle_position.y
        paddle_height = 15
        paddle_top = paddle_y - paddle_height / 2
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return []
        
        time_to_paddle = distance_y / abs(vel_y)
        
        trajectory = []
        current_x = ball_x
        current_y = ball_y
        current_vel_x = vel_x
        current_vel_y = vel_y
        
        min_center_x = ball_radius
        max_center_x = self.screen_width - ball_radius
        min_center_y = ball_radius
        max_center_y = self.screen_height - ball_radius
        
        for _ in range(max_relevant_points):
            trajectory.append(Point(current_x, current_y))
            
            if current_vel_y >= 0 and current_y >= max_center_y:
                current_y = max_center_y
                current_vel_y = -current_vel_y
                trajectory.append(Point(current_x, current_y))
                continue
            
            if current_vel_x != 0:
                time_to_wall_x = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else (current_x - min_center_x) / abs(current_vel_x)
            else:
                time_to_wall_x = float('inf')
            
            if current_vel_y != 0:
                time_to_wall_y = (max_center_y - current_y) / current_vel_y if current_vel_y > 0 else (current_y - min_center_y) / abs(current_vel_y)
            else:
                time_to_wall_y = float('inf')
            
            time_to_wall = min(time_to_wall_x, time_to_wall_y)
            
            if time_to_wall <= 0:
                break
            
            new_x = current_x + current_vel_x * time_to_wall
            new_y = current_y + current_vel_y * time_to_wall
            
            if new_x < min_center_x or new_x > max_center_x:
                current_x = new_x
                current_vel_x = -current_vel_x
                if new_x < min_center_x:
                    current_x = min_center_x
                else:
                    current_x = max_center_x
            elif new_y < min_center_y or new_y > max_center_y:
                current_y = new_y
                current_vel_y = -current_vel_y
                if new_y < min_center_y:
                    current_y = min_center_y
                else:
                    current_y = max_center_y
            else:
                current_x = new_x
                current_y = new_y
                break
        
        return trajectory
    
    def get_adaptive_trajectory(self, game_state: GameState, ball_y: float, paddle_y: float) -> List[Point]:
        """
        Получает адаптивную траекторию мяча.
        
        Args:
            game_state: Текущее состояние игры.
            ball_y: Y-координата мяча.
            paddle_y: Y-координата платформы.
            
        Returns:
            Список точек адаптивной траектории.
        """
        if not game_state:
            return []
        
        ball_x = game_state.ball_position.x
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        if vel_y >= 0:
            return []
        
        ball_radius = self.config.ball.radius
        paddle_height = 15
        paddle_top = paddle_y - paddle_height / 2
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return []
        
        time_to_paddle = distance_y / abs(vel_y)
        
        trajectory = []
        current_x = ball_x
        current_y = ball_y
        current_vel_x = vel_x
        current_vel_y = vel_y
        
        min_center_x = ball_radius
        max_center_x = self.screen_width - ball_radius
        min_center_y = ball_radius
        max_center_y = self.screen_height - ball_radius
        
        max_points = 100
        for _ in range(max_points):
            trajectory.append(Point(current_x, current_y))
            
            if current_vel_y >= 0 and current_y >= max_center_y:
                current_y = max_center_y
                current_vel_y = -current_vel_y
                trajectory.append(Point(current_x, current_y))
                continue
            
            if current_vel_x != 0:
                time_to_wall_x = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else (current_x - min_center_x) / abs(current_vel_x)
            else:
                time_to_wall_x = float('inf')
            
            if current_vel_y != 0:
                time_to_wall_y = (max_center_y - current_y) / current_vel_y if current_vel_y > 0 else (current_y - min_center_y) / abs(current_vel_y)
            else:
                time_to_wall_y = float('inf')
            
            time_to_wall = min(time_to_wall_x, time_to_wall_y)
            
            if time_to_wall <= 0:
                break
            
            new_x = current_x + current_vel_x * time_to_wall
            new_y = current_y + current_vel_y * time_to_wall
            
            if new_x < min_center_x or new_x > max_center_x:
                current_x = new_x
                current_vel_x = -current_vel_x
                if new_x < min_center_x:
                    current_x = min_center_x
                else:
                    current_x = max_center_x
            elif new_y < min_center_y or new_y > max_center_y:
                current_y = new_y
                current_vel_y = -current_vel_y
                if new_y < min_center_y:
                    current_y = min_center_y
                else:
                    current_y = max_center_y
            else:
                current_x = new_x
                current_y = new_y
                break
        
        return trajectory
