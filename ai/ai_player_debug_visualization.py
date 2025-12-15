"""
Модуль для визуализации отладочной информации в AIPlayer.

Содержит методы для отображения отладочной информации и предсказанной траектории.
"""

from typing import Any

try:
    import pygame
except ImportError:
    pygame = None


class AIPlayerDebugVisualizationMixin:
    """
    Миксин для методов визуализации отладочной информации.
    Добавляет методы для отображения отладочной информации на экране.
    """

    def visualize_debug_info(self, screen: Any) -> None:
        """
        Отображает отладочную информацию AI системы на экране.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            # Информация о состоянии AI
            info_lines = [
                f"Accuracy: {self.performance_metrics['average_accuracy']:.2f}",
                f"Learning: {self.performance_metrics['learning_progress']:.2f} (прогресс обучения)",
                f"Games: {self.performance_metrics['games_played']}",
            ]
            
            # Добавляем лучшее время для матча с 50 блоками
            best_time = self.performance_metrics.get("best_time_50_bricks")
            if best_time is not None and best_time > 0:
                # Форматируем время: если больше 60 секунд, показываем минуты и секунды
                if best_time >= 60:
                    minutes = int(best_time // 60)
                    seconds = best_time % 60
                    info_lines.append(f"Best: {minutes}m {seconds:.1f}s (50 blocks)")
                else:
                    info_lines.append(f"Best: {best_time:.1f}s (50 blocks)")
            else:
                info_lines.append(f"Best: -- (50 blocks)")
            
            # Отрисовка фона для текста
            font = pygame.font.SysFont("arial", 16)
            line_height = 20
            box_width = 200
            box_height = len(info_lines) * line_height + 10
            
            # Полупрозрачный фон
            debug_surface = pygame.Surface((box_width, box_height))
            debug_surface.set_alpha(128)
            debug_surface.fill((0, 0, 0))
            screen.blit(debug_surface, (10, 10))
            
            # Текст
            y_offset = 15
            for line in info_lines:
                text_surface = font.render(line, True, (255, 255, 0))
                screen.blit(text_surface, (15, y_offset))
                y_offset += line_height
                
            # Визуализация предсказанной траектории
            if (
                self.is_active
                and self.current_game_state
                and self.is_ball_moving_towards_paddle()
                and self.debug_mode
            ):
                self._draw_predicted_trajectory(screen)
                
        except (AttributeError, TypeError) as e:
            # Игнорируем ошибки типов при визуализации, чтобы не прерывать игру
            self._logger.debug(f"Ошибка типов при визуализации: {e}", exc_info=True)
        except (ImportError, NameError) as e:
            # Игнорируем ошибки импорта pygame при визуализации
            self._logger.debug(f"Ошибка импорта при визуализации: {e}", exc_info=True)

    def _draw_predicted_trajectory(self, screen: Any) -> None:
        """
        Рисует предсказанную траекторию мяча для отладки.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            if not self.current_game_state:
                return
                
            # Предсказываем траекторию (используем оптимизированную для визуализации)
            trajectory = self.trajectory_predictor.get_optimized_trajectory(
                self.current_game_state, max_relevant_points=50
            )
            
            if not trajectory:
                return
                
            # Рисуем точки траектории
            for i, point in enumerate(
                trajectory[::3]
            ):  # Каждая 3-я точка для оптимизации
                if hasattr(point, "x") and hasattr(point, "y"):
                    # Цвет зависит от типа точки
                    if i < len(trajectory) // 3:
                        color = (0, 255, 0)  # Зеленый - начало траектории
                    else:
                        color = (255, 255, 0)  # Желтый - конец траектории
                    
                    pygame.draw.circle(screen, color, (int(point.x), int(point.y)), 2)
            
            # Рисуем точку пересечения с платформой
            intersection = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state,
                self.current_game_state.paddle_position.y,
            )
            
            if (
                intersection
                and hasattr(intersection, "x")
                and hasattr(intersection, "y")
            ):
                pygame.draw.circle(
                    screen, (255, 0, 0), (int(intersection.x), int(intersection.y)), 5
                )
                
        except (AttributeError, TypeError) as e:
            # Игнорируем ошибки типов при визуализации
            self._logger.debug(f"Ошибка типов при отрисовке траектории: {e}", exc_info=True)
        except (ImportError, NameError) as e:
            # Игнорируем ошибки импорта pygame
            self._logger.debug(f"Ошибка импорта при отрисовке траектории: {e}", exc_info=True)
        except Exception as e:
            # Игнорируем ошибки предсказания при отрисовке
            if hasattr(self, '_logger'):
                self._logger.debug(f"Ошибка предсказания при отрисовке: {e}", exc_info=True)
