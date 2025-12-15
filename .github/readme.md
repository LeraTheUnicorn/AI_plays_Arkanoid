![5000.png](../resources/5000.png)

## Схема проекта

```
├── 📁 ai/                          # AI-система для авторежима
│   ├── ai_player.py                # Основной класс AIPlayer (координатор)
│   ├── ai_player_*.py              # Миксины для функциональности AIPlayer
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
│   ├── PyGameBall.py               # Главный файл игры (точка входа)
│   ├── game_config.py              # Конфигурация игры
│   ├── game_models.py              # Модели данных игры
│   ├── game_utils.py               # Утилиты игры
│   ├── game_ui.py                  # UI компоненты
│   ├── game_rendering.py           # Отрисовка игры
│   ├── game_main_helpers.py        # Вспомогательные функции main()
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
├── 📄 run_with_multithreading.bat  # Запуск с многопоточностью
├── 📄 run_with_multithreading.sh   # Запуск с многопоточностью (Linux)
├── 📄 OPTIMIZATION_PLAN.md         # План оптимизации
├── 📄 PROGRESS_REPORT.md           # Отчет о прогрессе
├── 📄 REFACTORING_LOG.md           # Лог рефакторинга
├── 📄 MULTITHREADING_GUIDE.md      # Руководство по многопоточности
└── 📄 QUICK_START_MULTITHREADING.md # Быстрый старт многопоточности
```