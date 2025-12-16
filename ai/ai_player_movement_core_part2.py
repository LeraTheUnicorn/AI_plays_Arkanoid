"""
Модуль второй части метода _apply_movement_strategy AIPlayer.

Содержит продолжение обработки зафиксированной позиции (ПРАВИЛО 3) и установку новой позиции (ПРАВИЛО 4).
"""

import time
from typing import Optional


class AIPlayerMovementCorePart2Mixin:
    """Миксин для второй части метода _apply_movement_strategy AIPlayer."""

    def _apply_movement_strategy_part2(
        self,
        current_x: int,
        optimal_x: int,
        paddle_speed: int,
        ball_y: float,
        ball_vel_y: float,
        separation_zone_start: float,
        paddle_zone_start: float,
        paddle_y: float,
        ball_lost: bool,
        in_separation_zone: bool,
        start_time_monitor: Optional[float],
    ) -> Optional[int]:
        """
        Вторая часть метода _apply_movement_strategy: продолжение ПРАВИЛА 3 и ПРАВИЛО 4.

        Args:
            current_x: Текущая X-координата платформы.
            optimal_x: Оптимальная X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.
            ball_y: Y-координата мяча.
            ball_vel_y: Y-скорость мяча.
            separation_zone_start: Начало зоны разделения.
            paddle_zone_start: Начало зоны платформы.
            paddle_y: Y-координата платформы.
            ball_lost: Флаг потери мяча.
            in_separation_zone: Флаг нахождения мяча в зоне разделения.
            start_time_monitor: Время начала мониторинга производительности.

        Returns:
            Смещение платформы (-1, 0, 1) или None, если нужно продолжить обработку.
        """
        # Продолжение ПРАВИЛА 3: обработка зафиксированной позиции
        # (код из строк 1200-1538 в оригинальном методе)
        # Код полностью перенесен в ai_player_movement_core_part1.py

        # ПРАВИЛО 4: Если целевая позиция НЕ установлена и мяч в зоне разделения
        # - устанавливаем целевую позицию ОДИН РАЗ через get_optimal_paddle_position
        # - после установки используем её без пересчета
        # КРИТИЧНО: Проверяем, что мяч НЕ потерян перед установкой целевой позиции
        if (
            in_separation_zone
            and not self.separation_zone_tracker.target_position_set
            and not ball_lost
        ):
            # КРИТИЧНО: Логируем установку целевой позиции
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(
                f"[PADDLE DEBUG] ПРАВИЛО 4: Устанавливаем целевую позицию. ball_y={ball_y:.1f}, in_separation_zone={in_separation_zone}"
            )
            # Устанавливаем целевую позицию один раз
            optimal_x = self.get_optimal_paddle_position()
            # get_optimal_paddle_position() всегда возвращает int, не None

            # КРИТИЧНО: Проверяем, успеет ли платформа добраться до цели ПЕРЕД установкой
            # Рассчитываем время до приземления мяча и возможность достижения цели
            distance_to_target = abs(current_x - optimal_x)
            distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
            time_to_paddle = (
                distance_to_paddle_y / ball_vel_y
                if ball_vel_y > 0 and distance_to_paddle_y > 0
                else float("inf")
            )

            # КРИТИЧНО: Всегда проверяем возможность достижения цели
            # Рассчитываем время, необходимое для достижения цели платформой
            if (
                time_to_paddle != float("inf")
                and time_to_paddle > 0
                and distance_to_target > 0
            ):
                # Используем текущую скорость платформы (уже увеличенную)
                frames_to_reach = (
                    distance_to_target / paddle_speed
                    if paddle_speed > 0
                    else float("inf")
                )

                # КРИТИЧНО: Увеличиваем запас безопасности до 20% и используем только 85% времени
                # Это гарантирует, что платформа успеет доехать с запасом
                safety_margin = 1.2  # 20% запас
                time_usage = 0.85  # Используем только 85% времени для безопасности

                if frames_to_reach > time_to_paddle * safety_margin:
                    # Платформа не успеет - используем максимальное расстояние, которое можно пройти
                    max_distance = paddle_speed * time_to_paddle * time_usage

                    # КРИТИЧНО: Рассчитываем предсказанную позицию мяча для более точной промежуточной цели
                    ball_x = (
                        self.current_game_state.ball_position.x
                        if self.current_game_state
                        else 0
                    )
                    ball_vel_x = (
                        self.current_game_state.ball_velocity.x
                        if (
                            self.current_game_state
                            and hasattr(self.current_game_state, "ball_velocity")
                        )
                        else 0
                    )
                    predicted_ball_x = ball_x + ball_vel_x * time_to_paddle

                    # Применяем логику зон к предсказанной позиции
                    zone_size = self.config.paddle.zone_size
                    screen_center = self.screen_width / 2
                    left_threshold = screen_center - zone_size * 2
                    right_threshold = screen_center + zone_size * 2

                    if predicted_ball_x < left_threshold:
                        zone_center_x = predicted_ball_x + zone_size
                    elif predicted_ball_x > right_threshold:
                        zone_center_x = predicted_ball_x - zone_size
                    else:
                        zone_center_x = predicted_ball_x

                    # Выбираем промежуточную позицию в направлении зоны мяча, но не дальше чем можем пройти
                    if zone_center_x > current_x:
                        achievable_target = min(zone_center_x, current_x + max_distance)
                    else:
                        achievable_target = max(zone_center_x, current_x - max_distance)

                    self._logger.warning(
                        f"[ACHIEVABLE TARGET] Цель недостижима: расстояние={distance_to_target:.1f}px, "
                        f"время_до_мяча={time_to_paddle:.1f}, время_до_цели={frames_to_reach:.1f}. "
                        f"Используем промежуточную цель: {achievable_target:.1f} вместо {optimal_x:.1f} "
                        f"(predicted_ball_x={predicted_ball_x:.1f}, zone_center={zone_center_x:.1f})"
                    )
                    optimal_x = int(achievable_target)

            # Дополнительная проверка для экстренных ситуаций (мяч очень близко)
            if (
                time_to_paddle != float("inf")
                and time_to_paddle < 10
                and distance_to_target > 100
            ):
                # Мяч очень близко, а платформа далеко - пересчитываем цель с учетом зон
                # Вместо простого ограничения движения, пересчитываем оптимальную позицию
                # с учетом того, что платформа не успеет далеко переместиться
                original_optimal = optimal_x

                # Рассчитываем максимальное расстояние, которое платформа может пройти
                # Используем переданный paddle_speed или базовую скорость
                max_distance = paddle_speed * time_to_paddle

                # Определяем, в какую зону попадает predicted_x
                ball_x = (
                    self.current_game_state.ball_position.x
                    if self.current_game_state
                    else 0
                )
                ball_vel_x = (
                    self.current_game_state.ball_velocity.x
                    if (
                        self.current_game_state
                        and hasattr(self.current_game_state, "ball_velocity")
                    )
                    else 0
                )
                predicted_x = ball_x + ball_vel_x * time_to_paddle

                # Применяем логику зон к predicted_x
                zone_size = self.config.paddle.zone_size
                screen_center = self.screen_width / 2
                left_threshold = screen_center - zone_size * 2
                right_threshold = screen_center + zone_size * 2

                if predicted_x < left_threshold:
                    # Левая зона
                    zone_center_x = predicted_x + zone_size
                elif predicted_x > right_threshold:
                    # Правая зона
                    zone_center_x = predicted_x - zone_size
                else:
                    # Центральная зона
                    zone_center_x = predicted_x

                # Ограничиваем максимальное расстояние движения
                if zone_center_x > current_x:
                    optimal_x = int(min(zone_center_x, current_x + max_distance))
                else:
                    optimal_x = int(max(zone_center_x, current_x - max_distance))

                self._logger.debug(
                    f"[TARGET ADJUST] Мяч близко! time_to_paddle={time_to_paddle:.1f}, скорректирована цель с {original_optimal:.1f} на {optimal_x:.1f} (max_distance={max_distance:.1f})"
                )

            # Сохраняем целевую позицию
            current_target = self.separation_zone_tracker.target_position
            old_target_str = (
                f"{current_target:.1f}" if current_target is not None else "None"
            )
            self._logger.debug(
                f"[POSITION CHANGE] ФЛАГ: Платформа устанавливает новую цель (ПРАВИЛО 4)! paddle_x={current_x:.1f}, "
                f"старая_цель={old_target_str}, "
                f"новая_цель={optimal_x:.1f}, distance_to_target={abs(current_x - optimal_x):.1f}"
            )
            self.separation_zone_tracker.target_position = int(optimal_x)
            self.separation_zone_tracker.target_position_set = True
            self.separation_zone_tracker.paddle_moved_after_set = False
            self.separation_zone_tracker.paddle_reached_target = False
            self.separation_zone_tracker.frames_since_target_set = 0
            # КРИТИЧНО: Сохраняем vel_x для отслеживания отскоков от стены
            ball_vel_x_save = (
                self.current_game_state.ball_velocity.x
                if (
                    self.current_game_state
                    and hasattr(self.current_game_state, "ball_velocity")
                )
                else 0
            )
            self.separation_zone_tracker.saved_ball_vel_x = ball_vel_x_save
            self._log_paddle_movement(current_x, optimal_x, "target_position_set", 1.0)
            # Продолжаем обработку с установленной позицией
            target_pos = int(optimal_x)
            distance_to_target = abs(current_x - target_pos)

            # КРИТИЧНО: Проверяем, что движение действительно нужно
            # Если target_pos == current_x, не двигаемся
            if target_pos == current_x:
                self.separation_zone_tracker.paddle_reached_target = True
                return 0

            # КРИТИЧНО: В зоне разделения останавливаемся только если ОЧЕНЬ близко к цели
            # Увеличено до 25 пикселей для предотвращения дрожания
            if distance_to_target <= 25:
                self.separation_zone_tracker.paddle_reached_target = True
                # КРИТИЧНО: Логируем для диагностики
                # Фильтрация по уровню выполняется автоматически системой логирования Python
                self._logger.debug(
                    f"[PADDLE DEBUG] ПРАВИЛО 4: Платформа очень близко к цели (distance={distance_to_target:.1f} <= 5), не двигаемся"
                )
                return 0

            movement = (
                1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
            )
            # КРИТИЧНО: Проверяем, что movement не равен 0
            if movement == 0:
                # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                self._logger.warning(
                    f"[PADDLE DEBUG] ПРАВИЛО 4: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback"
                )
                return self._fallback_movement(current_x)

            # КРИТИЧНО: Логируем движение
            # Фильтрация по уровню выполняется автоматически системой логирования Python
            self._logger.debug(
                f"[PADDLE DEBUG] ПРАВИЛО 4: Движение! movement={movement}, distance={distance_to_target:.1f}, current_x={current_x}, target_pos={target_pos}"
            )

            self.separation_zone_tracker.paddle_moved_after_set = True
            self._update_loop_tracking(movement, int(current_x), int(target_pos))
            self._update_smoothness_tracking(movement, current_x)
            self._log_paddle_movement(
                current_x, target_pos, "moving_to_new_target", 0.9
            )
            # Записываем метрику производительности
            if self.performance_monitor and start_time_monitor:
                duration = time.time() - start_time_monitor
                self.performance_monitor.record_metric("move_paddle_towards", duration)
            return movement

        # Продолжаем обработку в следующей части метода
        return None
