# -*- coding: utf-8 -*-
"""Скрипт для удаления дублированного кода из ai_player.py"""

with open("ai/ai_player.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Находим начало дублированного блока (после комментария "# Обучение по результату действия")
start_idx = None
for i, line in enumerate(lines):
    if i > 750 and "# Обучение по результату действия" in line:
        # Ищем следующую непустую строку после комментариев
        for j in range(i + 1, min(i + 5, len(lines))):
            if lines[j].strip() and not lines[j].strip().startswith("#"):
                start_idx = j
                break
        if start_idx:
            break

# Находим конец дублированного блока (перед правильным методом learn_from_result)
end_idx = None
for i, line in enumerate(lines):
    if i > 2800 and line.strip().startswith("def learn_from_result"):
        # Ищем строку с комментарием перед методом
        for j in range(max(0, i - 5), i):
            if "# Обучение по результату действия" in lines[j]:
                # Находим конец комментариев
                for k in range(j + 1, i):
                    if lines[k].strip() and not lines[k].strip().startswith("#"):
                        end_idx = k
                        break
                if not end_idx:
                    end_idx = j + 3  # После комментариев
                break
        if not end_idx:
            end_idx = i
        break

if start_idx and end_idx and start_idx < end_idx:
    print(
        f"Найдены границы: start={start_idx} (строка {start_idx+1}), end={end_idx} (строка {end_idx+1})"
    )
    print(f"Удаляется {end_idx - start_idx} строк дублированного кода")
    print(f"Первая строка для удаления: {repr(lines[start_idx][:80])}")
    print(f"Последняя строка перед удалением: {repr(lines[end_idx-1][:80])}")

    # Удаляем дублированный блок
    new_lines = lines[:start_idx] + lines[end_idx:]

    with open("ai/ai_player.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"Успешно удалено {end_idx - start_idx} строк")
    print(f"Новый размер файла: {len(new_lines)} строк (было {len(lines)})")
else:
    print(f"Границы не найдены: start_idx={start_idx}, end_idx={end_idx}")
