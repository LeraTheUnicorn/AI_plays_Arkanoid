# Тесты для проекта Arkanoid Game

Этот каталог содержит тесты для всех модулей проекта.

## Структура

```
tests/
├── conftest.py          # Общие фикстуры и настройки
├── ai/                  # Тесты для AI модулей
│   ├── test_game_state.py
│   ├── test_config.py
│   ├── test_exceptions.py
│   ├── test_platform_utils.py
│   ├── test_logging_config.py
│   └── test_ai_player_init.py
├── game/                # Тесты для game модулей
│   ├── test_game_models.py
│   ├── test_game_config.py
│   └── test_game_utils.py
└── utils/               # Тесты для utils модулей
```

## Установка зависимостей

Проект использует Poetry для управления зависимостями. Убедитесь, что у вас установлен Poetry, затем выполните:

```bash
poetry install
```

Или если используете pip:

```bash
pip install pytest pytest-cov
```

## Запуск тестов

### Запуск всех тестов

```bash
pytest
```

### Запуск тестов для конкретного модуля

```bash
pytest tests/ai/
pytest tests/game/
pytest tests/utils/
```

### Запуск конкретного тестового файла

```bash
pytest tests/ai/test_game_state.py
```

### Запуск с подробным выводом

```bash
pytest -v
```

### Запуск с покрытием кода

```bash
pytest --cov=ai --cov=game --cov-report=html
```

Это создаст HTML отчет в `htmlcov/index.html`.

### Запуск только быстрых тестов

```bash
pytest -m "not slow"
```

## Структура тестов

### Фикстуры (conftest.py)

Общие фикстуры доступны для всех тестов:
- `mock_pygame` - мокирование pygame
- `mock_game_state` - создание мокового GameState
- `mock_ball` - создание мокового мяча
- `mock_paddle` - создание моковой платформы
- `mock_bricks` - создание списка кирпичей
- `screen_dimensions` - размеры экрана

### Пример использования фикстур

```python
def test_something(mock_game_state, screen_dimensions):
    state = mock_game_state
    width = screen_dimensions['width']
    # ... ваш тест
```

## Написание новых тестов

### Шаблон тестового файла

```python
"""
Тесты для модуля example.py
"""

import pytest
from module import ClassName


class TestClassName:
    """Тесты для класса ClassName."""
    
    def test_method_name(self):
        """Тест метода method_name."""
        obj = ClassName()
        result = obj.method_name()
        assert result == expected_value
```

### Рекомендации

1. **Именование**: Тестовые файлы должны начинаться с `test_`
2. **Классы**: Группируйте связанные тесты в классы
3. **Документация**: Добавляйте docstrings для классов и методов
4. **Изоляция**: Каждый тест должен быть независимым
5. **Моки**: Используйте моки для внешних зависимостей (pygame, файловая система)

## Покрытие кода

Цель - достичь покрытия кода не менее 80% для основных модулей.

Проверить текущее покрытие:

```bash
pytest --cov=ai --cov=game --cov-report=term-missing
```

## Отладка тестов

### Запуск с выводом print

```bash
pytest -s
```

### Запуск конкретного теста

```bash
pytest tests/ai/test_game_state.py::TestPoint::test_point_creation -v
```

### Использование отладчика

```bash
pytest --pdb
```

Это запустит отладчик при падении теста.

## CI/CD

Тесты автоматически запускаются в CI/CD пайплайне. Убедитесь, что все тесты проходят перед созданием PR.

## Известные проблемы

- Некоторые тесты могут требовать инициализации pygame (используйте фикстуру `mock_pygame`)
- Тесты, работающие с файловой системой, должны использовать временные директории

## Дополнительные ресурсы

- [Документация pytest](https://docs.pytest.org/)
- [Документация по фикстурам](https://docs.pytest.org/en/stable/fixture.html)
- [Моки в Python](https://docs.python.org/3/library/unittest.mock.html)

