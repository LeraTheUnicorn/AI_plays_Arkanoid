"""
Пример использования AsyncTrajectoryPredictor для асинхронных расчетов траектории
"""

import asyncio
from .async_trajectory_predictor import AsyncTrajectoryPredictor
from .game_state import GameState, Point


async def example_async_trajectory_prediction():
    """
    Пример использования асинхронного предсказания траектории
    """
    # Создаем асинхронный предиктор
    async_predictor = AsyncTrajectoryPredictor(screen_width=800, screen_height=600, max_workers=2)
    
    # Создаем тестовое состояние игры
    game_state = GameState(
        ball_position=Point(400, 100),
        ball_velocity=Point(5, 3),
        paddle_position=Point(400, 550),
        paddle_width=100,
        remaining_bricks=[],
        game_score=0,
        game_time=0,
        ball_speed=5
    )
    
    # Асинхронное предсказание траектории
    trajectory = await async_predictor.predict_trajectory_async(game_state, max_points=50)
    print(f"Предсказано точек траектории: {len(trajectory)}")
    
    # Асинхронное предсказание пересечения с платформой
    intersection = await async_predictor.predict_paddle_intersection_async(game_state, paddle_y=550.0)
    if intersection:
        print(f"Точка пересечения с платформой: ({intersection.x}, {intersection.y})")
    
    # Параллельное выполнение нескольких предсказаний
    tasks = [
        async_predictor.predict_trajectory_async(game_state, max_points=40),
        async_predictor.predict_trajectory_async(game_state, max_points=60),
        async_predictor.get_optimized_trajectory_async(game_state, max_relevant_points=30)
    ]
    
    results = await asyncio.gather(*tasks)
    print(f"Параллельно выполнено {len(results)} предсказаний")
    
    # Очистка ресурсов
    async_predictor.shutdown()


# Пример использования в синхронном коде
def example_sync_usage():
    """
    Пример использования AsyncTrajectoryPredictor в синхронном коде
    (через синхронные методы для обратной совместимости)
    """
    async_predictor = AsyncTrajectoryPredictor(screen_width=800, screen_height=600)
    
    game_state = GameState(
        ball_position=Point(400, 100),
        ball_velocity=Point(5, 3),
        paddle_position=Point(400, 550),
        paddle_width=100,
        remaining_bricks=[],
        game_score=0,
        game_time=0,
        ball_speed=5
    )
    
    # Использование синхронных методов (для обратной совместимости)
    trajectory = async_predictor.predict_trajectory_sync(game_state, max_points=50)
    print(f"Предсказано точек траектории (синхронно): {len(trajectory)}")
    
    intersection = async_predictor.predict_paddle_intersection_sync(game_state, paddle_y=550.0)
    if intersection:
        print(f"Точка пересечения (синхронно): ({intersection.x}, {intersection.y})")
    
    async_predictor.shutdown()


if __name__ == "__main__":
    # Запуск асинхронного примера
    asyncio.run(example_async_trajectory_prediction())
    
    # Запуск синхронного примера
    example_sync_usage()








