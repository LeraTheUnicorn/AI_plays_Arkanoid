# Руководство по запуску игры в многопоточном режиме

## Обзор

Многопоточный режим использует `AsyncTrajectoryPredictor` для выполнения расчетов траектории в отдельных потоках, что позволяет не блокировать основной игровой цикл.

## Быстрый старт

### Вариант 1: Включить для всех созданий AIPlayer

Найдите все места, где создается `AIPlayer`, и добавьте параметры:

```python
ai_player = AIPlayer(
    SCREEN_WIDTH, 
    SCREEN_HEIGHT, 
    debug_mode=True,
    use_async_trajectory=True,      # Включить асинхронные расчеты
    async_max_workers=2              # Количество потоков (рекомендуется 2-4)
)
```

### Вариант 2: Использовать переменную окружения

Добавьте в начало файла `PyGameBall.py`:

```python
import os

# Настройка многопоточного режима через переменные окружения
USE_ASYNC_TRAJECTORY = os.getenv("AI_USE_ASYNC_TRAJECTORY", "false").lower() == "true"
ASYNC_MAX_WORKERS = int(os.getenv("AI_ASYNC_MAX_WORKERS", "2"))
```

Затем используйте при создании:

```python
ai_player = AIPlayer(
    SCREEN_WIDTH, 
    SCREEN_HEIGHT, 
    debug_mode=True,
    use_async_trajectory=USE_ASYNC_TRAJECTORY,
    async_max_workers=ASYNC_MAX_WORKERS
)
```

Запуск с переменными окружения:
```bash
# Windows PowerShell
$env:AI_USE_ASYNC_TRAJECTORY="true"; $env:AI_ASYNC_MAX_WORKERS="4"; python game/PyGameBall.py

# Windows CMD
set AI_USE_ASYNC_TRAJECTORY=true && set AI_ASYNC_MAX_WORKERS=4 && python game/PyGameBall.py

# Linux/Mac
AI_USE_ASYNC_TRAJECTORY=true AI_ASYNC_MAX_WORKERS=4 python game/PyGameBall.py
```

## Где изменить код

### Основные места создания AIPlayer в PyGameBall.py:

1. **Строка ~1049** - Создание при запуске в режиме обучения:
```python
ai_player = AIPlayer(
    SCREEN_WIDTH, 
    SCREEN_HEIGHT, 
    debug_mode=True,
    use_async_trajectory=True,      # Добавить
    async_max_workers=2            # Добавить
)
```

2. **Строка ~1237** - Создание при перезапуске игры:
```python
ai_player = AIPlayer(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    debug_mode=True,
    use_async_trajectory=True,      # Добавить
    async_max_workers=2              # Добавить
)
```

3. **Строка ~1274** - Создание при активации AI:
```python
ai_player = AIPlayer(
    SCREEN_WIDTH, 
    SCREEN_HEIGHT, 
    debug_mode=True,
    use_async_trajectory=True,      # Добавить
    async_max_workers=2              # Добавить
)
```

4. **Строка ~2332, ~2636, ~2781** - Другие места создания

## Как это работает

### Синхронный режим (по умолчанию)
- Расчеты выполняются в основном потоке
- Блокирует игровой цикл во время расчетов
- Проще в использовании, но может вызывать задержки

### Асинхронный режим (многопоточный)
- Расчеты выполняются в отдельных потоках через `ThreadPoolExecutor`
- Не блокирует основной игровой цикл
- Использует синхронные методы-обертки для обратной совместимости
- Автоматически управляет event loop

## Рекомендации

### Количество потоков (async_max_workers)

- **1 поток**: Минимальная нагрузка, но без параллелизма
- **2 потока** (рекомендуется): Оптимальный баланс для большинства случаев
- **3-4 потока**: Для мощных систем, если нужно выполнять много расчетов параллельно
- **>4 потока**: Обычно избыточно, может снизить производительность из-за накладных расходов

### Когда использовать

✅ **Используйте асинхронный режим, если:**
- Замечаете задержки в игре при расчетах траектории
- Играете на многоядерном процессоре
- Нужна максимальная производительность

❌ **Не используйте, если:**
- Игра работает плавно без задержек
- На слабом одноядерном процессоре
- Возникают проблемы с синхронизацией

## Проверка работы

После включения многопоточного режима проверьте:

1. **Логи**: В логах должно быть видно использование `AsyncTrajectoryPredictor`
2. **Производительность**: Игра должна работать плавнее, без задержек
3. **CPU**: В диспетчере задач должно быть видно использование нескольких ядер

## Отладка

Если возникают проблемы:

1. **Проверьте логи**: Ищите ошибки, связанные с `AsyncTrajectoryPredictor`
2. **Уменьшите количество потоков**: Попробуйте `async_max_workers=1`
3. **Отключите асинхронный режим**: Вернитесь к синхронному режиму для сравнения
4. **Проверьте совместимость**: Убедитесь, что все методы вызываются корректно

## Пример полной интеграции

```python
# В начале PyGameBall.py
import os

# Настройки многопоточности
USE_ASYNC_TRAJECTORY = os.getenv("AI_USE_ASYNC_TRAJECTORY", "false").lower() == "true"
ASYNC_MAX_WORKERS = int(os.getenv("AI_ASYNC_MAX_WORKERS", "2"))

# Функция-помощник для создания AIPlayer
def create_ai_player(screen_width: int, screen_height: int, debug_mode: bool = True):
    """Создает AIPlayer с настройками многопоточности"""
    return AIPlayer(
        screen_width,
        screen_height,
        debug_mode=debug_mode,
        use_async_trajectory=USE_ASYNC_TRAJECTORY,
        async_max_workers=ASYNC_MAX_WORKERS
    )

# Использование
ai_player = create_ai_player(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
```

## Дополнительная информация

- `AsyncTrajectoryPredictor` автоматически использует синхронные методы для обратной совместимости
- Все существующие вызовы работают без изменений
- Кэширование работает так же, как в синхронном режиме
- При завершении игры executor автоматически закрывается

