"""
Модуль первой части метода _apply_movement_strategy AIPlayer.

Содержит начальную валидацию, проверки и обработку зафиксированной позиции (ПРАВИЛО 3).
"""

import time
from typing import Optional

from .game_state import Point


class AIPlayerMovementCorePart1Mixin:
    """Миксин для первой части метода _apply_movement_strategy AIPlayer."""

    def _apply_movement_strategy_part1(
        self, current_x: int, optimal_x: int, paddle_speed: int
    ) -> Optional[int]:
        """
        Первая часть метода _apply_movement_strategy: начальная валидация и ПРАВИЛО 3.
        
        Args:
            current_x: Текущая X-координата платформы.
            optimal_x: Оптимальная X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            
        Returns:
            Смещение платформы (-1, 0, 1) или None, если нужно продолжить обработку.
        """
        start_time_monitor = time.time() if self.performance_monitor else None
        
        # Определяем переменные состояния мяча и зон
        if not self.current_game_state:
            return self._fallback_movement(current_x)
        
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity"))
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start
        
        # КРИТИЧНО: УБРАНО ПРАВИЛО 1 - платформа ДОЛЖНА двигаться к точке падения мяча
        # даже когда мяч летит вверх, чтобы успеть к моменту падения
        # Продолжаем расчет оптимальной позиции независимо от направления мяча
        
        if ball_vel_y == 0:
            # КРИТИЧНО: Если vel_y == 0, это ошибка состояния (должно быть исправлено в PyGameBall.py)
            # Но на всякий случай продолжаем движение к оптимальной позиции, а не используем fallback
            # Это предотвращает ситуацию, когда платформа перестает двигаться из-за временного vel_y=0
            # Логируем для диагностики, но продолжаем нормальную логику
            self._log_paddle_movement(current_x, current_x, "ball_vel_y_zero_warning", 0.5)
            # Продолжаем обработку с обычной логикой - НЕ возвращаем fallback!
        
        # ПРАВИЛО 2: Если мяч в зоне кубиков - платформа НЕ двигается
        # КРИТИЧНО: ИСКЛЮЧЕНИЕ - при 1 кирпиче разрешаем упреждающее движение
        bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 50
        is_last_brick = bricks_count == 1
        
        if ball_y < separation_zone_start and not is_last_brick:
            # Для нормальных случаев - не двигаемся в зоне кубиков
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2: Мяч в зоне кубиков (ball_y={ball_y:.1f} < {separation_zone_start}), платформа не двигается")
            self._log_paddle_movement(current_x, current_x, "ball_in_bricks_zone", 1.0)
            return 0
        elif ball_y < separation_zone_start and is_last_brick:
            # КРИТИЧНО: При 1 кирпиче разрешаем упреждающее движение
            # Это позволяет платформе подготовиться к попаданию в последний кирпич
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2 EXCEPTION: Последний кирпич! Разрешаем движение в зоне кубиков")
            # Продолжаем обработку - не возвращаем 0
        
        # КРИТИЧНО: Проверяем, не потерян ли мяч (ниже верхней границы платформы)
        # Если мяч ниже верхней границы платформы - он считается потерянным, платформа НЕ двигается
        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
        ball_lost = ball_y > paddle_y  # Мяч ниже верхней границы платформы
        
        if ball_lost:
            # Мяч потерян - платформа НЕ двигается
            # КРИТИЧНО: Логируем для диагностики (периодически)
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(f"[PADDLE DEBUG] Мяч потерян (ball_y={ball_y:.1f} > paddle_y={paddle_y:.1f}), платформа не двигается")
            self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle", 1.0)
            return 0
        
        # Проверяем, находится ли мяч в зоне разделения
        # КРИТИЧНО: Мяч должен быть выше верхней границы платформы и в разрешенной зоне
        # Зона разделения: от separation_zone_start до верхней границы платформы
        in_separation_zone = separation_zone_start <= ball_y < paddle_y and ball_vel_y > 0
        
        # КРИТИЧНО: Логируем состояние зоны разделения для диагностики
        # Логируем всегда когда мяч в зоне разделения или близко к платформе
        should_log = in_separation_zone or (ball_y > paddle_y - 100 and ball_vel_y > 0)
        # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
        if should_log:  # Всегда логируем когда мяч близко
            ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
            ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            ball_speed = self.current_game_state.ball_speed if self.current_game_state else 0
            distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
            time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
            # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() если позиция уже зафиксирована
            # Это может вызвать пересчет и дергание
            if self.separation_zone_tracker.target_position_set:
                target_pos = self.separation_zone_tracker.target_position
                if target_pos is not None:
                    optimal_x = int(target_pos)
                else:
                    optimal_x = self.get_optimal_paddle_position()
                    
                    # Записываем метрику производительности
                    if self.performance_monitor and start_time_monitor:
                        duration = time.time() - start_time_monitor
                        self.performance_monitor.record_metric("get_optimal_paddle_position", duration)
            else:
                optimal_x = self.get_optimal_paddle_position()
            distance_to_target = abs(current_x - optimal_x) if optimal_x is not None else 0
            self._logger.debug(f"[BALL TRACKING] ball=({ball_x:.1f},{ball_y:.1f}) vel=({ball_vel_x:.1f},{ball_vel_y:.1f}) speed={ball_speed:.1f} | "
                               f"paddle_x={current_x:.1f} optimal_x={optimal_x:.1f} dist_to_target={distance_to_target:.1f} | "
                               f"zone: sep_start={separation_zone_start} paddle_y={paddle_y:.1f} in_zone={in_separation_zone} | "
                               f"time_to_paddle={time_to_paddle:.2f} frames")
        
        # КРИТИЧНО: Обнаружение отскоков от кирпичей по резкому изменению позиции мяча ИЛИ изменению направления
        ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
        current_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
        current_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
        
        brick_bounce_detected = False
        if self._last_ball_position is not None and self._last_ball_velocity is not None and self.current_game_state:
            # Проверяем резкое изменение позиции мяча (более 50 пикселей за кадр)
            position_change = abs(ball_x - self._last_ball_position.x)
            # Также проверяем изменение Y координаты вверх (мяч отскочил)
            y_change = ball_y - self._last_ball_position.y
            
            # КРИТИЧНО: Проверяем изменение направления ball_vel_y (мяч отскочил вверх после движения вниз)
            # Это самый надежный способ обнаружения отскока от кирпича
            last_vel_y = self._last_ball_velocity.y
            vel_y_direction_change = (last_vel_y > 0 and current_vel_y < 0)  # Мяч двигался вниз, теперь вверх
            
            # Отскок от кирпича: 
            # 1. Резкое изменение позиции X (>50px) И vel_x не изменилась сильно
            # 2. ИЛИ изменение направления Y координаты вверх (y_change < -10)
            # 3. ИЛИ изменение направления ball_vel_y (мяч отскочил вверх)
            if position_change > 50 or (y_change < -10 and ball_y < separation_zone_start) or vel_y_direction_change:
                # Проверяем, что это не отскок от стены (vel_x должен был измениться, но это уже отслеживается)
                vel_x_change = abs(current_vel_x - self._last_ball_velocity.x)
                
                # Если скорость vel_x не изменилась сильно, но позиция изменилась резко - это отскок от кирпича
                # ИЛИ если изменилось направление ball_vel_y (мяч отскочил вверх)
                if (vel_x_change < 5 and position_change > 50) or vel_y_direction_change:
                    brick_bounce_detected = True
                    bounce_reason = "vel_y direction change" if vel_y_direction_change else f"position change {position_change:.1f}px"
                    self._logger.debug(f"[BRICK BOUNCE DETECTED] {bounce_reason}, "
                                     f"ball=({ball_x:.1f},{ball_y:.1f}) prev=({self._last_ball_position.x:.1f},{self._last_ball_position.y:.1f}), "
                                     f"vel_y: {last_vel_y:.1f} -> {current_vel_y:.1f}")
        
        # Обновляем предыдущую позицию мяча
        if self.current_game_state:
            self._last_ball_position = Point(ball_x, ball_y)
            self._last_ball_velocity = Point(current_vel_x, current_vel_y)
        
        # ПРАВИЛО 3: Если целевая позиция установлена - используем её БЕЗ пересчета
        # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз при входе мяча в зону разделения
        # и не меняется до следующего отскока от стены ИЛИ отскока от кирпича
        if self.separation_zone_tracker.target_position_set:
            # КРИТИЧНО: Проверяем отскоки от стены И от кирпичей
            current_target = self.separation_zone_tracker.target_position
            if current_target is not None and in_separation_zone:
                # КРИТИЧНО: Проверяем изменение vel_x - это признак отскока от стены
                # ИЛИ обнаружение отскока от кирпича
                saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                
                # Если vel_x изменился (мяч отскочил от стены) ИЛИ обнаружен отскок от кирпича - сбрасываем цель
                if (saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > 0.1) or brick_bounce_detected:
                    # Мяч отскочил от стены или от кирпича - траектория изменилась, нужно пересчитать цель
                    if brick_bounce_detected:
                        self._logger.debug(f"[TARGET RESET] Мяч отскочил от кирпича! Траектория изменилась, пересчитываем цель")
                    else:
                        self._logger.debug(f"[TARGET RESET] Мяч отскочил от стены! Старая vel_x={saved_vel_x:.1f}, Новая vel_x={current_vel_x:.1f}")
                    
                    # ИСПРАВЛЕНИЕ: Проверяем расстояние до новой потенциальной цели перед сбросом
                    # Рассчитываем новую потенциальную цель для проверки расстояния
                    ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                    ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                    ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else 0
                    
                    # Рассчитываем время до приземления мяча
                    distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                    time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                    
                    # Предсказываем новую позицию приземления
                    if time_to_paddle != float('inf') and time_to_paddle > 0:
                        predicted_new_x = ball_x + current_vel_x * time_to_paddle
                        # Применяем зоны
                        zone_size = self.config.paddle.zone_size
                        screen_center = self.screen_width / 2
                        left_threshold = screen_center - zone_size * 2
                        right_threshold = screen_center + zone_size * 2
                        
                        if predicted_new_x < left_threshold:
                            zone_center_x = predicted_new_x + zone_size
                        elif predicted_new_x > right_threshold:
                            zone_center_x = predicted_new_x - zone_size
                        else:
                            zone_center_x = predicted_new_x
                        
                        distance_to_new_target = abs(current_x - zone_center_x)
                        
                        # ИСПРАВЛЕНИЕ: Если новая цель слишком далеко (>200px), используем консервативный подход
                        # Вместо резкого изменения цели, двигаемся постепенно или выбираем промежуточную позицию
                        if distance_to_new_target > 200:
                            # Рассчитываем максимальное расстояние, которое можем пройти за время до приземления
                            max_distance = paddle_speed * time_to_paddle if time_to_paddle < 100 else 200
                            
                            # Выбираем промежуточную позицию в направлении новой цели
                            if zone_center_x > current_x:
                                conservative_target = min(zone_center_x, current_x + max_distance)
                            else:
                                conservative_target = max(zone_center_x, current_x - max_distance)
                            
                            # КРИТИЧНО: Ограничиваем границами экрана, чтобы избежать отрицательных координат
                            min_x = self.paddle_width // 2
                            max_x = self.screen_width - self.paddle_width // 2
                            conservative_target = max(min_x, min(max_x, conservative_target))
                            
                            self._logger.debug(f"[CONSERVATIVE TARGET] Большое расстояние ({distance_to_new_target:.1f}px), "
                                               f"используем промежуточную цель: {conservative_target:.1f} вместо {zone_center_x:.1f}")
                            
                            # Устанавливаем консервативную цель вместо полного сброса
                            self.separation_zone_tracker.target_position = int(conservative_target)
                            self.separation_zone_tracker.target_position_set = True
                            self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                            # Продолжаем с этой целью без полного сброса
                        else:
                            # Расстояние приемлемое - выполняем обычный сброс
                            self.separation_zone_tracker.target_position_set = False
                            self.separation_zone_tracker.target_position = None
                    else:
                        # Не можем рассчитать время - выполняем обычный сброс
                        self.separation_zone_tracker.target_position_set = False
                        self.separation_zone_tracker.target_position = None
                    
                    self.separation_zone_tracker.paddle_moved_after_set = False
                    self.separation_zone_tracker.paddle_reached_target = False
                    self.separation_zone_tracker.frames_since_target_set = 0
                    self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                    self._log_paddle_movement(current_x, current_x, "target_reset_wall_bounce", 1.0)
                    # Продолжаем обработку с обычной логикой для установки новой цели
                else:
                    # Скорость не изменилась - траектория стабильна, НЕ обновляем цель
                    # КРИТИЧНО: Возвращаем зафиксированную позицию БЕЗ пересчета
                    # Это гарантирует, что позиция не изменится до отскока от стены
                    self.separation_zone_tracker.saved_ball_vel_x = current_vel_x
                    
                    # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() для проверки - это может вызвать пересчет
                    # Просто используем зафиксированную позицию
                    
                    # ВСЕГДА возвращаем зафиксированную позицию
                    # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() - это может вызвать пересчет и дергание
                    target_pos = int(current_target)
                    distance_to_target = abs(current_x - target_pos)
                    
                    # КРИТИЧНО: Используем большой tolerance для остановки, чтобы предотвратить дергание
                    # Проблема: платформа движется со скоростью 15px/кадр и "перескакивает" через цель
                    # Решение: используем большой tolerance (равный скорости движения), чтобы платформа останавливалась
                    # даже если немного перескочила через цель
                    tolerance = 15  # Равен скорости движения платформы - предотвращает дергание
                    
                    # КРИТИЧНО: Логируем движение к зафиксированной позиции для отслеживания
                    # Фильтрация по уровню выполняется автоматически системой логирования Python
                    self._logger.debug(f"[MOVING TO FIXED] ФЛАГ: Движение к зафиксированной позиции! "
                                       f"current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
                                       f"distance={distance_to_target:.1f}px, tolerance={tolerance}")
                    
                    # Двигаемся к зафиксированной позиции
                    if distance_to_target > tolerance:
                        # Платформа далеко от цели - начинаем движение
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        if movement != 0:
                            self._update_loop_tracking(movement, int(current_x), int(target_pos))
                            self._update_smoothness_tracking(movement, current_x)
                            self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                            return movement
                    else:
                        # Достигли цели - останавливаемся
                        # КРИТИЧНО: НЕ устанавливаем флаг paddle_reached_target - он не нужен
                        # Просто останавливаемся, если близко к цели
                        return 0
            
            # КРИТИЧНО: Если позиция зафиксирована, но мяч не в зоне разделения - проверяем сброс
            # КРИТИЧНО: Используем гистерезис для предотвращения дергания
            # Сбрасываем целевую позицию ТОЛЬКО если:
            # 1. Мяч ушел далеко вверх (выше зоны кубиков) ИЛИ
            # 2. Мяч потерян (ниже верхней границы платформы)
            should_reset = False
            
            # Проверка 1: Мяч ушел далеко вверх (выше зоны кубиков)
            if ball_y < separation_zone_start - 50:  # Далеко выше зоны разделения
                should_reset = True
            
            # Проверка 2: Мяч потерян (ниже верхней границы платформы)
            if ball_lost:
                should_reset = True
            
            # Если нужно сбросить - сбрасываем
            if should_reset:
                self.separation_zone_tracker.target_position_set = False
                self.separation_zone_tracker.target_position = None
                self.separation_zone_tracker.paddle_moved_after_set = False
                self.separation_zone_tracker.paddle_reached_target = False
                self._log_paddle_movement(current_x, current_x, "target_reset_ball_left_zone", 1.0)
                # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
            else:
                # КРИТИЧНО: Позиция зафиксирована, но мяч не в зоне разделения
                # Используем зафиксированную позицию БЕЗ пересчета
                current_target = self.separation_zone_tracker.target_position
                if current_target is not None:
                    target_pos = int(current_target)
                    distance_to_target = abs(current_x - target_pos)
                    tolerance = 3
                    
                    if distance_to_target > tolerance:
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        if movement != 0:
                            self._update_loop_tracking(movement, int(current_x), int(target_pos))
                            self._update_smoothness_tracking(movement, current_x)
                            self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target_outside_zone", 1.0)
                            return movement
                    else:
                        return 0
        
        # Продолжаем обработку в следующей части метода
        return None

