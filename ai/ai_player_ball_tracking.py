"""
Модуль отслеживания мяча AIPlayer.

Содержит методы для отслеживания позиции мяча, обработки отскоков
и расчета адаптивной скорости платформы.
"""

import random
import logging
from typing import Optional, Any, TYPE_CHECKING, Dict, Callable

if TYPE_CHECKING:
    from .game_state import GameState
    from .targeting import TargetSelector, PositionCalculator
    from .ai_player_models import TargetingSystem, SeparationZoneTracker
    from .config import AIConfig


class AIPlayerBallTrackingMixin:
    """Миксин для методов отслеживания мяча AIPlayer."""

    # Аннотации типов для статического анализатора
    current_game_state: Optional["GameState"]
    target_selector: "TargetSelector"
    loop_prevention_system: Dict[str, Any]
    targeting_system: "TargetingSystem"
    position_calculator: "PositionCalculator"
    smoothness_system: Dict[str, Any]
    separation_zone_tracker: "SeparationZoneTracker"
    empty_bounce_tracker: Dict[str, Any]
    screen_width: int
    paddle_width: int
    config: "AIConfig"
    _logger: logging.Logger
    _predict_exact_landing_position: Callable[[], float]
    _change_strategy_if_looping: Callable[[], None]
    _apply_alternative_strategy: Callable[[int], int]
    is_ball_moving_towards_paddle: Callable[[], bool]

    def _reevaluate_after_bounce(self) -> None:
        """Переоценивает ситуацию после отбития мяча."""
        if not self.current_game_state:
            return

        target_brick = self.target_selector.find_best_target_brick(
            self.current_game_state,
            self.current_game_state.paddle_position.y,
            self.current_game_state.ball_position.x,
        )
        if target_brick:
            self.targeting_system.target_brick = target_brick
            landing_x = self._predict_exact_landing_position()
            new_offset = self.position_calculator.calculate_optimal_offset(
                landing_x, target_brick, self.current_game_state
            )
            self.targeting_system.optimal_offset = new_offset

        # Сбрасываем историю зацикливания для нового цикла
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []

        # Сбрасываем историю плавности движения после отскока
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0

        # КРИТИЧНО: Сбрасываем отслеживание зоны разделения после отскока
        self.separation_zone_tracker.ball_entered_separation_zone = False
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        self.separation_zone_tracker.last_movement_frame = 0

        # КРИТИЧНО: Проверяем, было ли отбитие в пустоту (мяч отскочил от потолка без попадания в кубики)
        # Это определяется в PyGameBall.py при отскоке от потолка
        # Здесь мы сбрасываем счетчик только если было успешное попадание в кубик

    def _handle_ceiling_bounce_positioning(self) -> int:
        """
        Специальная логика для позиционирования при отскоке мяча от потолка.
        Предотвращает симметричные отскоки и зацикливание.
        """
        if not self.current_game_state:
            return self.screen_width // 2
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y

        if ball_y < 30 and vel_y > 0:
            # ✅ ИСПРАВЛЕНО: Проверяем зацикливание при отскоках от потолка
            ceiling_bounces = self.empty_bounce_tracker.get("ceiling_bounces", 0) or 0
            if ceiling_bounces >= 2:
                # Обнаружено зацикливание - используем альтернативную стратегию
                if hasattr(self, "_logger"):
                    self._logger.warning(
                        f"[CEILING BOUNCE] Обнаружено зацикливание при отскоках от потолка "
                        f"(ceiling_bounces={ceiling_bounces}), используем альтернативную стратегию"
                    )
                # Принудительно меняем стратегию
                self._change_strategy_if_looping()
                # Используем альтернативную стратегию для выхода из зацикливания
                optimal_x = int(self._track_ball_position())
                optimal_x = self._apply_alternative_strategy(optimal_x)
                return optimal_x

            # Мяч только что отскочил от потолка
            if abs(vel_x) < 2:
                # Почти вертикальный отскок — смещаемся в сторону средней позиции кубиков
                remaining_bricks = self.targeting_system.brick_coordinates
                if remaining_bricks:
                    avg_brick_x = sum(c["x"] for c in remaining_bricks) / len(
                        remaining_bricks
                    )
                    target_x = (ball_x + avg_brick_x) / 2.0
                else:
                    # Нет кубиков — небольшое смещение от центра
                    center_x = self.screen_width // 2
                    target_x = center_x + (ball_x - center_x) * 0.3
            else:
                # Есть горизонтальная скорость — небольшое упреждение
                target_x = ball_x + vel_x * 2.0

            # Добавляем случайное смещение, чтобы избежать идеальной симметрии
            target_x += random.choice([-15, -10, 0, 10, 15])

            paddle_half_width = self.paddle_width / 2
            min_x = paddle_half_width + 5
            max_x = self.screen_width - paddle_half_width - 5
            target_x = max(min_x, min(max_x, target_x))
            return int(target_x)

        # Стандартное слежение за мячом
        return int(self._track_ball_position())

    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с небольшим упреждением."""
        if not self.current_game_state:
            return self.screen_width / 2.0
        game_state = self.current_game_state
        ball_x = game_state.ball_position.x
        vel_x = game_state.ball_velocity.x

        prediction_time = 3  # кадров вперёд
        predicted_x = ball_x + vel_x * prediction_time

        screen_width = self.screen_width
        ball_radius = self.config.ball.radius
        min_x = ball_radius
        max_x = screen_width - ball_radius

        return max(min_x, min(max_x, predicted_x))

    def calculate_adaptive_paddle_speed(
        self, current_x: int, optimal_x: int, ball_speed: int
    ) -> int:
        """
        Рассчитывает адаптивную скорость платформы на основе физики игры.

        Учитывает:
        - Скорость мяча
        - Расстояние до оптимальной позиции
        - Время до встречи с мячом
        - Историю успешных движений

        Args:
            current_x: Текущая позиция платформы
            optimal_x: Оптимальная позиция платформы
            ball_speed: Скорость мяча

        Returns:
            Адаптивная скорость платформы
        """
        import random

        # КРИТИЧНО: Адаптивная базовая скорость на основе скорости мяча
        # Адаптивная скорость с разумными пределами: min=35, max=60, base=ball_speed * 2.5
        base_paddle_speed = max(35, min(int(ball_speed * 2.5), 60))
        min_speed = 35  # Минимальная скорость
        max_speed = 60  # Максимальная скорость

        if not self.current_game_state:
            return base_paddle_speed

        distance_to_optimal = abs(optimal_x - current_x)

        # Если позиция уже оптимальна или близка к ней
        if distance_to_optimal <= 5:
            return min_speed

        # Рассчитываем время до встречи с мячом (если он движется к платформе)
        time_to_meeting: float = 0.0
        if self.is_ball_moving_towards_paddle() and self.current_game_state:
            game_state = self.current_game_state
            ball_y = game_state.ball_position.y
            paddle_y = game_state.paddle_position.y
            ball_vel_y = game_state.ball_velocity.y

            if ball_vel_y > 0:  # Мяч движется вниз
                # Более точный расчет времени с учетом текущей позиции мяча
                distance_y = paddle_y - ball_y
                if distance_y > 0:
                    time_to_meeting = distance_y / ball_vel_y
                    time_to_meeting = max(
                        0.0, time_to_meeting
                    )  # Не может быть отрицательным

        # Рассчитываем требуемую скорость на основе времени до встречи
        required_speed: float = float(base_paddle_speed)

        if time_to_meeting > 0 and time_to_meeting != float("inf"):
            # Если времени мало, нужна высокая скорость
            if time_to_meeting <= 20:  # Менее 20 кадров - критическая ситуация
                required_speed = max(
                    float(base_paddle_speed * 2.5),  # Увеличено с 1.5 до 2.5
                    float(distance_to_optimal)
                    / max(time_to_meeting * 0.5, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 40:  # Менее 40 кадров
                required_speed = max(
                    float(base_paddle_speed * 2.0),  # Увеличено с 1.2 до 2.0
                    float(distance_to_optimal)
                    / max(time_to_meeting * 0.6, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 80:  # Менее 80 кадров
                required_speed = max(
                    float(base_paddle_speed * 1.5),  # Увеличено с 0.9 до 1.5
                    float(distance_to_optimal) / max(time_to_meeting * 0.8, 1),
                )
            else:  # Много времени - можно двигаться медленно
                required_speed = max(
                    float(min_speed), float(base_paddle_speed * 1.0)
                )  # Увеличено с 0.6 до 1.0
        else:
            # Мяч не движется к платформе, используем умеренную скорость
            required_speed = float(base_paddle_speed * 0.8)

        # Корректируем на основе скорости мяча
        speed_ratio = float(ball_speed) / 5.0  # 5 - BALL_SPEED_DEFAULT
        speed_multiplier = (
            0.7 + speed_ratio * 0.6
        )  # 0.7x до 1.3x в зависимости от скорости мяча
        required_speed *= speed_multiplier

        # Учитываем расстояние - чем дальше, тем быстрее
        if distance_to_optimal > 150:
            required_speed *= 1.4
        elif distance_to_optimal > 100:
            required_speed *= 1.2
        elif distance_to_optimal > 50:
            required_speed *= 1.1

        # Дополнительная корректировка для экстренных ситуаций
        if (
            distance_to_optimal > time_to_meeting * ball_speed * 0.8
            and time_to_meeting > 0
        ):
            # Если расстояние больше, чем может пролететь мяч за время до встречи
            required_speed *= 1.3

        # Применяем границы
        required_speed = max(min_speed, min(max_speed, required_speed))

        # Добавляем небольшую случайность для естественности
        if distance_to_optimal > 20:
            variation = random.uniform(0.97, 1.03)
            required_speed *= variation

        return int(required_speed)
