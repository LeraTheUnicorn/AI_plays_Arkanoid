"""
Модуль обработки зон AIPlayer.

Содержит методы расчета зон и обработки различных зон игры.
"""

import math
from typing import Dict, Optional

from .exceptions import PredictionError


class AIPlayerZonesMixin:
    """Миксин для методов обработки зон AIPlayer."""

    def _calculate_zones(self) -> Dict[str, float]:
        """
        Рассчитывает границы зон игры.
        
        Returns:
            Словарь с границами зон: bricks_zone_end, separation_zone_start, paddle_zone_start
        """
        bricks_zone_end = self.config.zones.bricks_zone_end
        separation_zone_start = self.config.zones.separation_zone_start
        paddle_zone_start = self.config.zones.paddle_zone_start(self.screen_height)
        
        # Обновляем отслеживание зоны разделения
        self.separation_zone_tracker.separation_zone_start = separation_zone_start
        self.separation_zone_tracker.paddle_zone_start = paddle_zone_start
        
        return {
            "bricks_zone_end": bricks_zone_end,
            "separation_zone_start": separation_zone_start,
            "paddle_zone_start": paddle_zone_start,
        }

    def _handle_bricks_zone(self, ball_y: float) -> int:
        """
        Обрабатывает ситуацию, когда мяч находится в зоне кубиков.
        
        Args:
            ball_y: Y-координата мяча
            
        Returns:
            Текущая позиция платформы (не двигаемся)
        """
        if not self.current_game_state:
            return self.screen_width // 2
        # КРИТИЧНО: НЕ сбрасываем отслеживание зоны разделения и целевую позицию,
        # так как мяч может временно попасть в зону кубиков (при отскоке),
        # но потом вернуться в зону разделения
        # Сбрасываем только если мяч действительно ушел далеко вверх
        # и НЕ установлена целевая позиция (чтобы не сбрасывать уже установленную позицию)
        if ball_y < self.config.zones.ball_reset_height and not self.separation_zone_tracker.target_position_set:
            # Мяч очень высоко и целевая позиция не установлена - сбрасываем отслеживание
            self.separation_zone_tracker.ball_entered_separation_zone = False
            self.separation_zone_tracker.target_position_set = False
            self.separation_zone_tracker.target_position = None
        # ВСЕГДА возвращаем текущую позицию, не двигаемся
        return int(self.current_game_state.paddle_position.x)

    def _handle_separation_zone(
        self, ball_y: float, ball_vel_y: float, zones: Dict[str, float]
    ) -> Optional[int]:
        """
        Обрабатывает ситуацию, когда мяч находится в зоне разделения.
        
        Args:
            ball_y: Y-координата мяча
            ball_vel_y: Y-скорость мяча
            zones: Словарь с границами зон
            
        Returns:
            Оптимальная позиция платформы или None, если нужно продолжить расчет
        """
        if not self.current_game_state:
            return None
        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]
        
        # Если мяч в разделительной зоне, но движется вверх — не дёргаем платформу
        if separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0:
            return int(self.current_game_state.paddle_position.x)
        
        # Проверяем, вошел ли мяч в зону разделения
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        # Если позиция уже зафиксирована в зоне разделения - возвращаем её БЕЗ пересчета
        if in_separation_zone and self.separation_zone_tracker.target_position_set:
            fixed_position = self.separation_zone_tracker.target_position
            if fixed_position is not None:
                # Логируем возврат зафиксированной позиции для отслеживания
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(f"[POSITION RETURN] ФЛАГ: Возвращаем зафиксированную позицию БЕЗ пересчета! "
                                  f"target_position={fixed_position:.1f}, ball_y={ball_y:.1f}")
                
                # Проверяем, не изменилась ли позиция (нарушение правила)
                saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                
                # Если vel_x не изменился (нет отскока от стены), но позиция изменилась - нарушение
                if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) <= self.config.ball.velocity_tolerance:
                    # Нет отскока от стены - позиция НЕ должна меняться
                    return int(fixed_position)
                else:
                    # vel_x изменился - это отскок от стены, позиция может измениться
                    # Но мы все равно возвращаем зафиксированную позицию до следующего пересчета
                    return int(fixed_position)
        
        # Если мяч только что вошел в зону разделения, отмечаем это
        if in_separation_zone and not self.separation_zone_tracker.ball_entered_separation_zone:
            self.separation_zone_tracker.ball_entered_separation_zone = True
        
        return None  # Продолжаем расчет позиции

    def _handle_upward_movement(self, ball_y: float) -> int:
        """
        Обрабатывает ситуацию, когда мяч движется вверх.
        
        Args:
            ball_y: Y-координата мяча
            
        Returns:
            Оптимальная позиция платформы
        """
        # Мяч движется вверх — обрабатываем возможный отскок от потолка
        if ball_y < self.config.zones.ball_reset_height:
            return self._handle_ceiling_bounce_positioning()
        # Иначе просто сопровождаем мяч
        return int(self._track_ball_position())
