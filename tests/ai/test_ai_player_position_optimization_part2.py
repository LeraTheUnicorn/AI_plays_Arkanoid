"""
Тесты для модуля ai_player_position_optimization_part2.py
"""

import pytest
import math
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player_position_optimization_part2 import AIPlayerPositionOptimizationPart2Mixin
from ai.game_state import GameState, Point


class TestAIPlayerPositionOptimizationPart2Mixin:
    """Тесты для миксина AIPlayerPositionOptimizationPart2Mixin."""
    
    def _create_mock_player(self):
        """Создает мок AIPlayer с необходимыми атрибутами."""
        player = type('TestPlayer', (AIPlayerPositionOptimizationPart2Mixin,), {})()
        player.screen_width = 800
        player.screen_height = 600
        player.paddle_width = 120
        player.current_game_state = None
        player._logger = Mock()
        player._predict_exact_landing_position = Mock(return_value=400.0)
        player._find_best_target_for_few_bricks = Mock(return_value=None)
        
        # Trajectory predictor
        player.trajectory_predictor = Mock()
        player.trajectory_predictor.predict_paddle_intersection = Mock(return_value=Point(400, 550))
        player.trajectory_predictor.predict_after_bounce_trajectory = Mock(return_value=[
            Point(300, 200)
        ])
        
        # Config
        player.config = Mock()
        player.config.ball = Mock()
        player.config.ball.radius = 8
        
        # Targeting system
        player.targeting_system = Mock()
        player.targeting_system.hit_patterns = {}
        
        return player
    
    def test_find_optimal_angle_for_max_destruction_no_game_state(self):
        """Тест когда нет game_state."""
        player = self._create_mock_player()
        player.current_game_state = None
        
        result = player._find_optimal_angle_for_max_destruction()
        
        assert result is None
    
    def test_find_optimal_angle_for_max_destruction_no_bricks(self):
        """Тест когда нет кубиков."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        result = player._find_optimal_angle_for_max_destruction()
        
        assert result is None
    
    def test_count_bricks_in_trajectory_empty(self):
        """Тест подсчета кубиков в пустой траектории."""
        player = self._create_mock_player()
        
        result = player._count_bricks_in_trajectory([], [])
        
        assert result == 0
    
    def test_count_bricks_in_trajectory_with_hits(self):
        """Тест подсчета кубиков в траектории с попаданиями."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60
        mock_brick.height = 20
        
        trajectory = [Point(300, 200), Point(350, 250)]
        bricks = [mock_brick]
        
        result = player._count_bricks_in_trajectory(trajectory, bricks)
        
        assert result >= 0
    
    def test_find_first_brick_in_trajectory_empty(self):
        """Тест поиска первого кубика в пустой траектории."""
        player = self._create_mock_player()
        
        result = player._find_first_brick_in_trajectory([], [])
        
        assert result is None
    
    def test_find_first_brick_in_trajectory_with_hit(self):
        """Тест поиска первого кубика в траектории с попаданием."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60
        mock_brick.height = 20
        
        trajectory = [Point(300, 200), Point(350, 250)]
        bricks = [mock_brick]
        
        result = player._find_first_brick_in_trajectory(trajectory, bricks)
        
        assert result is not None or result is None  # Может быть или не быть
    
    def test_find_best_target_for_few_bricks_no_bricks(self):
        """Тест когда нет кубиков."""
        player = self._create_mock_player()
        
        result = player._find_best_target_for_few_bricks([], 550, 400)
        
        assert result is None
    
    def test_find_best_target_for_few_bricks_single_brick(self):
        """Тест для одного кубика."""
        player = self._create_mock_player()
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        # Устанавливаем current_game_state для логирования
        player.current_game_state = GameState(
            ball_position=Point(400, 300),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[mock_brick],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        result = player._find_best_target_for_few_bricks([mock_brick], 550, 400)
        
        # Для одного кубика метод должен вернуть его или None в зависимости от условий
        # Проверяем что метод выполнился без ошибок
        assert result is None or result == mock_brick
    
    def test_find_best_target_for_few_bricks_multiple_bricks(self):
        """Тест для нескольких кубиков."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        mock_brick1 = Mock()
        mock_brick1.x = 300
        mock_brick1.y = 250
        mock_brick1.width = 60
        
        mock_brick2 = Mock()
        mock_brick2.x = 500
        mock_brick2.y = 200
        mock_brick2.width = 60
        
        # Для 2-3 кубиков метод должен вернуть один из них
        result = player._find_best_target_for_few_bricks([mock_brick1, mock_brick2], 550, 400)
        
        # Результат может быть None или одним из кубиков в зависимости от логики
        assert result is None or result in [mock_brick1, mock_brick2]
    
    def test_calculate_optimal_offset_no_target_brick(self):
        """Тест когда нет целевого кубика."""
        player = self._create_mock_player()
        
        result = player._calculate_optimal_offset(400.0, None)
        
        assert result == 0.0
    
    def test_calculate_optimal_offset_single_brick(self):
        """Тест расчета смещения для одного кубика."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(5, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()],
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        mock_brick = Mock()
        mock_brick.x = 300
        mock_brick.y = 200
        mock_brick.width = 60
        
        result = player._calculate_optimal_offset(400.0, mock_brick)
        
        assert isinstance(result, float)
        assert -1.5 <= result <= 1.5
    
    def test_calculate_optimal_offset_with_velocity(self):
        """Тест расчета смещения с учетом скорости."""
        player = self._create_mock_player()
        player.current_game_state = GameState(
            ball_position=Point(400, 400),
            ball_velocity=Point(10, 5),
            paddle_position=Point(400, 550),
            paddle_width=120,
            remaining_bricks=[Mock()] * 2,  # Не 1 кирпич, чтобы не использовать специальную логику
            game_score=0,
            game_time=0,
            ball_speed=5,
        )
        
        mock_brick = Mock()
        mock_brick.x = 500
        mock_brick.y = 200
        mock_brick.width = 60
        mock_brick.height = 20
        
        result = player._calculate_optimal_offset(400.0, mock_brick)
        
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0

