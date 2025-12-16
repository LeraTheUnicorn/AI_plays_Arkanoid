"""
Скрипт для сброса данных обучения AI.

Использование:
    python reset_learning.py

Этот скрипт:
1. Создает резервную копию текущей модели
2. Сбрасывает все данные обучения
3. Начинает обучение с нуля
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path


def get_ai_directory():
    """Определяет каталог для AI файлов"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ai_dir = os.path.join(current_dir, "ai")
    return ai_dir


def backup_model(model_path: str) -> str:
    """Создает резервную копию модели"""
    if not os.path.exists(model_path):
        print(f"Модель не найдена: {model_path}")
        return None

    # Создаем папку для бэкапов
    ai_dir = os.path.dirname(model_path)
    backups_dir = os.path.join(ai_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)

    # Имя файла бэкапа с датой и временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"ai_model_backup_{timestamp}.json"
    backup_path = os.path.join(backups_dir, backup_name)

    # Копируем файл
    shutil.copy2(model_path, backup_path)
    print(f"✅ Резервная копия создана: {backup_path}")
    return backup_path


def reset_model(model_path: str) -> bool:
    """Сбрасывает модель к начальному состоянию"""
    try:
        # Начальные данные обучения
        default_data = {
            "strategy_weights": {
                "aggressive": 0.5,
                "conservative": 0.5,
                "precision": 0.5,
                "speed": 0.5,
            },
            "position_preferences": {},
            "trajectory_patterns": {},
            "success_factors": {},
            "historical_performance": [],
            "learning_stats": {
                "total_learning_iterations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "average_improvement": 0.0,
            },
            "success_prediction_model": None,
            "model_metrics": {},
            "paddle_speed_factors": {},
            "user_prompt_destruction_control": "",
        }

        # Сохраняем сброшенную модель
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Модель сброшена: {model_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе модели: {e}")
        return False


def get_model_info(model_path: str) -> dict:
    """Получает информацию о текущей модели"""
    if not os.path.exists(model_path):
        return {"exists": False}

    try:
        with open(model_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stats = data.get("learning_stats", {})
        return {
            "exists": True,
            "total_iterations": stats.get("total_learning_iterations", 0),
            "successful_adaptations": stats.get("successful_adaptations", 0),
            "failed_adaptations": stats.get("failed_adaptations", 0),
            "position_preferences_count": len(data.get("position_preferences", {})),
            "trajectory_patterns_count": len(data.get("trajectory_patterns", {})),
            "file_size_kb": os.path.getsize(model_path) / 1024,
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}


def main():
    """Основная функция"""
    print("=" * 60)
    print("Сброс данных обучения AI")
    print("=" * 60)
    print()

    # Определяем путь к модели
    ai_dir = get_ai_directory()
    models_dir = os.path.join(ai_dir, "models")
    model_path = os.path.join(models_dir, "ai_model.json")

    # Проверяем существование модели
    if not os.path.exists(model_path):
        print(f"⚠️  Модель не найдена: {model_path}")
        print("Создаем новую модель...")
        os.makedirs(models_dir, exist_ok=True)
    else:
        # Показываем информацию о текущей модели
        print("📊 Информация о текущей модели:")
        info = get_model_info(model_path)
        if "error" in info:
            print(f"   ⚠️  Ошибка при чтении: {info['error']}")
        else:
            print(f"   - Всего итераций обучения: {info.get('total_iterations', 0)}")
            print(f"   - Успешных адаптаций: {info.get('successful_adaptations', 0)}")
            print(f"   - Неудачных адаптаций: {info.get('failed_adaptations', 0)}")
            print(
                f"   - Изученных позиций: {info.get('position_preferences_count', 0)}"
            )
            print(
                f"   - Паттернов траекторий: {info.get('trajectory_patterns_count', 0)}"
            )
            print(f"   - Размер файла: {info.get('file_size_kb', 0):.1f} KB")
        print()

    # Спрашиваем подтверждение
    print("⚠️  ВНИМАНИЕ: Это действие удалит все данные обучения!")
    print("   Резервная копия будет создана автоматически.")
    print()
    response = input("Продолжить? (yes/no): ").strip().lower()

    if response not in ("yes", "y", "да", "д"):
        print("❌ Отменено пользователем")
        return

    print()

    # Создаем резервную копию
    if os.path.exists(model_path):
        backup_path = backup_model(model_path)
        if backup_path is None:
            print("❌ Не удалось создать резервную копию. Прерывание.")
            return

    # Сбрасываем модель
    if reset_model(model_path):
        print()
        print("=" * 60)
        print("✅ Сброс выполнен успешно!")
        print("=" * 60)
        print()
        print("Следующие шаги:")
        print("1. Запустите игру в режиме обучения")
        print("2. AI начнет обучение с нуля")
        print("3. Если что-то пойдет не так, восстановите бэкап из:")
        print(f"   {os.path.join(ai_dir, 'models', 'backups')}")
    else:
        print()
        print("❌ Ошибка при сбросе модели")


if __name__ == "__main__":
    main()
