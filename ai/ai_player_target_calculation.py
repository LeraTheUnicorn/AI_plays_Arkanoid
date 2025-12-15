"""
Модуль расчета целевой позиции AIPlayer.

Содержит методы расчета оптимальной позиции платформы на основе траектории мяча и оставшихся кубиков.
"""

import math
from typing import Dict, Any, Optional


class AIPlayerTargetCalculationMixin:
    """Миксин для методов расчета целевой позиции AIPlayer."""

    def _calculate_target_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float]
    ) -> int:
        """
        Рассчитывает целевую позицию платформы на основе траектории и оставшихся кубиков.
        
        Args:
            landing_x: Предсказанная X-координата приземления мяча
            ball_y: Y-координата мяча
            zones: Словарь с границами зон
            
        Returns:
            Оптимальная позиция платформы
        """
        bricks_count = (
            len(self.current_game_state.remaining_bricks)
            if self.current_game_state
            else 0
        )
        ball_speed = (
            self.current_game_state.ball_speed if self.current_game_state else self.config.ball.default_speed
        )

        # Получаем текущую ситуацию для learning_system
        current_situation = {
            "bricks_remaining": bricks_count,
            "ball_speed": ball_speed,
            "time_pressure": self._is_time_pressure(),
        }

        # Применяем пользовательские правила из промпта "разрушение и контроль"
        user_rules = self.learning_system.apply_user_prompt_rules(current_situation)

        # Получаем рекомендации по стратегии (для будущего использования)
        _strategy_weights = self.learning_system.get_strategy_recommendation(
            current_situation
        )

        # КРИТИЧНО: Для малого количества блоков (<=10) ВСЕГДА используем точное прицеливание
        # КРИТИЧНО: Для последнего кирпича (<=1) ПРИНУДИТЕЛЬНО используем максимально точное прицеливание
        precision_priority = (
            user_rules.get("precision_priority", False) or 
            bricks_count <= self.config.precision_priority_threshold or
            bricks_count <= 1  # Принудительно для последнего кирпича
        )
        
        # Применяем правила из промпта: если указан приоритет точности, используем его
        if user_rules.get("destruction_priority", False):
            precision_priority = True  # Приоритет разрушения всех блоков
        
        # КРИТИЧНО: Если было отбитие в пустоту, принудительно используем точное прицеливание
        if self.empty_bounce_tracker["consecutive_empty_bounces"] >= self.empty_bounce_tracker["max_empty_bounces"]:
            precision_priority = True
            # Используем координаты кубиков напрямую из brick_coordinates
            if self.targeting_system.brick_coordinates:
                optimal_position = self._force_target_brick_from_coordinates(landing_x)
                if optimal_position is not None:
                    # КРИТИЧНО: Применяем защиту от попадания в углы платформы
                    safe_margin = 30
                    paddle_half_width = self.paddle_width / 2
                    min_position = paddle_half_width + safe_margin
                    max_position = self.screen_width - paddle_half_width - safe_margin
                    optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                    optimal_position = max(min_position, min(max_position, int(optimal_position)))
                    
                    # Сбрасываем целевую позицию и устанавливаем новую
                    self.separation_zone_tracker.target_position_set = False
                    self.separation_zone_tracker.target_position = None
                    in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
                    if in_separation_zone:
                        self.separation_zone_tracker.target_position = int(optimal_position)
                        self.separation_zone_tracker.target_position_set = True
                    if self.current_game_state:
                        self._log_paddle_movement(
                            self.current_game_state.paddle_position.x,
                            int(optimal_position),
                            f"ПРИНУДИТЕЛЬНОЕ прицеливание после {self.empty_bounce_tracker['consecutive_empty_bounces']} отбитий в пустоту. Координаты кубиков: {len(self.targeting_system.brick_coordinates)}",
                            1.0
                        )
                    return int(optimal_position)

        if precision_priority:
            if not self.current_game_state:
                return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
            
            # КРИТИЧНО: Для малого количества кирпичей ВСЕГДА используем точное прицеливание
            # Даже если calculate_precise_position_for_few_bricks вернет None, используем _calculate_precision_position
            # который имеет fallback логику с прицеливанием по координатам кирпичей
            optimal_position = self.position_calculator.calculate_precise_position_for_few_bricks(
                landing_x, self.current_game_state
            )
            
            # КРИТИЧНО: Логируем, если метод вернул None для диагностики
            if optimal_position is None and bricks_count <= 3:
                self._logger.warning(
                    f"[PRECISION TARGETING] calculate_precise_position_for_few_bricks вернул None "
                    f"для {bricks_count} кирпичей! Используем fallback с прицеливанием."
                )
            
            # Всегда вызываем _calculate_precision_position, который имеет fallback логику
            return self._calculate_precision_position(landing_x, ball_y, zones, bricks_count, ball_speed, user_rules)

        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            if not self.current_game_state:
                return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
            optimal_position = self.position_calculator.calculate_position_for_max_destruction(
                landing_x, self.current_game_state
            )
            if optimal_position is not None and self.current_game_state:
                action_plan = {
                    "ball_speed": ball_speed,
                    "movement_distance": abs(
                        optimal_position - self.current_game_state.paddle_position.x
                    ),
                    "confidence": self.config.confidence_default,
                }
                success_prob = self.learning_system.predict_success_probability(action_plan)
                if success_prob > self.config.success_probability_threshold:
                    if self.separation_zone_tracker.target_position_set:
                        target_pos = self.separation_zone_tracker.target_position
                        if target_pos is not None:
                            return int(target_pos)
                    # КРИТИЧНО: Применяем защиту от попадания в углы платформы
                    safe_margin = 30
                    paddle_half_width = self.paddle_width / 2
                    min_position = paddle_half_width + safe_margin
                    max_position = self.screen_width - paddle_half_width - safe_margin
                    optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                    optimal_position = max(min_position, min(max_position, int(optimal_position)))
                    return int(optimal_position)

        # Ищем целевой кирпич и рассчитываем позицию
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        game_state = self.current_game_state
        target_brick = self.target_selector.find_best_target_brick(
            game_state,
            game_state.paddle_position.y,
            game_state.ball_position.x,
        )
        if target_brick:
            optimal_position = self.position_calculator.calculate_position_with_target_brick(
                landing_x, target_brick, game_state, zones
            )
            if optimal_position is not None:
                # КРИТИЧНО: Применяем защиту от попадания в углы платформы
                safe_margin = 30
                paddle_half_width = self.paddle_width / 2
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                return int(optimal_position)
        return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)

    def _calculate_precision_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float],
        bricks_count: int, ball_speed: int, user_rules: Dict[str, Any]
    ) -> int:
        """Рассчитывает точную позицию для малого количества блоков."""
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        
        # КРИТИЧНО: Для последнего кирпича используем специальную логику
        if bricks_count == 1:
            # Находим последний кирпич
            target_brick = None
            if self.current_game_state.remaining_bricks:
                target_brick = self.current_game_state.remaining_bricks[0]
            
            if target_brick:
                # Используем точный расчет позиции с учетом целевого кирпича
                optimal_offset = self.position_calculator.calculate_optimal_offset(
                    landing_x, target_brick, self.current_game_state
                )
                paddle_half_width = self.paddle_width / 2
                optimal_position = landing_x - (optimal_offset * paddle_half_width)
                
                # Обеспечиваем безопасную позицию
                safe_margin = 30
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                
                # КРИТИЧНО: Для последнего кирпича не проверяем success_probability - всегда используем расчет
                in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
                if in_separation_zone:
                    self._set_target_position_if_needed(int(optimal_position), "last_brick_precision")
                
                if self.current_game_state:
                    brick_x = getattr(target_brick, "x", 0)
                    brick_y = getattr(target_brick, "y", 0)
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        int(optimal_position),
                        f"КРИТИЧНО: Точное прицеливание в ПОСЛЕДНИЙ кирпич ({brick_x:.0f}, {brick_y:.0f}), offset={optimal_offset:.2f}",
                        1.0  # Максимальная уверенность
                    )
                return int(optimal_position)
        
        optimal_position = self.position_calculator.calculate_precise_position_for_few_bricks(
            landing_x, self.current_game_state
        )
        
        # КРИТИЧНО: Если метод вернул None, используем fallback с прицеливанием по координатам
        if optimal_position is None:
            if self.targeting_system.brick_coordinates:
                optimal_position = self._force_target_brick_from_coordinates(landing_x)
                if optimal_position is not None:
                    self._logger.warning(
                        f"[PRECISION FALLBACK] Используем _force_target_brick_from_coordinates "
                        f"для {bricks_count} кирпичей"
                    )
            else:
                # Если нет координат кирпичей, используем упрощенный расчет на основе текущего состояния
                if self.current_game_state and self.current_game_state.remaining_bricks:
                    bricks = self.current_game_state.remaining_bricks
                    closest_brick = min(
                        bricks,
                        key=lambda b: (
                            self.current_game_state.paddle_position.y - getattr(b, "y", 0),
                            abs((getattr(b, "x", 0) + getattr(b, "width", 60) / 2) - landing_x),
                        ),
                    )
                    brick_center_x = getattr(closest_brick, "x", 0) + getattr(closest_brick, "width", 60) / 2
                    paddle_half_width = self.paddle_width / 2
                    dx = brick_center_x - landing_x
                    required_offset = max(-1.5, min(1.5, dx / (paddle_half_width * 1.5)))
                    optimal_position = landing_x - (required_offset * paddle_half_width)
                    min_position = paddle_half_width + 30
                    max_position = self.screen_width - paddle_half_width - 30
                    optimal_position = max(min_position, min(max_position, optimal_position))
                    self._logger.warning(
                        f"[PRECISION FALLBACK] Используем упрощенный расчет для {bricks_count} кирпичей, "
                        f"brick_center_x={brick_center_x:.0f}, optimal_position={optimal_position:.0f}"
                    )
        
        if optimal_position is not None:
            if not self.current_game_state:
                return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
            action_plan = {
                "ball_speed": ball_speed,
                "movement_distance": abs(
                    optimal_position - self.current_game_state.paddle_position.x
                ),
                "confidence": 0.8,
            }
            success_prob = self.learning_system.predict_success_probability(action_plan)
            if success_prob > self.config.low_success_probability_threshold or bricks_count <= self.config.precision_priority_threshold:
                in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
                if self.separation_zone_tracker.target_position_set:
                    target_pos = self.separation_zone_tracker.target_position
                    if target_pos is not None:
                        return int(target_pos)
                
                # КРИТИЧНО: Применяем защиту от попадания в углы платформы
                safe_margin = 30
                paddle_half_width = self.paddle_width / 2
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                
                if in_separation_zone:
                    self._set_target_position_if_needed(int(optimal_position), "few_bricks")
                
                if user_rules.get("use_movement_log", True) and self.current_game_state:
                    brick_coords = [f"({b.get('x', 0):.0f},{b.get('y', 0):.0f})" for b in self.targeting_system.brick_coordinates]
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        int(optimal_position),
                        f"Точное прицеливание в {bricks_count} блоков. Координаты: {', '.join(brick_coords[:5])}",
                        0.9
                    )
                return int(optimal_position)
        
        return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)

    def _calculate_position_with_target_brick(
        self, landing_x: float, ball_y: float, zones: Dict[str, float], bricks_count: int
    ) -> int:
        """Рассчитывает позицию с учетом целевого кирпича."""
        if not self.current_game_state:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)
        game_state = self.current_game_state
        target_brick = self.target_selector.find_best_target_brick(
            game_state,
            game_state.paddle_position.y,
            game_state.ball_position.x,
        )
        
        if target_brick:
            optimal_offset = self.position_calculator.calculate_optimal_offset(
                landing_x, target_brick, game_state
            )
            self.targeting_system.target_brick = target_brick
            self.targeting_system.optimal_offset = optimal_offset
            
            paddle_half_width = self.paddle_width / 2
            optimal_position = landing_x - (optimal_offset * paddle_half_width)
            
            # Обеспечиваем безопасную позицию
            safe_margin = 30
            min_position = paddle_half_width + safe_margin
            max_position = self.screen_width - paddle_half_width - safe_margin
            optimal_position = max(min_position, min(max_position, optimal_position))
            
            # Дополнительная проверка границ
            paddle_left_edge = optimal_position - paddle_half_width
            paddle_right_edge = optimal_position + paddle_half_width
            if paddle_left_edge < safe_margin:
                optimal_position = safe_margin + paddle_half_width
            elif paddle_right_edge > self.screen_width - safe_margin:
                optimal_position = self.screen_width - safe_margin - paddle_half_width
            
            # Учитываем предпочтения позиций
            position_preference = self.learning_system.get_optimal_position_preference(
                int(optimal_position)
            )
            if position_preference < 0.4:
                if not self.separation_zone_tracker.target_position_set:
                    for offset in range(self.config.paddle_zone_offset_range[0], self.config.paddle_zone_offset_range[1], self.config.paddle_zone_offset_step):
                        test_x = int(optimal_position) + offset
                        if min_position <= test_x <= max_position:
                            pref = self.learning_system.get_optimal_position_preference(test_x)
                            if pref > 0.6:
                                return test_x
            
            in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
            if in_separation_zone and not self.separation_zone_tracker.target_position_set and self.current_game_state:
                self.separation_zone_tracker.target_position = int(optimal_position)
                self.separation_zone_tracker.target_position_set = True
            
            if self.current_game_state:
                self._log_paddle_movement(
                    self.current_game_state.paddle_position.x,
                    int(optimal_position),
                    f"Прицеливание в целевой блок (осталось {bricks_count} блоков)",
                    0.8
                )
            return int(optimal_position)
        else:
            return self._calculate_fallback_position(landing_x, ball_y, zones, bricks_count)

    def _ensure_safe_paddle_position(
        self, paddle_center_x: float, landing_x: float
    ) -> float:
        """
        Обеспечивает безопасную позицию платформы, предотвращая попадание мяча в углы.
        
        Если предсказанная точка приземления (landing_x) слишком близко к краю платформы,
        смещает позицию платформы так, чтобы мяч попадал в безопасную зону (минимум 25px от края).
        
        Args:
            paddle_center_x: Текущая позиция центра платформы
            landing_x: Предсказанная X-координата приземления мяча
            
        Returns:
            Скорректированная позиция центра платформы
        """
        paddle_half_width = self.paddle_width / 2
        ball_radius = 8  # Радиус мяча
        safe_edge_distance = 25  # Минимальное расстояние от края платформы до точки попадания мяча
        
        # Вычисляем края платформы при текущей позиции
        paddle_left_edge = paddle_center_x - paddle_half_width
        paddle_right_edge = paddle_center_x + paddle_half_width
        
        # Вычисляем расстояние от точки приземления до краев платформы
        distance_to_left_edge = landing_x - paddle_left_edge
        distance_to_right_edge = paddle_right_edge - landing_x
        
        # Если мяч попадает слишком близко к левому краю
        if distance_to_left_edge < safe_edge_distance:
            # Смещаем платформу вправо, чтобы мяч попадал в безопасную зону
            adjustment = safe_edge_distance - distance_to_left_edge
            paddle_center_x += adjustment
            self._logger.debug(
                f"[SAFE POSITION] Мяч слишком близко к левому краю (distance={distance_to_left_edge:.1f}px), "
                f"смещаем платформу вправо на {adjustment:.1f}px"
            )
        
        # Если мяч попадает слишком близко к правому краю
        elif distance_to_right_edge < safe_edge_distance:
            # Смещаем платформу влево, чтобы мяч попадал в безопасную зону
            adjustment = safe_edge_distance - distance_to_right_edge
            paddle_center_x -= adjustment
            self._logger.debug(
                f"[SAFE POSITION] Мяч слишком близко к правому краю (distance={distance_to_right_edge:.1f}px), "
                f"смещаем платформу влево на {adjustment:.1f}px"
            )
        
        # Ограничиваем границами экрана
        safe_margin = 30
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        paddle_center_x = max(min_position, min(max_position, paddle_center_x))
        
        return paddle_center_x

    def _calculate_fallback_position(
        self, landing_x: float, ball_y: float, zones: Dict[str, float], bricks_count: int
    ) -> int:
        """Рассчитывает резервную позицию, когда нет явной цели."""
        in_separation_zone = zones["separation_zone_start"] <= ball_y < zones["paddle_zone_start"]
        
        if bricks_count <= self.config.precision_priority_threshold and self.targeting_system.brick_coordinates:
            if self.separation_zone_tracker.target_position_set:
                target_pos = self.separation_zone_tracker.target_position
                if target_pos is not None:
                    return int(target_pos)
            
            optimal_position = self._force_target_brick_from_coordinates(landing_x)
            if optimal_position is not None:
                safe_margin = 30
                paddle_half_width = self.paddle_width / 2
                min_position = paddle_half_width + safe_margin
                max_position = self.screen_width - paddle_half_width - safe_margin
                optimal_position = max(min_position, min(max_position, optimal_position))
                
                # КРИТИЧНО: Применяем защиту от попадания в углы платформы
                optimal_position = self._ensure_safe_paddle_position(float(optimal_position), landing_x)
                optimal_position = max(min_position, min(max_position, int(optimal_position)))
                
                if in_separation_zone:
                    self._set_target_position_if_needed(int(optimal_position), "brick_coords")
                
                if self.current_game_state:
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        int(optimal_position),
                        f"Прицеливание по координатам (осталось {bricks_count} блоков)",
                        0.7
                    )
                return int(optimal_position)
        
        if in_separation_zone and self.separation_zone_tracker.target_position_set:
            fixed_position = self.separation_zone_tracker.target_position
            if fixed_position is not None:
                return int(fixed_position)
        
        safe_margin = 30
        paddle_half_width = self.paddle_width / 2
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        base_position = max(min_position, min(max_position, int(landing_x)))
        
        # КРИТИЧНО: Применяем защиту от попадания в углы платформы
        base_position = self._ensure_safe_paddle_position(float(base_position), landing_x)
        base_position = max(min_position, min(max_position, int(base_position)))
        
        if in_separation_zone:
            self._set_target_position_if_needed(int(base_position), "простое движение")
        
        if self.current_game_state is not None:
            self._log_paddle_movement(
                self.current_game_state.paddle_position.x,
                base_position,
                f"Простое движение к мячу (осталось {bricks_count} блоков)",
                0.5
            )
        
        base_position_int = int(base_position)
        position_preference = self.learning_system.get_optimal_position_preference(base_position_int)
        if position_preference < 0.4:
            for offset in range(-40, 41, 10):
                test_x = base_position_int + offset
                if min_position <= test_x <= max_position:
                    pref = self.learning_system.get_optimal_position_preference(test_x)
                    if pref > 0.6:
                        return test_x
        return base_position_int

    def _set_target_position_if_needed(self, position: int, reason: str) -> None:
        """
        Устанавливает целевую позицию, если она еще не установлена.
        
        ✅ ИСПРАВЛЕНО: Использует target_tracker для проверки максимального расстояния.
        """
        # ✅ ИСПРАВЛЕНО: Получаем текущую позицию платформы для проверки расстояния
        current_pos = None
        if self.current_game_state:
            current_pos = int(self.current_game_state.paddle_position.x)
        
        # ✅ ИСПРАВЛЕНО: Используем target_tracker для установки позиции с проверкой расстояния
        self.target_tracker.set_target_position(position, reason, self._logger, current_pos)
