#!/usr/bin/env python3
"""Скрипт для анализа размеров файлов проекта."""

import os
from pathlib import Path


def get_file_sizes(root_dir="."):
    """Получить размеры всех Python файлов."""
    files = {}
    root_path = Path(root_dir)

    for py_file in root_path.rglob("*.py"):
        # Пропускаем .venv и __pycache__
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = len(f.readlines())
                files[str(py_file)] = lines
        except Exception as e:
            print(f"Ошибка при чтении {py_file}: {e}")

    return files


if __name__ == "__main__":
    files = get_file_sizes()

    # Фильтруем только ai_player модули
    ai_player_files = {k: v for k, v in files.items() if "ai_player" in k and "ai" in k}

    print("=== МОДУЛИ AI_PLAYER ===")
    for path, lines in sorted(
        ai_player_files.items(), key=lambda x: x[1], reverse=True
    ):
        rel_path = os.path.relpath(path)
        print(f"{lines:5} {rel_path}")

    print(f"\nВсего модулей ai_player: {len(ai_player_files)}")
    print(f"Общее количество строк: {sum(ai_player_files.values())}")

    # Основной файл
    main_file = ai_player_files.get("ai/ai_player.py", 0)
    print(f"\nОсновной файл ai_player.py: {main_file} строк")

    # Модули (без основного)
    modules = {k: v for k, v in ai_player_files.items() if k != "ai/ai_player.py"}
    print(f"Модули (без основного): {len(modules)}")
    print(f"Строк в модулях: {sum(modules.values())}")

    # Проверка на превышение 500 строк
    oversized = {k: v for k, v in modules.items() if v > 500}
    if oversized:
        print(f"\n[WARNING] Модули превышающие 500 строк ({len(oversized)}):")
        for path, lines in sorted(oversized.items(), key=lambda x: x[1], reverse=True):
            rel_path = os.path.relpath(path)
            print(f"  {lines:5} {rel_path}")
    else:
        print("\n[OK] Все модули <= 500 строк!")
