"""
Модуль третьей части метода _apply_movement_strategy AIPlayer.

Содержит ПРАВИЛО 5: обычное движение к оптимальной позиции.
"""

import time
from typing import Optional


class AIPlayerMovementCorePart3Mixin:
    """Миксин для третьей части метода _apply_movement_strategy AIPlayer."""

    def _apply_movement_strategy_part3(
        self,
        current_x: int,
        optimal_x: int,
        paddle_speed: int,
        ball_lost: bool,
        start_time_monitor: Optional[float],
    ) -> int:
        """
        Третья часть метода _apply_movement_strategy: ПРАВИЛО 5 (обычное движение).
        
        Args:
            current_x: Текущая X-координата платформы.
            optimal_x: Оптимальная X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            ball_lost: Флаг потери мяча.
            start_time_monitor: Время начала мониторинга производительности.
            
        Returns:
            Смещение платформы (-1, 0, 1).
        """
        # ПРАВИЛО 5: Если мяч НЕ в зоне разделения и целевая позиция НЕ установлена
        # - используем обычную логику (мяч еще в зоне кубиков или выше)
        # КРИТИЧНО: Но только если мяч НЕ потерян и движется вниз
        # Если мяч потерян или движется вверх - не двигаемся
        if ball_lost:
            self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle_rule5", 1.0)
            return 0
        
        # КРИТИЧНО: УБРАНО правило "не двигаться когда мяч летит вверх"
        # Платформа ДОЛЖНА двигаться к точке падения мяча даже когда мяч летит вверх,
        # чтобы успеть к моменту падения. Продолжаем расчет оптимальной позиции.
        
        # КРИТИЧНО: Если мяч в разрешенной зоне (ниже кубиков, но выше платформы) и движется вниз
        # - платформа ДОЛЖНА двигаться к точке падения мяча
        optimal_x = self.get_optimal_paddle_position()
        # get_optimal_paddle_position() всегда возвращает int, не None
        
        # Проверяем зацикливание и при необходимости меняем стратегию
        # НО ТОЛЬКО если целевая позиция НЕ установлена
        if not self.separation_zone_tracker.target_position_set:
            self._change_strategy_if_looping()
            if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                optimal_x = self._apply_alternative_strategy(optimal_x)
                # Проверяем, что альтернативная стратегия тоже валидна
                if optimal_x is None:
                    return self._fallback_movement(current_x)
        
        # Допуск по точности позиционирования
        precision_tolerance = 2
        # Проверяем дрожание и применяем штрафы
        jitter_detected = self._detect_jitter()
        if jitter_detected:
            # Увеличиваем допуск для уменьшения дрожания
            precision_tolerance = max(5, precision_tolerance + 2)
            # Увеличиваем штраф за дрожание
            self.smoothness_system["smoothness_penalty"] = min(
                1.0, self.smoothness_system["smoothness_penalty"] + 0.1
            )
        else:
            # Уменьшаем штраф при плавном движении
            self.smoothness_system["smoothness_penalty"] = max(
                0.0, self.smoothness_system["smoothness_penalty"] - 0.05
            )
        
        # Допуск по точности позиционирования (учитываем штраф за дрожание)
        base_precision_tolerance = 2
        precision_tolerance = base_precision_tolerance + int(
            self.smoothness_system["smoothness_penalty"] * 3
        )
        
        # Увеличиваем допуск, когда мяч движется вниз и траектория известна
        if self.current_game_state:
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            ball_y = self.current_game_state.ball_position.y
            paddle_zone_start = self.screen_height - 60
            separation_zone_start = self.separation_zone_tracker.separation_zone_start
            in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
            
            # КРИТИЧНО: НЕ увеличиваем допуск слишком сильно, иначе платформа не будет двигаться
            # Если мяч движется вниз и уже ниже кубиков - используем умеренный допуск
            if ball_vel_y > 0 and ball_y > 250:  # Мяч движется вниз и ниже кубиков
                # Используем умеренный допуск (5-10 пикселей), чтобы платформа могла двигаться
                # Только если платформа УЖЕ очень близко к цели (менее 5 пикселей) - не двигаемся
                if abs(optimal_x - current_x) < 5:
                    precision_tolerance = max(precision_tolerance, 5)  # Очень близко - не двигаемся
                else:
                    # Платформа еще не достигла цели - используем минимальный допуск для движения
                    precision_tolerance = max(precision_tolerance, 2)  # Минимальный допуск
        
        distance_to_optimal = abs(optimal_x - current_x)
        
        # Поощряем минимальные движения - если расстояние очень мало, не двигаемся
        min_movement_distance = self.smoothness_system["min_movement_distance"]
        
        # КРИТИЧНО: Убрана проверка ball_approaching_quickly - она вызывала дергание
        # В зоне разделения с установленной целевой позицией платформа просто движется к цели и останавливается
        
        if distance_to_optimal < min_movement_distance:
            # Если расстояние меньше минимального, проверяем, стоит ли двигаться
            if distance_to_optimal <= precision_tolerance:
                movement = 0
                # Поощряем точное позиционирование
                self.smoothness_system["consecutive_stops"] += 1
                if self.smoothness_system["consecutive_stops"] > 3:
                    # Уменьшаем штраф за хорошее позиционирование
                    self.smoothness_system["smoothness_penalty"] = max(
                        0.0, self.smoothness_system["smoothness_penalty"] - 0.1
                    )
                # Сохраняем базовую скорость, так как не двигаемся
                self._last_adjusted_paddle_speed = paddle_speed
            else:
                # Двигаемся только если действительно нужно
                movement = self._calculate_smooth_movement(
                    current_x, optimal_x, distance_to_optimal
                )
                # Сохраняем базовую скорость для этого случая
                self._last_adjusted_paddle_speed = paddle_speed
        elif distance_to_optimal <= precision_tolerance:
            movement = 0
            self.smoothness_system["consecutive_stops"] += 1
            # Сохраняем базовую скорость, так как не двигаемся
            self._last_adjusted_paddle_speed = paddle_speed
        else:
            self.smoothness_system["consecutive_stops"] = 0
            # Адаптивная скорость от системы обучения
            if self.current_game_state:
                ball_speed = self.current_game_state.ball_speed
                distance_to_target = distance_to_optimal
                
                # Рассчитываем время до встречи с мячом для более агрессивного увеличения скорости
                time_to_meeting = float("inf")
                ball_vel_y = (
                    self.current_game_state.ball_velocity.y
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                if ball_vel_y > 0:  # Мяч движется вниз
                    ball_y = self.current_game_state.ball_position.y
                    paddle_y = self.current_game_state.paddle_position.y
                    distance_y = paddle_y - ball_y
                    if distance_y > 0:
                        time_to_meeting = distance_y / ball_vel_y
                
                speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                    ball_speed, distance_to_target
                )
                
                # Если мяч быстро приближается, агрессивно увеличиваем скорость
                if time_to_meeting != float("inf") and time_to_meeting > 0:
                    # Чем меньше времени до встречи, тем выше должна быть скорость
                    if time_to_meeting < 30:  # Менее 30 кадров (0.5 сек при 60 FPS)
                        urgency_factor = 30.0 / max(time_to_meeting, 1)
                        speed_multiplier *= min(
                            urgency_factor, 3.0
                        )  # До 3x дополнительного ускорения
                    elif time_to_meeting < 60:  # Менее 60 кадров (1 сек)
                        urgency_factor = 60.0 / max(time_to_meeting, 1)
                        speed_multiplier *= min(
                            urgency_factor, 2.0
                        )  # До 2x дополнительного ускорения
                
                # ИСПРАВЛЕНИЕ: Адаптивная базовая скорость в зависимости от расстояния
                # При больших расстояниях (>150px) увеличиваем базовую скорость дополнительно
                base_speed_multiplier = 10.0  # Базовая скорость в 10 раз
                
                # ИСПРАВЛЕНИЕ: При расстоянии >150px увеличиваем скорость еще больше
                if distance_to_target > 150:
                    # Для больших расстояний используем более агрессивную скорость
                    base_speed_multiplier = 15.0  # Увеличиваем до 15x для больших расстояний
                elif distance_to_target > 100:
                    base_speed_multiplier = 12.0  # 12x для средних расстояний
                
                # ИСПРАВЛЕНИЕ: При экстренных ситуациях (мало времени до встречи) еще больше увеличиваем
                if time_to_meeting != float('inf') and time_to_meeting < 20:  # Менее 20 кадров
                    base_speed_multiplier *= 1.5  # Дополнительно увеличиваем на 50%
                
                # Ограничиваем минимальный множитель скорости, чтобы платформа не двигалась слишком медленно
                # AI может увеличивать скорость до 10x для достижения цели (в дополнение к базовому 10-15x)
                max_multiplier = 10.0  # Дополнительный множитель до 10x
                speed_multiplier = max(0.8, min(max_multiplier, speed_multiplier))
                adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)  # ИСПРАВЛЕНО: убрано двойное умножение
                # Гарантируем минимальную скорость платформы
                adjusted_paddle_speed = max(
                    int(paddle_speed * 0.8), adjusted_paddle_speed
                )
                self._last_paddle_speed_multiplier = speed_multiplier
                # Сохраняем для использования в PyGameBall.py
                self._last_adjusted_paddle_speed = adjusted_paddle_speed
            else:
                adjusted_paddle_speed = paddle_speed
            
            # Сохраняем для использования в PyGameBall.py
            self._last_adjusted_paddle_speed = adjusted_paddle_speed
            
            movement = self.position_optimizer.calculate_paddle_movement(
                current_x, optimal_x, adjusted_paddle_speed
            )
            
            # Если расчёт не даёт движения, но мы не на месте — fallback
            if movement == 0 and optimal_x != current_x:
                movement = self._fallback_movement(current_x)
        
        # Обновляем данные по зацикливанию
        self._update_loop_tracking(movement, current_x, optimal_x)
        
        # Обновляем данные по плавности движения
        self._update_smoothness_tracking(movement, current_x)
        
        # Логирование движения
        if movement != 0:
            reason = (
                "ball_tracking"
                if not self.is_ball_moving_towards_paddle()
                else "trajectory_optimization"
            )
            confidence = self._calculate_decision_confidence(optimal_x)
            self.performance_logger.log_paddle_movement(
                from_x=current_x,
                to_x=current_x + movement * paddle_speed,
                reason=reason,
                confidence=confidence,
            )
        
        # Статистика по ходам
        self.current_game_stats["total_moves"] += 1
        if abs(optimal_x - current_x) < 10:
            self.current_game_stats["optimal_moves"] += 1
        
        # Учитываем плавность движения в обучении
        if movement != 0:
            # Штрафуем за дрожание при обучении
            if self.smoothness_system["smoothness_penalty"] > 0.5:
                # Высокий штраф за дрожание - это плохое поведение
                jitter_penalty = {
                    "action_type": "movement_jitter",
                    "success": False,
                    "penalty": self.smoothness_system["smoothness_penalty"],
                    "movement_distance": abs(optimal_x - current_x),
                }
                # Можно добавить в систему обучения для улучшения поведения
                # self.learning_system.update_strategy(jitter_penalty)
        
        # Записываем метрику производительности
        if self.performance_monitor and start_time_monitor:
            duration = time.time() - start_time_monitor
            self.performance_monitor.record_metric("move_paddle_towards", duration)
        return movement

