"""
Скрипт для анализа падения винрейта AI игрока.
Анализирует логи и выявляет причины поражений.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Any
from datetime import datetime


def load_game_results() -> List[Dict[str, Any]]:
    """Загружает результаты всех игр."""
    results_file = os.path.join(os.path.dirname(__file__), "all_game_results.json")
    if not os.path.exists(results_file):
        print(f"Файл {results_file} не найден!")
        return []

    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_winrate_trend(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует тренд винрейта."""
    if not results:
        return {}

    total_games = len(results)
    wins = sum(1 for r in results if r.get("success", False))
    losses = total_games - wins
    overall_winrate = (wins / total_games * 100) if total_games > 0 else 0

    # Анализ по блокам (последние 50, 100, 200 игр)
    recent_50 = results[-50:] if len(results) >= 50 else results
    recent_100 = results[-100:] if len(results) >= 100 else results
    recent_200 = results[-200:] if len(results) >= 200 else results

    def calc_winrate(games):
        if not games:
            return 0
        wins_count = sum(1 for g in games if g.get("success", False))
        return (wins_count / len(games) * 100) if games else 0

    return {
        "total_games": total_games,
        "total_wins": wins,
        "total_losses": losses,
        "overall_winrate": overall_winrate,
        "recent_50_winrate": calc_winrate(recent_50),
        "recent_100_winrate": calc_winrate(recent_100),
        "recent_200_winrate": calc_winrate(recent_200),
        "recent_50_games": len(recent_50),
        "recent_100_games": len(recent_100),
        "recent_200_games": len(recent_200),
    }


def analyze_loss_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует паттерны поражений."""
    losses = [r for r in results if not r.get("success", False)]

    if not losses:
        return {"total_losses": 0}

    # Анализ по оставшимся кирпичам
    bricks_remaining_stats = defaultdict(int)
    for loss in losses:
        bricks = loss.get("final_bricks_remaining", -1)
        bricks_remaining_stats[bricks] += 1

    # Анализ по счету
    score_ranges = {
        "0-10": 0,
        "11-20": 0,
        "21-30": 0,
        "31-40": 0,
        "41-49": 0,
        "50": 0,
    }

    for loss in losses:
        score = loss.get("final_score", 0)
        if score == 0:
            score_ranges["0-10"] += 1
        elif score <= 10:
            score_ranges["0-10"] += 1
        elif score <= 20:
            score_ranges["11-20"] += 1
        elif score <= 30:
            score_ranges["21-30"] += 1
        elif score <= 40:
            score_ranges["31-40"] += 1
        elif score < 50:
            score_ranges["41-49"] += 1
        else:
            score_ranges["50"] += 1

    # Анализ по длительности игры
    durations = [loss.get("game_duration", 0) for loss in losses]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total_losses": len(losses),
        "bricks_remaining_distribution": dict(bricks_remaining_stats),
        "score_distribution": score_ranges,
        "average_duration": avg_duration,
        "min_duration": min(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0,
    }


def analyze_victory_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует паттерны побед."""
    victories = [r for r in results if r.get("success", False)]

    if not victories:
        return {"total_victories": 0}

    # Проверка на аномалии (победа с оставшимися кирпичами)
    anomalies = [v for v in victories if v.get("final_bricks_remaining", 0) > 0]

    durations = [v.get("game_duration", 0) for v in victories]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total_victories": len(victories),
        "anomalies_with_remaining_bricks": len(anomalies),
        "average_duration": avg_duration,
        "min_duration": min(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0,
    }


def analyze_recent_performance(
    results: List[Dict[str, Any]], window: int = 50
) -> Dict[str, Any]:
    """Анализирует последние N игр."""
    if len(results) < window:
        window = len(results)

    recent = results[-window:]

    # Подсчет последовательных поражений
    consecutive_losses = 0
    max_consecutive_losses = 0
    current_streak = 0

    for game in recent:
        if game.get("success", False):
            current_streak = 0
        else:
            current_streak += 1
            consecutive_losses = max(consecutive_losses, current_streak)
            max_consecutive_losses = max(max_consecutive_losses, current_streak)

    # Подсчет последовательных побед
    consecutive_wins = 0
    max_consecutive_wins = 0
    current_win_streak = 0

    for game in recent:
        if game.get("success", False):
            current_win_streak += 1
            consecutive_wins = max(consecutive_wins, current_win_streak)
            max_consecutive_wins = max(max_consecutive_wins, current_win_streak)
        else:
            current_win_streak = 0

    return {
        "window_size": window,
        "wins": sum(1 for g in recent if g.get("success", False)),
        "losses": sum(1 for g in recent if not g.get("success", False)),
        "winrate": (
            (sum(1 for g in recent if g.get("success", False)) / len(recent) * 100)
            if recent
            else 0
        ),
        "max_consecutive_losses": max_consecutive_losses,
        "max_consecutive_wins": max_consecutive_wins,
    }


