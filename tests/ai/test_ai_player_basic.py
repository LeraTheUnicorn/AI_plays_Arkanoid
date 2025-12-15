"""
Базовые тесты для модуля ai_player.py
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from ai.ai_player import AIPlayer
from ai.game_state import GameState, Point
from ai.trajectory_predictor import TrajectoryPredictor
from ai.position_optimizer import PositionOptimizer


class TestAIPlayerInit:
    """Тесты инициализации AIPlayer."""
    
    def test_init_basic(self):
        """Тест базовой инициализации."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600, debug_mode=False)
            
            assert ai_player.screen_width == 800
            assert ai_player.screen_height == 600
            assert ai_player.debug_mode is False
            assert ai_player.config is not None
    
    def test_init_with_dependencies(self):
        """Тест инициализации с инъекцией зависимостей."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            mock_predictor = Mock(spec=TrajectoryPredictor)
            mock_optimizer = Mock(spec=PositionOptimizer)
            
            ai_player = AIPlayer(
                800, 600,
                trajectory_predictor=mock_predictor,
                position_optimizer=mock_optimizer
            )
            
            assert ai_player.trajectory_predictor == mock_predictor
            assert ai_player.position_optimizer == mock_optimizer
    
    def test_init_async_trajectory(self):
        """Тест инициализации с асинхронным предиктором."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600, use_async_trajectory=True, async_max_workers=3)
            
            assert ai_player.trajectory_predictor is not None
            # Проверяем, что используется AsyncTrajectoryPredictor
            from ai.async_trajectory_predictor import AsyncTrajectoryPredictor
            assert isinstance(ai_player.trajectory_predictor, AsyncTrajectoryPredictor)
    
    def test_init_sync_trajectory(self):
        """Тест инициализации с синхронным предиктором."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600, use_async_trajectory=False)
            
            assert ai_player.trajectory_predictor is not None
            assert isinstance(ai_player.trajectory_predictor, TrajectoryPredictor)
    
    def test_init_validation(self):
        """Тест валидации параметров при инициализации."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            # Некорректные размеры должны вызывать исключение
            with pytest.raises((TypeError, ValueError)):
                AIPlayer("800", 600)
            
            with pytest.raises((TypeError, ValueError)):
                AIPlayer(800, "600")
            
            with pytest.raises(ValueError):
                AIPlayer(0, 600)
            
            with pytest.raises(ValueError):
                AIPlayer(800, -100)


class TestAIPlayerActivation:
    """Тесты активации/деактивации AIPlayer."""
    
    def test_activate(self):
        """Тест активации AIPlayer."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600)
            ai_player.activate()
            
            assert ai_player.is_active is True
    
    def test_deactivate(self):
        """Тест деактивации AIPlayer."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600)
            ai_player.activate()
            ai_player.deactivate()
            
            assert ai_player.is_active is False


class TestAIPlayerState:
    """Тесты работы с состоянием игры."""
    
    def test_update_game_state(self):
        """Тест обновления состояния игры."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600)
            
            # Создаем моки для объектов игры
            mock_ball = Mock()
            mock_ball.rect = Mock()
            mock_ball.rect.centerx = 400
            mock_ball.rect.centery = 300
            mock_ball.vel_x = 5
            mock_ball.vel_y = -5
            mock_ball.get_speed = Mock(return_value=5)
            
            mock_paddle = Mock()
            mock_paddle.rect = Mock()
            mock_paddle.rect.centerx = 400
            mock_paddle.rect.centery = 550
            mock_paddle.rect.width = 120
            
            mock_bricks = []
            start_time = 0
            
            # update_game_state принимает объекты игры, а не GameState
            ai_player.update_game_state(mock_ball, mock_paddle, mock_bricks, 0, start_time)
            
            # Проверяем, что состояние было обновлено
            assert ai_player.current_game_state is not None
    
    def test_get_current_state(self):
        """Тест получения текущего состояния."""
        with patch('ai.ai_player_init.AIPlayerInitMixin._setup_logging') as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger
            
            ai_player = AIPlayer(800, 600)
            
            # Создаем моки для объектов игры
            mock_ball = Mock()
            mock_ball.rect = Mock()
            mock_ball.rect.centerx = 400
            mock_ball.rect.centery = 300
            mock_ball.vel_x = 5
            mock_ball.vel_y = -5
            mock_ball.get_speed = Mock(return_value=5)
            
            mock_paddle = Mock()
            mock_paddle.rect = Mock()
            mock_paddle.rect.centerx = 400
            mock_paddle.rect.centery = 550
            mock_paddle.rect.width = 120
            
            mock_bricks = []
            start_time = 0
            
            ai_player.update_game_state(mock_ball, mock_paddle, mock_bricks, 0, start_time)
            
            # Проверяем прямой доступ к current_game_state
            current_state = ai_player.current_game_state
            assert current_state is not None
            assert isinstance(current_state, GameState)

