"""
Модуль второй части методов выбора целей для AIPlayer.

Содержит методы для выбора лучшей цели при малом количестве кирпичей и расчета оптимального смещения.
"""

import math
from typing import List, Optional, Any


class AIPlayerTargetSelectionPart2Mixin:
    """
    Миксин для второй части методов выбора целей.
    Добавляет методы выбора лучшей цели и расчета оптимального смещения.
    """

    def _find_best_target_for_few_bricks(
        self,
        bricks: List[Any],
        paddle_y: float,
        ball_x: float,
    ) -> Optional[Any]:
        """Специальная логика выбора цели для малого количества оставшихся кубиков."""
        if not bricks:
            return None

        if len(bricks) == 1:
            brick = bricks[0]
            self._logger.debug(f"[LAST BRICK] Таргетирование последнего кирпича: x={getattr(brick, 'x', 0)}, y={getattr(brick, 'y', 0)}")
            return brick

        if len(bricks) <= 3:
            bottom_brick = min(bricks, key=lambda b: getattr(b, "y", 0))
            ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
            vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            
            for brick in bricks:
                brick_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
                brick_y = getattr(brick, "y", 0)
                
                if abs(brick_x - ball_x) < 150 and brick_y <= getattr(bottom_brick, "y", 0) + 30:
                    if (vel_x > 0 and brick_x > ball_x) or (vel_x < 0 and brick_x < ball_x):
                        return brick
            
            return bottom_brick

        best_brick = None
        best_score = -float("inf")

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 2000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3

            horizontal_distance = abs(brick_center_x - ball_x)
            score -= horizontal_distance * 0.2

            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system.hit_patterns:
                pattern = self.targeting_system.hit_patterns[brick_key]
                score += pattern.get("success_rate", 0.0) * 300.0

            if score > best_score:
                best_score = score
                best_brick = brick

        return best_brick

    def _calculate_optimal_offset(self, landing_x: float, target_brick: Any) -> float:
        """Рассчитывает оптимальное смещение на платформе для попадания в кубик."""
        if not target_brick or not self.current_game_state:
            return 0.0
        
        bricks_count = len(self.current_game_state.remaining_bricks)
        
        if bricks_count == 1:
            brick_center_x = getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
            horizontal_offset_needed = brick_center_x - landing_x
            paddle_half_width = self.paddle_width / 2
            max_offset = 1.5
            
            if abs(horizontal_offset_needed) > paddle_half_width * max_offset:
                offset = max_offset if horizontal_offset_needed > 0 else -max_offset
            else:
                offset = horizontal_offset_needed / (paddle_half_width * max_offset) * max_offset
            
            vel_x = self.current_game_state.ball_velocity.x if hasattr(self.current_game_state, "ball_velocity") else 0
            if abs(vel_x) > 0.1:
                prediction_adjustment = (vel_x / abs(vel_x)) * 0.2
                offset += prediction_adjustment
            
            offset = max(-max_offset, min(max_offset, offset))
            self._logger.debug(f"[LAST BRICK OFFSET] brick_x={brick_center_x:.1f}, landing_x={landing_x:.1f}, offset={offset:.2f}")
            return offset
        
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_width = getattr(target_brick, "width", 60)
        brick_height = getattr(target_brick, "height", 20)
        
        brick_center_x = brick_x + brick_width / 2
        brick_center_y = brick_y + brick_height / 2

        paddle_y = self.current_game_state.paddle_position.y
        ball_x = self.current_game_state.ball_position.x
        ball_vel_x = self.current_game_state.ball_velocity.x
        
        if abs(ball_vel_x) > 0:
            if ball_vel_x > 0 and ball_x < brick_center_x:
                target_x = brick_center_x + min(brick_width * 0.15, 10)
            elif ball_vel_x < 0 and ball_x > brick_center_x:
                target_x = brick_center_x - min(brick_width * 0.15, 10)
            else:
                target_x = brick_center_x
        else:
            target_x = brick_center_x

        target_x = max(brick_x, min(brick_x + brick_width, target_x))

        delta_x = target_x - landing_x
        delta_y = paddle_y - brick_center_y

        if delta_y <= 0:
            return 0.0

        target_angle = math.atan2(delta_x, delta_y)
        max_angle = math.pi / 4
        offset = target_angle / max_angle
        offset = max(-1.0, min(1.0, offset))

        if abs(offset) < 0.1:
            offset = 0.25 if delta_x > 0 else -0.25
        elif abs(delta_x) < 10:
            offset = max(0.2, offset) if delta_x > 0 else min(-0.2, offset)

        offset = self._adjust_offset_from_history(offset, target_brick)
        return offset

    def _adjust_offset_from_history(self, offset: float, target_brick: Any) -> float:
        """Корректирует смещение на основе истории успешных ударов по данному кубику."""
        brick_x = float(getattr(target_brick, "x", 0))
        brick_y = float(getattr(target_brick, "y", 0))
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        pattern = self.targeting_system.hit_patterns.get(brick_key)
        if not pattern:
            return offset

        successful_offsets = pattern.get("successful_offsets", [])
        if not successful_offsets:
            return offset

        # Type narrowing: ensure successful_offsets is a list of numbers
        if not isinstance(successful_offsets, list):
            return offset
        
        # Convert to list of floats for type safety
        offset_values = [float(x) for x in successful_offsets if isinstance(x, (int, float))]
        if not offset_values:
            return offset

        avg_successful_offset = sum(offset_values) / len(offset_values)
        return float(offset * 0.7 + avg_successful_offset * 0.3)