def print_analysis_report(results: List[Dict[str, Any]]):
    """Выводит отчет об анализе."""
    print("=" * 80)
    print("АНАЛИЗ ПАДЕНИЯ ВИНРЕЙТА AI ИГРОКА")
    print("=" * 80)
    print()

    if not results:
        print("Нет данных для анализа!")
        return

    # Общий анализ винрейта
    winrate_trend = analyze_winrate_trend(results)
    print("📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего игр: {winrate_trend['total_games']}")
    print(f"   Побед: {winrate_trend['total_wins']}")
    print(f"   Поражений: {winrate_trend['total_losses']}")
    print(f"   Общий винрейт: {winrate_trend['overall_winrate']:.2f}%")
    print()

    print("📈 ТРЕНД ВИНРЕЙТА:")
    print(
        f"   Последние 50 игр: {winrate_trend['recent_50_winrate']:.2f}% ({winrate_trend['recent_50_games']} игр)"
    )
    print(
        f"   Последние 100 игр: {winrate_trend['recent_100_winrate']:.2f}% ({winrate_trend['recent_100_games']} игр)"
    )
    print(
        f"   Последние 200 игр: {winrate_trend['recent_200_winrate']:.2f}% ({winrate_trend['recent_200_games']} игр)"
    )
    print()

    # Анализ последних игр
    recent_perf = analyze_recent_performance(results, window=50)
    print("🎯 ПОСЛЕДНИЕ 50 ИГР:")
    print(f"   Побед: {recent_perf['wins']}")
    print(f"   Поражений: {recent_perf['losses']}")
    print(f"   Винрейт: {recent_perf['winrate']:.2f}%")
    print(
        f"   Максимум последовательных поражений: {recent_perf['max_consecutive_losses']}"
    )
    print(f"   Максимум последовательных побед: {recent_perf['max_consecutive_wins']}")
    print()

    # Анализ поражений
    loss_patterns = analyze_loss_patterns(results)
    if loss_patterns.get("total_losses", 0) > 0:
        print("❌ АНАЛИЗ ПОРАЖЕНИЙ:")
        print(f"   Всего поражений: {loss_patterns['total_losses']}")
        print(f"   Распределение по оставшимся кирпичам:")
        for bricks, count in sorted(
            loss_patterns["bricks_remaining_distribution"].items()
        ):
            print(
                f"      {bricks} кирпичей: {count} игр ({count/loss_patterns['total_losses']*100:.1f}%)"
            )
        print(f"   Распределение по счету:")
        for score_range, count in loss_patterns["score_distribution"].items():
            if count > 0:
                print(
                    f"      {score_range}: {count} игр ({count/loss_patterns['total_losses']*100:.1f}%)"
                )
        print(
            f"   Средняя длительность поражения: {loss_patterns['average_duration']:.2f} сек"
        )
        print(
            f"   Мин/Макс длительность: {loss_patterns['min_duration']:.2f} / {loss_patterns['max_duration']:.2f} сек"
        )
        print()

    # Анализ побед
    victory_patterns = analyze_victory_patterns(results)
    if victory_patterns.get("total_victories", 0) > 0:
        print("✅ АНАЛИЗ ПОБЕД:")
        print(f"   Всего побед: {victory_patterns['total_victories']}")
        if victory_patterns.get("anomalies_with_remaining_bricks", 0) > 0:
            print(
                f"   ⚠️  АНОМАЛИИ: {victory_patterns['anomalies_with_remaining_bricks']} побед с оставшимися кирпичами!"
            )
        print(
            f"   Средняя длительность победы: {victory_patterns['average_duration']:.2f} сек"
        )
        print(
            f"   Мин/Макс длительность: {victory_patterns['min_duration']:.2f} / {victory_patterns['max_duration']:.2f} сек"
        )
        print()

    # Вывод последних поражений
    recent_losses = [r for r in results[-20:] if not r.get("success", False)]
    if recent_losses:
        print("🔍 ПОСЛЕДНИЕ ПОРАЖЕНИЯ (последние 20 игр):")
        for i, loss in enumerate(recent_losses[-10:], 1):
            score = loss.get("final_score", 0)
            bricks = loss.get("final_bricks_remaining", -1)
            duration = loss.get("game_duration", 0)
            print(
                f"   {i}. Счет: {score}, Осталось кирпичей: {bricks}, Длительность: {duration:.1f}с"
            )
        print()

    # Вывод рекомендаций
    print("💡 РЕКОМЕНДАЦИИ:")
    if winrate_trend["recent_50_winrate"] < 100:
        print("   ⚠️  Винрейт упал ниже 100%!")
        if loss_patterns.get("total_losses", 0) > 0:
            bricks_dist = loss_patterns["bricks_remaining_distribution"]
            if (
                1 in bricks_dist
                and bricks_dist[1] > loss_patterns["total_losses"] * 0.5
            ):
                print("   🔴 КРИТИЧНО: Большинство поражений с 1 оставшимся кирпичом!")
                print("      → Проблема: AI не может уничтожить последний кирпич")
                print("      → Возможные причины:")
                print("         - Проблемы с предсказанием траектории")
                print("         - Неправильная логика выбора цели")
                print("         - Проблемы с позиционированием платформы")

            if 49 in bricks_dist or 50 in bricks_dist:
                print("   🔴 КРИТИЧНО: Поражения с почти всеми кирпичами!")
                print("      → Проблема: AI теряет мяч в начале игры")
                print("      → Возможные причины:")
                print("         - Проблемы с реакцией на старт игры")
                print("         - Неправильная обработка начальной траектории")

        if recent_perf["max_consecutive_losses"] >= 3:
            print(
                f"   ⚠️  Обнаружена серия из {recent_perf['max_consecutive_losses']} последовательных поражений"
            )
            print("      → Возможная деградация модели обучения")

    print()
    print("=" * 80)


if __name__ == "__main__":
    results = load_game_results()
    print_analysis_report(results)
