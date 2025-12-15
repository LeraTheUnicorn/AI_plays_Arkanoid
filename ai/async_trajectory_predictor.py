"""
Модуль для асинхронного предсказания траектории мяча
"""

import asyncio
import concurrent.futures
from typing import List, Optional, Any
from .trajectory_predictor import TrajectoryPredictor
from .game_state import GameState, Point


class AsyncTrajectoryPredictor:
    """
    Асинхронная обертка над TrajectoryPredictor для выполнения расчетов
    в отдельных потоках без блокировки основного потока игры.
    """
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600, max_workers: int = 2):
        """
        Инициализация асинхронного предиктора траектории.
        
        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
            max_workers: Максимальное количество потоков для выполнения расчетов
        """
        self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Получает или создает event loop для асинхронных операций"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    
    async def predict_trajectory_async(
        self, game_state: GameState, max_points: int = 120
    ) -> List[Point]:
        """
        Асинхронное предсказание траектории мяча.
        
        Args:
            game_state: Текущее состояние игры
            max_points: Максимальное количество точек в траектории
            
        Returns:
            Список точек траектории
        """
        loop = self._get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.trajectory_predictor.predict_trajectory,
            game_state,
            max_points
        )
    
    async def predict_paddle_intersection_async(
        self, game_state: GameState, paddle_y: float
    ) -> Optional[Point]:
        """
        Асинхронное предсказание точки пересечения мяча с платформой.
        
        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы
            
        Returns:
            Точка пересечения или None если пересечения не будет
        """
        loop = self._get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.trajectory_predictor.predict_paddle_intersection,
            game_state,
            paddle_y
        )
    
    async def predict_after_bounce_trajectory_async(
        self, game_state: GameState, bounce_point: Point, bounce_x: float
    ) -> List[Point]:
        """
        Асинхронное предсказание траектории мяча после отскока от платформы.
        
        Args:
            game_state: Текущее состояние игры
            bounce_point: Точка отскока
            bounce_x: X-координата точки отскока на платформе
            
        Returns:
            Траектория после отскока
        """
        loop = self._get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.trajectory_predictor.predict_after_bounce_trajectory,
            game_state,
            bounce_point,
            bounce_x
        )
    
    async def get_optimized_trajectory_async(
        self, game_state: GameState, max_relevant_points: int = 40
    ) -> List[Point]:
        """
        Асинхронное получение оптимизированной траектории.
        
        Args:
            game_state: Текущее состояние игры
            max_relevant_points: Максимальное количество релевантных точек для возврата
            
        Returns:
            Список точек траектории (оптимизированный)
        """
        loop = self._get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.trajectory_predictor.get_optimized_trajectory,
            game_state,
            max_relevant_points
        )
    
    async def get_adaptive_trajectory_async(
        self, game_state: GameState, ball_y: float, paddle_y: float
    ) -> List[Point]:
        """
        Асинхронное получение адаптивной траектории.
        
        Args:
            game_state: Текущее состояние игры
            ball_y: Y-координата мяча
            paddle_y: Y-координата платформы
            
        Returns:
            Список точек траектории (адаптивный размер)
        """
        loop = self._get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.trajectory_predictor.get_adaptive_trajectory,
            game_state,
            ball_y,
            paddle_y
        )
    
    def predict_trajectory_sync(
        self, game_state: GameState, max_points: int = 120
    ) -> List[Point]:
        """
        Синхронное предсказание траектории (для обратной совместимости).
        
        Args:
            game_state: Текущее состояние игры
            max_points: Максимальное количество точек в траектории
            
        Returns:
            Список точек траектории
        """
        return self.trajectory_predictor.predict_trajectory(game_state, max_points)
    
    def predict_paddle_intersection_sync(
        self, game_state: GameState, paddle_y: float
    ) -> Optional[Point]:
        """
        Синхронное предсказание точки пересечения (для обратной совместимости).
        
        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы
            
        Returns:
            Точка пересечения или None если пересечения не будет
        """
        return self.trajectory_predictor.predict_paddle_intersection(game_state, paddle_y)
    
    def predict_after_bounce_trajectory_sync(
        self, game_state: GameState, bounce_point: Point, bounce_x: float
    ) -> List[Point]:
        """
        Синхронное предсказание траектории после отскока (для обратной совместимости).
        
        Args:
            game_state: Текущее состояние игры
            bounce_point: Точка отскока
            bounce_x: X-координата точки отскока на платформе
            
        Returns:
            Траектория после отскока
        """
        return self.trajectory_predictor.predict_after_bounce_trajectory(
            game_state, bounce_point, bounce_x
        )
    
    def get_optimized_trajectory_sync(
        self, game_state: GameState, max_relevant_points: int = 40
    ) -> List[Point]:
        """
        Синхронное получение оптимизированной траектории (для обратной совместимости).
        
        Args:
            game_state: Текущее состояние игры
            max_relevant_points: Максимальное количество релевантных точек для возврата
            
        Returns:
            Список точек траектории (оптимизированный)
        """
        return self.trajectory_predictor.get_optimized_trajectory(
            game_state, max_relevant_points
        )
    
    def get_adaptive_trajectory_sync(
        self, game_state: GameState, ball_y: float, paddle_y: float
    ) -> List[Point]:
        """
        Синхронное получение адаптивной траектории (для обратной совместимости).
        
        Args:
            game_state: Текущее состояние игры
            ball_y: Y-координата мяча
            paddle_y: Y-координата платформы
            
        Returns:
            Список точек траектории (адаптивный размер)
        """
        return self.trajectory_predictor.get_adaptive_trajectory(
            game_state, ball_y, paddle_y
        )
    
    def clear_cache(self) -> None:
        """Очищает кэш предиктора траектории"""
        self.trajectory_predictor.clear_cache()
    
    def shutdown(self) -> None:
        """Закрывает executor и освобождает ресурсы"""
        self.executor.shutdown(wait=True)
    
    def __getattr__(self, name: str) -> Any:
        """
        Проксирует доступ к методам TrajectoryPredictor для обратной совместимости.
        Если метод не найден в AsyncTrajectoryPredictor, ищет его в TrajectoryPredictor.
        """
        return getattr(self.trajectory_predictor, name)




