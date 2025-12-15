![5000.png](../resources/5000.png)

## Схема проекта

```
├── 📁 ai/                          # AI-система для авторежима
│   ├── ai_player.py                # Основной класс AIPlayer (координатор, 479 строк)
│   ├── ai_player_init.py           # Миксин: инициализация
│   ├── ai_player_state.py          # Миксин: управление состоянием
│   ├── ai_player_targeting.py      # Миксин: прицеливание
│   ├── ai_player_target_selection_part1.py # Миксин: выбор целей (часть 1)
│   ├── ai_player_target_selection_part2.py # Миксин: выбор целей (часть 2)
│   ├── ai_player_target_calculation.py # Миксин: расчет целей
│   ├── ai_player_positioning.py    # Миксин: позиционирование
│   ├── ai_player_position_optimization_part1.py # Миксин: оптимизация позиции (часть 1)
│   ├── ai_player_position_optimization_part2.py # Миксин: оптимизация позиции (часть 2)
│   ├── ai_player_movement.py       # Миксин: движение платформы
│   ├── ai_player_movement_core_part1.py # Миксин: ядро движения (часть 1)
│   ├── ai_player_movement_core_part2.py # Миксин: ядро движения (часть 2)
│   ├── ai_player_movement_core_part3.py # Миксин: ядро движения (часть 3)
│   ├── ai_player_movement_helpers.py # Миксин: вспомогательные функции движения
│   ├── ai_player_learning.py       # Миксин: обучение (координатор)
│   ├── ai_player_learning_core_part1.py # Миксин: ядро обучения (часть 1)
│   ├── ai_player_learning_core_part2.py # Миксин: ядро обучения (часть 2)
│   ├── ai_player_match_processing.py # Миксин: обработка матчей
│   ├── ai_player_metrics.py        # Миксин: метрики производительности
│   ├── ai_player_reset.py          # Миксин: сброс состояния
│   ├── ai_player_zones.py          # Миксин: работа с зонами
│   ├── ai_player_loop_prevention.py # Миксин: предотвращение зацикливания
│   ├── ai_player_ball_tracking.py # Миксин: отслеживание мяча
│   ├── ai_player_fallback.py      # Миксин: резервные стратегии
│   ├── ai_player_cache.py          # Миксин: кэширование
│   ├── ai_player_utils.py          # Миксин: утилиты
│   ├── ai_player_models.py         # Модели данных AIPlayer
│   ├── ai_player_debug_visualization.py # Миксин: визуализация отладки
│   ├── trajectory_predictor.py     # Предсказание траектории мяча
│   ├── async_trajectory_predictor.py # Асинхронное предсказание траекторий
│   ├── position_optimizer.py       # Оптимизация позиции платформы
│   ├── learning_system.py          # Система машинного обучения
│   ├── lazy_learning_system.py     # Ленивая система обучения
│   ├── performance_logger.py       # Логирование производительности
│   ├── performance_monitor.py      # Мониторинг производительности
│   ├── game_state.py               # Модель состояния игры
│   ├── config.py                    # Конфигурация AI
│   ├── exceptions.py               # Исключения AI системы
│   ├── logging_config.py           # Настройка логирования
│   ├── debug_logger.py             # Отладочное логирование
│   ├── platform_utils.py           # Утилиты для платформ
│   ├── buffered_logger.py          # Буферизованное логирование
│   ├── rotating_file_handler.py    # Ротирующий file handler
│   ├── analyze_ball_loss.py        # Анализ потери мяча
│   └── async_trajectory_example.py # Пример асинхронного предсказателя
│   │
│   ├── 📁 core/                    # Ядро AI системы
│   │   ├── ai_coordinator.py       # Координатор AI компонентов
│   │   ├── decision_maker.py       # Принятие решений
│   │   └── movement_engine.py      # Движение платформы
│   │
│   ├── 📁 strategy/                # Стратегии движения
│   │   ├── paddle_movement.py      # Стратегии движения платформы
│   │   ├── strategies.py           # Базовые стратегии
│   │   ├── target_tracker.py       # Отслеживание целей
│   │   └── zone_handler.py        # Обработка зон
│   │
│   ├── 📁 targeting/               # Система прицеливания
│   │   ├── target_selector.py      # Выбор целей
│   │   └── position_calculator.py  # Расчет позиций
│   │
│   ├── 📁 prediction/              # Предсказания
│   │   ├── trajectory_engine.py    # Движок траекторий
│   │   └── collision_detector.py  # Детектор столкновений
│   │
│   ├── 📁 learning/                # Обучение
│   │   ├── pattern_analyzer.py     # Анализ паттернов
│   │   └── strategy_optimizer.py   # Оптимизация стратегий
│   │
│   ├── 📁 cache/                   # Кэширование
│   │   └── memory_efficient_cache.py # Эффективный кэш
│   │
│   ├── 📁 models/                  # Обученные модели
│   │   └── ai_model.json           # Сохраненная модель
│   │
│   └── 📁 analysis/                # Анализ производительности
│       ├── all_game_results.json   # Результаты игр
│       └── analyze_performance_degradation.py # Анализ деградации
│
├── 📁 game/                        # Основная логика игры
│   ├── PyGameBall.py               # Главный файл игры (точка входа, 437 строк)
│   ├── game_loop_initialization.py # Инициализация игры (255 строк)
│   ├── game_loop_events.py         # Обработка событий (203 строки)
│   ├── game_loop_physics.py        # Физика и столкновения (845+ строк)
│   ├── game_loop_rendering.py      # Отрисовка игры (120 строк)
│   ├── game_loop_ai.py             # Логика AI (221 строка)
│   ├── game_config.py              # Конфигурация игры
│   ├── game_models.py              # Модели данных игры
│   ├── game_utils.py               # Утилиты игры
│   ├── game_ui.py                  # UI компоненты
│   ├── game_rendering.py           # Функции отрисовки
│   ├── game_main_helpers.py        # Вспомогательные функции (legacy)
│   ├── game_controllers.py        # Контроллеры игры
│   ├── game_views.py               # Представления игры
│   ├── highscores.py               # Система рекордов
│   ├── settings.py                 # Настройки игры
│   ├── di_container.py             # Dependency Injection контейнер
│   └── dirty_rects.py              # Оптимизация отрисовки
│
├── 📁 resources/                   # Ресурсы игры
│   ├── settings.json               # Настройки
│   ├── *.png, *.mp3                # Медиа файлы
│
├── 📁 docs/                        # Документация
│   ├── AI_ARCHITECTURE.md          # Архитектура AI
│   ├── AI_ARCHITECTURE_DIAGRAM.md  # Диаграммы архитектуры
│   ├── TRAJECTORY_CLUSTERING_AND_METRICS.md # Метрики траекторий
│   └── PROJECT_STRUCTURE.md        # Этот файл
│
├── 📄 pyproject.toml               # Конфигурация Poetry
├── 📄 poetry.lock                  # Зафиксированные зависимости
├── 📄 install_dependencies.bat     # Установка зависимостей
├── 📄 run_with_multithreading.bat  # Запуск с многопоточностью (Windows)
├── 📄 run_with_multithreading.sh   # Запуск с многопоточностью (Linux)
├── 📄 OPTIMIZATION_PLAN.md         # План оптимизации
├── 📄 PROGRESS_REPORT.md           # Отчет о прогрессе
├── 📄 REFACTORING_LOG.md           # Лог рефакторинга (часть 1)
├── 📄 REFACTORING_LOG_PART2.md     # Лог рефакторинга (часть 2)
├── 📄 REFACTORING_LOG_PART3_PYGAMEBALL.md # Лог рефакторинга PyGameBall
├── 📄 REMAINING_TASKS.md           # Оставшиеся задачи
├── 📄 PROJECT_IMPROVEMENT_PLAN.md  # План исправлений и доработок
├── 📄 MULTITHREADING_GUIDE.md      # Руководство по многопоточности
└── 📄 QUICK_START_MULTITHREADING.md # Быстрый старт многопоточности
```
