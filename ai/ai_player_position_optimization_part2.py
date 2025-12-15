"""
Модуль оптимизации позиций AIPlayer (часть 2).

Содержит методы для максимизации разрушений, подсчета блоков в траектории
и расчета оптимального смещения.
"""

import math
from typing import List, Optional, Any

from .game_state import Point


class AIPlayerPositionOptimizationPart2Mixin:
    """Миксин для методов оптимизации позиций AIPlayer (часть 2)."""

    def _find_optimal_angle_for_max_destruction(self) -> Optional[Any]:
        """
        Находит оптимальный угол удара для максимизации количества разрушенных блоков
        в следующем цикле отскоков. Используется на поздних этапах игры (<= 15 блоков).
        
        Returns:
            Целевой кубик, который приведет к максимальному количеству разрушений.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        landing_x = self._predict_exact_landing_position()
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        # Тестируем различные углы удара (смещения на платформе)
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0
        best_target_brick = None
        
        for offset in test_offsets:
            # Вычисляем позицию отскока на платформе
            bounce_x = landing_x - (offset * paddle_half_width)
            
            # Ограничиваем границами платформы
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            # Получаем точку пересечения с платформой
            intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state, paddle_y
            )
            
            if intersection_point is None:
                continue
            
            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Подсчитываем количество блоков, которые будут разрушены
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            # Если это лучший результат, сохраняем
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset
                
                # Находим первый блок, который будет разрушен
                first_hit_brick = self._find_first_brick_in_trajectory(
                    after_bounce_trajectory, self.current_game_state.remaining_bricks
                )
                if first_hit_brick:
                    best_target_brick = first_hit_brick
        
        # Если нашли оптимальный угол, возвращаем соответствующий целевой блок
        if best_target_brick:
            return best_target_brick
        
        # Fallback: используем стандартную логику для малого количества блоков
        return self._find_best_target_for_few_bricks(
            self.current_game_state.remaining_bricks,
            paddle_y,
            self.current_game_state.ball_position.x,
        )

    def _count_bricks_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> int:
        """
        Подсчитывает количество блоков, которые будут разрушены траекторией.
        Использует точные координаты кубиков для более точного подсчета.
        
        Args:
            trajectory: Траектория мяча после отскока.
            bricks: Список оставшихся блоков.
            
        Returns:
            Количество блоков, которые будут разрушены.
        """
        if not trajectory or not bricks:
            return 0
        
        destroyed_bricks = set()
        ball_radius = self.config.ball.radius  # Радиус мяча
        
        # Используем более частую проверку для точности
        # Проверяем каждую точку траектории (не каждую вторую)
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                # Пропускаем уже учтенные блоки
                brick_id = id(brick)
                if brick_id in destroyed_bricks:
                    continue
                
                # Точные координаты кубика
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                # Точные границы кубика
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                # Точная проверка пересечения мяча (с учетом радиуса) с границами кубика
                # Мяч пересекает кубик, если его центр находится в расширенной области кубика
                # или если мяч касается границ кубика
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    # Дополнительная проверка: мяч действительно попадает в кубик
                    # Проверяем, что центр мяча находится в области кубика или очень близко к границам
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    # Проверяем расстояние от центра мяча до ближайшей точки кубика
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
        """
        Находит первый блок, который будет разрушен траекторией.
        Использует точные координаты кубиков для более точного определения.
        
        Args:
            trajectory: Траектория мяча после отскока.
            bricks: Список оставшихся блоков.
            
        Returns:
            Первый блок, который будет разрушен, или None.
        """
        if not trajectory or not bricks:
            return None
        
        ball_radius = self.config.ball.radius
        min_distance = float("inf")
        first_brick = None
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                # Точные координаты кубика
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                
                # Точные границы кубика
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                # Точная проверка пересечения мяча (с учетом радиуса) с границами кубика
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    # Дополнительная проверка: мяч действительно попадает в кубик
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    # Проверяем расстояние от центра мяча до ближайшей точки кубика
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        # Вычисляем расстояние от начала траектории
                        distance = math.sqrt(
                            (point.x - trajectory[0].x) ** 2
                            + (point.y - trajectory[0].y) ** 2
                        )
                        
                        if distance < min_distance:
                            min_distance = distance
                            first_brick = brick
                            break  # Нашли первый кубик, выходим из внутреннего цикла
        
        return first_brick

    def _find_best_target_for_few_bricks(
        self,
        bricks: List[Any],
        paddle_y: float,
        ball_x: float,
    ) -> Optional[Any]:
        """
        Специальная логика выбора цели для малого количества оставшихся кубиков.
        Помогает быстрее завершить уровень и избегать симметричных циклов.
        """
        if not bricks:
            return None

        # КРИТИЧНО: Для 1 кирпича - используем улучшенную логику с максимальным приоритетом
        if len(bricks) == 1:
            brick = bricks[0]
            # Всегда выбираем единственный оставшийся кирпич
            # Логируем его координаты для отладки с максимальным приоритетом
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_center_x = brick_x + getattr(brick, "width", 60) / 2
            self._logger.warning(
                f"[LAST BRICK CRITICAL] КРИТИЧНО: Таргетирование ПОСЛЕДНЕГО кирпича! "
                f"x={brick_x:.0f}, y={brick_y:.0f}, center_x={brick_center_x:.0f}, "
                f"ball_x={ball_x:.0f}, paddle_y={paddle_y:.0f}"
            )
            return brick

        # Для 2-3 кубиков — самый нижний, но с учетом траектории
        if len(bricks) <= 3:
            # Находим самый нижний кирпич
            bottom_brick = min(bricks, key=lambda b: getattr(b, "y", 0))
            
            # Но также проверяем, есть ли кирпич ближе к текущей траектории мяча
            ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
            vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
            
            # Если мяч движется горизонтально, приоритезируем кирпичи в направлении движения
            for brick in bricks:
                brick_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
                brick_y = getattr(brick, "y", 0)
                
                # Если кирпич находится в направлении движения мяча и не слишком высоко
                if abs(brick_x - ball_x) < 150 and brick_y <= bottom_brick.y + 30:
                    # Проверяем, будет ли мяч двигаться в направлении этого кирпича
                    if (vel_x > 0 and brick_x > ball_x) or (vel_x < 0 and brick_x < ball_x):
                        return brick
            
            return bottom_brick

        # Для 4–5 — более сложная оценка
        best_brick = None
        best_score = -float("inf")

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            # Максимальный приоритет нижним кубикам
            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 2000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            # Центр — более предсказуемая зона
            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3

            # Бонус за близость к текущей траектории
            horizontal_distance = abs(brick_center_x - ball_x)
            score -= horizontal_distance * 0.2

            # История успехов
            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system.hit_patterns:
                pattern = self.targeting_system.hit_patterns[brick_key]
                score += pattern.get("success_rate", 0.0) * 300.0

            if score > best_score:
                best_score = score
                best_brick = brick

        return best_brick

    def _calculate_optimal_offset(self, landing_x: float, target_brick: Any) -> float:
        """
        Рассчитывает оптимальное смещение на платформе для попадания в кубик.
        Использует точные координаты кубика для избежания пропущенных попаданий.

        Args:
            landing_x: X-координата приземления мяча.
            target_brick: Целевой кубик.

        Returns:
            Смещение от -1.0 до 1.0 (0 — центр платформы).
        """
        if not target_brick or not self.current_game_state:
            return 0.0
        
        bricks_count = len(self.current_game_state.remaining_bricks)
        
        # КРИТИЧНО: При 1 кирпиче - используем максимально точный расчет с учетом траектории
        if bricks_count == 1:
            brick_center_x = getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
            brick_y = getattr(target_brick, "y", 0)
            brick_height = getattr(target_brick, "height", 20)
            brick_width = getattr(target_brick, "width", 60)
            
            # Вычисляем, куда нужно направить мяч для попадания в кирпич
            ball_y = self.current_game_state.ball_position.y
            ball_x = self.current_game_state.ball_position.x
            paddle_y = self.current_game_state.paddle_position.y
            vel_x = self.current_game_state.ball_velocity.x if hasattr(self.current_game_state, "ball_velocity") else 0
            vel_y = self.current_game_state.ball_velocity.y if hasattr(self.current_game_state, "ball_velocity") else 0
            
            # Расстояние от платформы до кирпича
            distance_to_brick = brick_y - paddle_y
            
            # КРИТИЧНО: Используем более точный расчет с учетом угла отскока
            # Рассчитываем требуемый угол отскока для попадания в центр кирпича
            horizontal_distance_needed = brick_center_x - landing_x
            
            # Учитываем, что мяч должен попасть в кирпич после отскока
            # Используем формулу: угол = atan2(horizontal_distance, vertical_distance)
            # Но учитываем максимальный угол отскока от платформы
            paddle_half_width = self.paddle_width / 2
            max_angle = math.atan2(paddle_half_width, 50)  # Максимальный угол отскока
            
            # Рассчитываем требуемый угол для попадания в кирпич
            required_angle = math.atan2(horizontal_distance_needed, distance_to_brick)
            
            # Нормализуем угол до максимально возможного
            normalized_angle = max(-max_angle, min(max_angle, required_angle))
            
            # Преобразуем угол в offset (-1.0 до 1.0 соответствует -max_angle до +max_angle)
            offset = normalized_angle / max_angle if max_angle > 0 else 0
            
            # КРИТИЧНО: Учитываем текущую траекторию мяча для более точного предсказания
            if abs(vel_x) > 0.1 and abs(vel_y) > 0.1:
                # Если мяч движется в сторону кирпича, немного корректируем offset
                direction_to_brick = 1.0 if (brick_center_x - ball_x) > 0 else -1.0
                ball_direction = 1.0 if vel_x > 0 else -1.0
                
                # Если мяч движется в сторону кирпича, уменьшаем offset (мяч уже направлен правильно)
                # Если мяч движется от кирпича, увеличиваем offset (нужно больше коррекции)
                if direction_to_brick == ball_direction:
                    offset *= 0.9  # Небольшое уменьшение, т.к. мяч уже направлен правильно
                else:
                    offset *= 1.1  # Увеличение для компенсации неправильного направления
            
            # Ограничиваем диапазоном (используем максимальный offset 1.5 для экстремальных углов)
            max_offset = 1.5
            offset = max(-max_offset, min(max_offset, offset))
            
            self._logger.debug(
                f"[LAST BRICK OFFSET] brick_x={brick_center_x:.1f}, landing_x={landing_x:.1f}, "
                f"offset={offset:.2f}, required_angle={math.degrees(required_angle):.1f}°, "
                f"normalized_angle={math.degrees(normalized_angle):.1f}°"
            )
            
            return offset
        
        # Точные координаты кубика
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_width = getattr(target_brick, "width", 60)
        brick_height = getattr(target_brick, "height", 20)
        
        # Центр целевого кубика
        brick_center_x = brick_x + brick_width / 2
        brick_center_y = brick_y + brick_height / 2
        
        # Учитываем границы кубика для более точного прицеливания
        # Предпочитаем прицеливаться в центр, но учитываем возможность попадания в края
        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height

        paddle_y = self.current_game_state.paddle_position.y

        # Рассчитываем оптимальную точку попадания в кубик
        # Предпочитаем центр кубика, но учитываем текущую траекторию мяча
        ball_x = self.current_game_state.ball_position.x
        ball_vel_x = self.current_game_state.ball_velocity.x
        
        # Если мяч движется в сторону кубика, можно прицеливаться ближе к краю
        # для более эффективного попадания
        if abs(ball_vel_x) > 0:
            # Определяем, в какую сторону движется мяч относительно кубика
            if ball_vel_x > 0 and ball_x < brick_center_x:
                # Мяч движется вправо и находится слева от кубика
                # Прицеливаемся немного правее центра для компенсации движения
                target_x = brick_center_x + min(brick_width * 0.15, 10)
            elif ball_vel_x < 0 and ball_x > brick_center_x:
                # Мяч движется влево и находится справа от кубика
                # Прицеливаемся немного левее центра
                target_x = brick_center_x - min(brick_width * 0.15, 10)
            else:
                # Стандартное прицеливание в центр
                target_x = brick_center_x
        else:
            target_x = brick_center_x

        # Ограничиваем целевую точку границами кубика
        target_x = max(brick_left, min(brick_right, target_x))

        # Требуемый угол отскока с учетом точной целевой точки
        delta_x = target_x - landing_x
        delta_y = paddle_y - brick_center_y

        if delta_y <= 0:
            # Кубик ниже платформы — физически недостижимо
            return 0.0

        target_angle = math.atan2(delta_x, delta_y)

        # Нормируем угол к диапазону смещения [-1; 1]
        max_angle = math.pi / 4  # около 45 градусов
        offset = target_angle / max_angle

        # Ограничиваем диапазон
        offset = max(-1.0, min(1.0, offset))

        return offset
