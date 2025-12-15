"""
Модуль для работы с целями и кирпичами в AIPlayer.
Содержит методы поиска целей, обновления карты кирпичей и записи результатов ударов.
"""

import math
import time
from typing import List, Optional, Dict, Any

from .game_state import Point
from .exceptions import PredictionError


class AIPlayerTargetingMixin:
    """
    Миксин для методов работы с целями и кирпичами.
    Добавляет методы поиска целей, обновления карты кирпичей и записи результатов ударов.
    """
    
    def _generate_brick_cache_key(self) -> str:
        """
        Генерирует ключ кэша для текущего состояния кирпичей.
        
        Returns:
            Строковый ключ, уникальный для текущего набора кирпичей
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return ""
        
        bricks = self.current_game_state.remaining_bricks
        # Сортируем кирпичи по позиции для стабильности ключа
        # Используем координаты и размеры для создания уникального ключа
        key_parts = []
        for brick in sorted(bricks, key=lambda b: (getattr(b, "y", 0), getattr(b, "x", 0))):
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            # Используем целочисленные координаты для стабильности
            key_parts.append(f"{int(brick_x)},{int(brick_y)},{int(brick_width)},{int(brick_height)}")
        
        return "|".join(key_parts)

    def _update_brick_map(self, changed_brick_indices: Optional[List[int]] = None) -> None:
        """
        Обновляет карту всех кубиков на поле и координаты их центров.
        Использует кэширование для оптимизации производительности.
        
        Args:
            changed_brick_indices: Опциональный список индексов измененных блоков в списке remaining_bricks
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            self.targeting_system.brick_map = {}
            self.targeting_system.brick_coordinates = []
            self._brick_map_cache = None
            return
        
        # Если передан список измененных блоков, инвалидируем кэш только для них
        if changed_brick_indices:
            self._invalidate_trajectory_cache(changed_brick_indices)

        # Генерируем ключ кэша для текущего состояния кирпичей
        cache_key = self._generate_brick_cache_key()
        
        # Проверяем кэш
        if self._brick_map_cache and self._brick_map_cache[0] == cache_key:
            # Кэш попадание - используем закэшированные данные
            _, cached_brick_map, cached_brick_coordinates = self._brick_map_cache
            self.targeting_system.brick_map = cached_brick_map
            self.targeting_system.brick_coordinates = cached_brick_coordinates
            self._brick_cache_stats["hits"] += 1
            # Обновляем видимые цели (они могут измениться даже при тех же кирпичах)
            self._update_visible_targets()
            return

        # Кэш промах - строим новую карту
        self._brick_cache_stats["misses"] += 1
        
        brick_map: Dict[str, Dict[str, Any]] = {}
        brick_coordinates: List[Dict[str, Any]] = []

        for brick in self.current_game_state.remaining_bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)

            # Ключ для карты кирпичей
            brick_key = f"{int(brick_x / self.config.brick.default_width)}_{int(brick_y / self.config.brick.default_height)}"

            brick_info = {
                "x": brick_x,
                "y": brick_y,
                "width": brick_width,
                "height": brick_height,
                "center_x": brick_x + brick_width / 2,
                "center_y": brick_y + brick_height / 2,
                "row": int(brick_y / self.config.brick.default_height),
                "col": int(brick_x / self.config.brick.default_width),
            }

            brick_map[brick_key] = brick_info
            brick_coordinates.append(
                {
                    "x": brick_info["center_x"],
                    "y": brick_info["center_y"],
                    "brick": brick,
                    "key": brick_key,
                }
            )

        # Обновляем кэш
        self._brick_map_cache = (cache_key, brick_map, brick_coordinates)
        
        self.targeting_system.brick_map = brick_map
        self.targeting_system.brick_coordinates = brick_coordinates

        # Обновляем видимые цели для текущей траектории мяча
        self._update_visible_targets()

    def get_brick_cache_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования кэша карты кирпичей.
        
        Returns:
            Словарь со статистикой: hits, misses, hit_rate
        """
        total = self._brick_cache_stats["hits"] + self._brick_cache_stats["misses"]
        hit_rate = (
            self._brick_cache_stats["hits"] / total
            if total > 0
            else 0.0
        )
        return {
            "hits": self._brick_cache_stats["hits"],
            "misses": self._brick_cache_stats["misses"],
            "total": total,
            "hit_rate": hit_rate,
        }

    def _update_visible_targets(self) -> None:
        """
        Обновляет список видимых целей (кубиков), в которые можно прицельно ударить
        с учётом текущей траектории мяча и возможных смещений по платформе.
        """
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            self.targeting_system.visible_targets = []
            return

        try:
            # Точка приземления мяча при текущей траектории
            landing_x = self._predict_exact_landing_position()

            visible_targets: List[Dict[str, Any]] = []

            # Несколько тестовых смещений платформы относительно точки приземления
            test_offsets = [-40, -20, 0, 20, 40]

            for offset in test_offsets:
                test_x = landing_x + offset

                # Строго ограничиваем позицию возможного центра платформы
                paddle_half_width = self.paddle_width / 2
                test_x = max(
                    paddle_half_width,
                    min(self.screen_width - paddle_half_width, test_x),
                )

                # Временное состояние игры с тестовой позицией платформы
                temp_game_state = self.current_game_state.clone()
                temp_game_state.paddle_position.x = test_x

                # Точка пересечения мяча с платформой
                intersection_point = (
                    self.trajectory_predictor.predict_paddle_intersection(
                        temp_game_state,
                        self.current_game_state.paddle_position.y,
                    )
                )
                if intersection_point is None:
                    continue

                # Траектория после отскока с данной позиции
                after_bounce_trajectory = (
                    self.trajectory_predictor.predict_after_bounce_trajectory(
                        temp_game_state,
                        intersection_point,
                        test_x,
                    )
                )

                # Проверяем, какие кубики пересекает эта траектория
                # Используем точную проверку пересечения с границами кубиков
                for coord in self.targeting_system.brick_coordinates:
                    brick = coord["brick"]
                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", self.config.brick.default_width)
                    brick_height = getattr(brick, "height", 20)
                    
                    # Точные границы кубика
                    brick_left = brick_x
                    brick_right = brick_x + brick_width
                    brick_top = brick_y
                    brick_bottom = brick_y + brick_height
                    
                    # Радиус мяча для проверки пересечения
                    ball_radius = self.config.ball.radius
                    
                    # Проверяем пересечение траектории с кубиком
                    # Используем более частую проверку для точности
                    for point in after_bounce_trajectory:
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue
                            
                        # Проверяем пересечение мяча (с учетом радиуса) с границами кубика
                        if (
                            brick_left - ball_radius
                            <= point.x
                            <= brick_right + ball_radius
                            and brick_top - ball_radius
                            <= point.y
                            <= brick_bottom + ball_radius
                        ):
                            # Дополнительная проверка: мяч действительно попадает в кубик
                            # Проверяем, что центр мяча находится в расширенной области кубика
                            if (
                                brick_left <= point.x <= brick_right
                                or brick_top <= point.y <= brick_bottom
                                or math.sqrt(
                                    (point.x - (brick_left + brick_right) / 2) ** 2
                                    + (point.y - (brick_top + brick_bottom) / 2) ** 2
                                )
                                < (brick_width / 2 + ball_radius)
                            ):
                                if coord not in visible_targets:
                                    visible_targets.append(coord)
                                break

            self.targeting_system.visible_targets = visible_targets
        except (AttributeError, TypeError, ValueError) as e:
            self._logger.warning(f"Ошибка при обновлении видимых целей: {e}", exc_info=True)
            self.targeting_system.visible_targets = []
        except PredictionError as e:
            self._logger.error(f"Ошибка предсказания при обновлении видимых целей: {e}", exc_info=True)
            self.targeting_system.visible_targets = []

    def record_hit_result(
        self,
        brick_hit: Any,
        paddle_offset: float,
        success: bool,
    ) -> None:
        """
        Записывает результат удара по кубику для обучения системы прицеливания.

        Args:
            brick_hit: Объект/описание сбитого кубика.
            paddle_offset: Смещение по платформе (-1..1).
            success: Был ли удар успешным.
        """
        brick_x = getattr(brick_hit, "x", 0)
        brick_y = getattr(brick_hit, "y", 0)
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        hit_patterns = self.targeting_system.hit_patterns

        if brick_key not in hit_patterns:
            hit_patterns[brick_key] = {
                "total_attempts": 0,
                "successful_hits": 0,
                "success_rate": 0.0,
                "successful_offsets": [],
            }

        pattern = hit_patterns[brick_key]
        pattern["total_attempts"] += 1

        if success:
            pattern["successful_hits"] += 1
            pattern["successful_offsets"].append(paddle_offset)
            # Ограничиваем историю
            if len(pattern["successful_offsets"]) > 20:
                pattern["successful_offsets"] = pattern["successful_offsets"][-10:]

        pattern["success_rate"] = (
            pattern["successful_hits"] / pattern["total_attempts"]
            if pattern["total_attempts"] > 0
            else 0.0
        )

        # Глобальная история успешных ударов
        if success:
            self.targeting_system.successful_hits.append(
                {
                    "brick_key": brick_key,
                    "offset": paddle_offset,
                    "ball_speed": (
                        self.current_game_state.ball_speed
                        if self.current_game_state
                        else 5
                    ),
                    "timestamp": time.time(),
                }
            )
            if len(self.targeting_system.successful_hits) > self.config.successful_hits_max:
                self.targeting_system.successful_hits = self.targeting_system.successful_hits[-self.config.successful_hits_keep:]

    def _find_best_target_brick(self) -> Optional[Any]:
        """
        Находит лучший кубик для прицеливания с учётом видимости, позиции платформы и траектории.

        Приоритеты:
        1. На поздних этапах (<= 15 блоков) - максимизация разрушений в следующем цикле.
        2. Кубики, видимые для текущей траектории.
        3. Кубики в нижних рядах (ближе к платформе).
        4. Кубики ближе к центру экрана (стабильнее).
        5. Кубики с хорошей историей попаданий.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks_count = len(self.current_game_state.remaining_bricks)
        
        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            return self._find_optimal_angle_for_max_destruction()

        visible_targets = self.targeting_system.visible_targets
        paddle_y = self.current_game_state.paddle_position.y

        # 1. Сначала рассматриваем только видимые цели
        if visible_targets:
            best_visible_brick = None
            best_visible_score = -float("inf")
            
            # Получаем историю последних выбранных целей для проверки симметрии
            recent_targets = self.targeting_system.recent_target_positions
            screen_center = self.screen_width // 2

            for target in visible_targets:
                brick = target["brick"]
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_center_x = brick_x + brick_width / 2

                score = 1000.0  # базовый бонус за видимость

                # Бонус за близость к платформе
                distance_to_paddle = paddle_y - brick_y
                if distance_to_paddle > 0:
                    score += (1.0 / distance_to_paddle) * 500.0

                # Штраф за удалённость от центра
                center_distance = abs(brick_center_x - screen_center)
                score -= center_distance * 0.3

                # Проверка на симметричные паттерны
                if recent_targets:
                    for prev_target_x in recent_targets[-3:]:
                        symmetry_distance = abs(
                            abs(brick_center_x - screen_center)
                            - abs(prev_target_x - screen_center)
                        )
                        if symmetry_distance < 20:
                            score -= 300.0
                        
                        if (
                            abs(brick_center_x - screen_center) < 30
                            and abs(prev_target_x - screen_center) < 30
                            and (brick_center_x - screen_center)
                            * (prev_target_x - screen_center)
                            < 0
                        ):
                            score -= 400.0

                # Бонус за успешную историю попаданий
                brick_key = target["key"]
                if brick_key in self.targeting_system.hit_patterns:
                    pattern = self.targeting_system.hit_patterns[brick_key]
                    score += pattern.get("success_rate", 0.0) * 200.0

                if score > best_visible_score:
                    best_visible_score = score
                    best_visible_brick = brick

            if best_visible_brick:
                # Сохраняем позицию выбранной цели
                selected_brick_x = (
                    getattr(best_visible_brick, "x", 0)
                    + getattr(best_visible_brick, "width", self.config.brick.default_width) / 2
                )
                if not self.targeting_system.recent_target_positions:
                    self.targeting_system.recent_target_positions = []
                self.targeting_system.recent_target_positions.append(selected_brick_x)
                if len(self.targeting_system.recent_target_positions) > self.config.recent_targets_max:
                    self.targeting_system.recent_target_positions = (
                        self.targeting_system.recent_target_positions[-self.config.recent_targets_max:]
                    )
                return best_visible_brick

        # 2. Резервная логика, если нет видимых целей
        bricks = self.current_game_state.remaining_bricks
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y

        # Если кубиков мало — отдельная логика
        if len(bricks) <= 5:
            return self._find_best_target_for_few_bricks(bricks, paddle_y, ball_x)

        # Проверяем, отбивается ли мяч от потолка
        is_ceiling_bounce = ball_y < 100 and self.current_game_state.ball_velocity.y > 0

        best_brick = None
        best_score = -float("inf")

        recent_targets = self.targeting_system.recent_target_positions
        screen_center = self.screen_width // 2

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 1000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            # Проверка на симметричные паттерны
            if recent_targets:
                for prev_target_x in recent_targets[-3:]:
                    symmetry_distance = abs(
                        abs(brick_center_x - screen_center)
                        - abs(prev_target_x - screen_center)
                    )
                    if symmetry_distance < 20:
                        score -= 200.0
                    
                    if (
                        abs(brick_center_x - screen_center) < 30
                        and abs(prev_target_x - screen_center) < 30
                        and (brick_center_x - screen_center)
                        * (prev_target_x - screen_center)
                        < 0
                    ):
                        score -= 300.0

            if is_ceiling_bounce:
                center_distance = abs(brick_center_x - screen_center)
                score -= center_distance * 0.3
                edge_distance = min(brick_center_x, self.screen_width - brick_center_x)
                score += edge_distance * 0.2
            else:
                horizontal_distance = abs(brick_center_x - ball_x)
                score -= horizontal_distance * 0.5

            # Бонус за историю попаданий
            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system.hit_patterns:
                pattern = self.targeting_system.hit_patterns[brick_key]
                score += pattern.get("success_rate", 0.0) * 100.0

            if score > best_score:
                best_score = score
                best_brick = brick

        if best_brick:
            selected_brick_x = (
                getattr(best_brick, "x", 0) + getattr(best_brick, "width", 60) / 2
            )
            if not self.targeting_system.recent_target_positions:
                self.targeting_system.recent_target_positions = []
            self.targeting_system.recent_target_positions.append(selected_brick_x)
            if len(self.targeting_system.recent_target_positions) > self.config.recent_targets_max:
                self.targeting_system.recent_target_positions = (
                    self.targeting_system.recent_target_positions[-self.config.recent_targets_max:]
                )

        return best_brick

    # Методы _find_optimal_angle_for_max_destruction, _count_bricks_in_trajectory,
    # _find_first_brick_in_trajectory теперь в ai_player_target_selection_part1.py

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
        if not successful_offsets or not isinstance(successful_offsets, list):
            return offset
        
        offset_values = [float(x) for x in successful_offsets if isinstance(x, (int, float))]
        if not offset_values:
            return offset

        avg_successful_offset = sum(offset_values) / len(offset_values)
        return float(offset * 0.7 + avg_successful_offset * 0.3)
