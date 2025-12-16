"""
Скрипт для анализа причин потери жизни AI игроком.
Анализирует логи и определяет паттерны потери мяча.
"""

import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Any


def analyze_session_logs(session_file: str) -> Dict[str, Any]:
    """Анализирует JSON лог сессии для поиска причин потери мяча."""
    if not os.path.exists(session_file):
        return {}

    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    actions = data.get("actions", [])

    # Ищем события потери мяча
    ball_loss_events = []
    brick_hits = []
    paddle_movements = []

    for action in actions:
        action_type = action.get("type", "")

        if action_type == "game_end" and not action.get("success", True):
            # Поражение - анализируем последние действия
            ball_loss_events.append(
                {
                    "timestamp": action.get("timestamp", 0),
                    "final_score": action.get("final_score", 0),
                    "bricks_remaining": action.get("final_bricks_remaining", 0),
                    "duration": action.get("game_duration", 0),
                }
            )

        elif action.get("action_type") == "brick_hit":
            brick_hits.append(
                {
                    "timestamp": action.get("timestamp", 0),
                    "bricks_destroyed": len(action.get("bricks_destroyed", [])),
                    "remaining_bricks": action.get("remaining_bricks", 0),
                }
            )

        elif action_type == "paddle_movement":
            paddle_movements.append(
                {
                    "timestamp": action.get("timestamp", 0),
                    "from_position": action.get("from_position", 0),
                    "to_position": action.get("to_position", 0),
                    "reason": action.get("reason", ""),
                    "confidence": action.get("confidence", 0),
                }
            )

    # Анализируем последние действия перед поражением
    analysis = {
        "total_actions": len(actions),
        "ball_loss_events": len(ball_loss_events),
        "brick_hits_count": len(brick_hits),
        "paddle_movements_count": len(paddle_movements),
        "recent_losses": ball_loss_events[-5:] if ball_loss_events else [],
    }

    return analysis


def analyze_text_logs(log_file: str) -> Dict[str, Any]:
    """Анализирует текстовые логи для поиска причин потери мяча."""
    if not os.path.exists(log_file):
        return {}

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Ищем паттерны
    ball_lost_patterns = []
    empty_bounce_patterns = []
    precision_targeting_patterns = []
    last_brick_patterns = []

    for i, line in enumerate(lines):
        # Потеря мяча
        if "BALL LOST" in line or "потеря" in line.lower() or "life" in line.lower():
            ball_lost_patterns.append(
                {
                    "line": i + 1,
                    "content": line.strip(),
                }
            )

        # Отбитие в пустоту
        if (
            "пустот" in line.lower()
            or "empty" in line.lower()
            or "отбитие" in line.lower()
        ):
            empty_bounce_patterns.append(
                {
                    "line": i + 1,
                    "content": line.strip(),
                }
            )

        # Точное прицеливание
        if (
            "precision" in line.lower()
            or "точное" in line.lower()
            or "few_bricks" in line.lower()
        ):
            precision_targeting_patterns.append(
                {
                    "line": i + 1,
                    "content": line.strip(),
                }
            )

        # Последний кирпич
        if "LAST BRICK" in line or "последн" in line.lower():
            last_brick_patterns.append(
                {
                    "line": i + 1,
                    "content": line.strip(),
                }
            )

    return {
        "total_lines": len(lines),
        "ball_lost_count": len(ball_lost_patterns),
        "empty_bounce_count": len(empty_bounce_patterns),
        "precision_targeting_count": len(precision_targeting_patterns),
        "last_brick_count": len(last_brick_patterns),
        "recent_ball_lost": ball_lost_patterns[-10:] if ball_lost_patterns else [],
        "recent_empty_bounce": (
            empty_bounce_patterns[-10:] if empty_bounce_patterns else []
        ),
        "recent_precision": (
            precision_targeting_patterns[-10:] if precision_targeting_patterns else []
        ),
        "recent_last_brick": last_brick_patterns[-10:] if last_brick_patterns else [],
    }


def print_analysis():
    """Выводит анализ логов."""
    print("=" * 80)
    print("АНАЛИЗ ПРИЧИН ПОТЕРИ ЖИЗНИ И ОТСУТСТВИЯ ПРИЦЕЛЬНОГО УДАРА")
    print("=" * 80)
    print()

    # Анализируем JSON логи
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    if os.path.exists(logs_dir):
        json_files = [f for f in os.listdir(logs_dir) if f.endswith(".json")]
        if json_files:
            latest_json = max(
                json_files, key=lambda f: os.path.getmtime(os.path.join(logs_dir, f))
            )
            json_path = os.path.join(logs_dir, latest_json)
            print(f"📊 Анализ JSON лога: {latest_json}")
            json_analysis = analyze_session_logs(json_path)
            if json_analysis:
                print(f"   Всего действий: {json_analysis.get('total_actions', 0)}")
                print(
                    f"   Событий потери мяча: {json_analysis.get('ball_loss_events', 0)}"
                )
                print(
                    f"   Попаданий в кирпичи: {json_analysis.get('brick_hits_count', 0)}"
                )
                print(
                    f"   Движений платформы: {json_analysis.get('paddle_movements_count', 0)}"
                )
                print()

    # Анализируем текстовые логи
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    if os.path.exists(logs_dir):
        # Ищем поддиректории с логами
        for item in os.listdir(logs_dir):
            item_path = os.path.join(logs_dir, item)
            if os.path.isdir(item_path):
                log_files = [f for f in os.listdir(item_path) if f.endswith(".log")]
                if log_files:
                    latest_log = max(
                        log_files,
                        key=lambda f: os.path.getmtime(os.path.join(item_path, f)),
                    )
                    log_path = os.path.join(item_path, latest_log)
                    print(f"📝 Анализ текстового лога: {latest_log}")
                    text_analysis = analyze_text_logs(log_path)
                    if text_analysis:
                        print(f"   Всего строк: {text_analysis.get('total_lines', 0)}")
                        print(
                            f"   Упоминаний потери мяча: {text_analysis.get('ball_lost_count', 0)}"
                        )
                        print(
                            f"   Упоминаний отбития в пустоту: {text_analysis.get('empty_bounce_count', 0)}"
                        )
                        print(
                            f"   Упоминаний точного прицеливания: {text_analysis.get('precision_targeting_count', 0)}"
                        )
                        print(
                            f"   Упоминаний последнего кирпича: {text_analysis.get('last_brick_count', 0)}"
                        )
                        print()

                        if text_analysis.get("recent_empty_bounce"):
                            print("🔴 ПОСЛЕДНИЕ ОТБИТИЯ В ПУСТОТУ:")
                            for item in text_analysis["recent_empty_bounce"][-5:]:
                                print(
                                    f"   Строка {item['line']}: {item['content'][:100]}"
                                )
                            print()

                        if text_analysis.get("recent_last_brick"):
                            print("🎯 ПОСЛЕДНИЕ УПОМИНАНИЯ ПОСЛЕДНЕГО КИРПИЧА:")
                            for item in text_analysis["recent_last_brick"][-5:]:
                                print(
                                    f"   Строка {item['line']}: {item['content'][:100]}"
                                )
                            print()

    print("=" * 80)


if __name__ == "__main__":
    print_analysis()
