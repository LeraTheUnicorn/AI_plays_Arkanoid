"""
Скрипт для анализа потери мяча из логов консоли.
Анализирует паттерны потери мяча и выявляет корневые причины.
"""

import re
from typing import List, Dict, Any, cast
from collections import defaultdict


def parse_ball_loss_log(log_text: str) -> List[Dict[str, Any]]:
    """Парсит логи потери мяча из текста."""
    losses = []
    
    # Паттерн для поиска блоков диагностики потери мяча
    pattern = r'\[BALL LOST\].*?========================================================'
    
    matches = re.findall(pattern, log_text, re.DOTALL)
    
    for match in matches:
        loss_data = {}
        
        # Извлекаем данные о мяче
        ball_match = re.search(r'Мяч: pos=\(([\d.]+), ([\d.]+)\) bottom=([\d.]+) vel=\(([-\d.]+), ([\d.]+)\) speed=([\d.]+)', match)
        if ball_match:
            loss_data['ball_x'] = float(ball_match.group(1))
            loss_data['ball_y'] = float(ball_match.group(2))
            loss_data['ball_bottom'] = float(ball_match.group(3))
            loss_data['ball_vel_x'] = float(ball_match.group(4))
            loss_data['ball_vel_y'] = float(ball_match.group(5))
            loss_data['ball_speed'] = float(ball_match.group(6))
        
        # Извлекаем данные о платформе
        paddle_match = re.search(r'Платформа: center_x=([\d.]+) top=([\d.]+) left=([\d.]+) right=([\d.]+)', match)
        if paddle_match:
            loss_data['paddle_x'] = float(paddle_match.group(1))
            loss_data['paddle_top'] = float(paddle_match.group(2))
            loss_data['paddle_left'] = float(paddle_match.group(3))
            loss_data['paddle_right'] = float(paddle_match.group(4))
        
        # Извлекаем расстояние
        dist_match = re.search(r'Расстояние: horizontal=([\d.]+)px vertical=([\d.]+)px', match)
        if dist_match:
            loss_data['horizontal_distance'] = float(dist_match.group(1))
            loss_data['vertical_distance'] = float(dist_match.group(2))
        
        # Извлекаем информацию о зоне
        zone_match = re.search(r'Мяч относительно платформы: ([^(]+) \(offset=([-\d.]+)px\)', match)
        if zone_match:
            loss_data['ball_zone'] = str(zone_match.group(1).strip())
            loss_data['ball_offset'] = float(str(zone_match.group(2)))
        
        # Извлекаем информацию о попадании
        hit_match = re.search(r'Мяч ударился о платформу: (True|False)', match)
        if hit_match:
            loss_data['ball_hit_paddle'] = hit_match.group(1) == 'True'
        
        # Извлекаем оптимальную позицию
        optimal_match = re.search(r'Целевая позиция AI: optimal_x=([\d.]+) distance_to_optimal=([\d.]+)px', match)
        if optimal_match:
            loss_data['optimal_x'] = float(optimal_match.group(1))
            loss_data['distance_to_optimal'] = float(optimal_match.group(2))
        
        # Извлекаем предсказание
        pred_match = re.search(r'🔴 ПРЕДСКАЗАНИЕ: Предсказанная позиция приземления: ([\d.]+)px', match)
        if pred_match:
            loss_data['predicted_landing_x'] = float(pred_match.group(1))
        
        actual_match = re.search(r'🔴 ПРЕДСКАЗАНИЕ: Фактическая позиция мяча: ([\d.]+)px', match)
        if actual_match:
            loss_data['actual_ball_x'] = float(actual_match.group(1))
        
        error_match = re.search(r'🔴 ПРЕДСКАЗАНИЕ: Ошибка предсказания: ([\d.]+)px', match)
        if error_match:
            loss_data['prediction_error'] = float(error_match.group(1))
        
        miss_match = re.search(r'🔴 ПРЕДСКАЗАНИЕ: Мяч пролетел мимо на: ([\d.]+)px от центра платформы', match)
        if miss_match:
            loss_data['miss_distance'] = float(miss_match.group(1))
        
        # Извлекаем скорость платформы
        speed_match = re.search(r'Скорость платформы: base=(\d+) adjusted=(\d+)', match)
        if speed_match:
            loss_data['paddle_base_speed'] = int(speed_match.group(1))
            loss_data['paddle_adjusted_speed'] = int(speed_match.group(2))
        
        # Извлекаем информацию о зонах
        zones_match = re.search(r'Зоны: separation_start=(\d+) paddle_start=(\d+) ball_was_in_zone=(True|False)', match)
        if zones_match:
            loss_data['separation_start'] = int(zones_match.group(1))
            loss_data['paddle_start'] = int(zones_match.group(2))
            loss_data['ball_was_in_zone'] = zones_match.group(3) == 'True'
        
        # Извлекаем информацию о целевой позиции
        target_set_match = re.search(r'Целевая позиция установлена: (True|False)', match)
        if target_set_match:
            loss_data['target_position_set'] = target_set_match.group(1) == 'True'
        
        saved_target_match = re.search(r'Сохраненная целевая позиция: ([\d.]+) distance=([\d.]+)px', match)
        if saved_target_match:
            loss_data['saved_target_position'] = float(saved_target_match.group(1))
            loss_data['distance_to_saved_target'] = float(saved_target_match.group(2))
        
        # Извлекаем жизни
        lives_match = re.search(r'Жизни: (\d+)', match)
        if lives_match:
            loss_data['lives_left'] = int(lives_match.group(1))
        
        if loss_data:
            losses.append(loss_data)
    
    return losses


def analyze_losses(losses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует потери мяча и выявляет паттерны."""
    if not losses:
        return {"error": "Нет данных о потерях мяча"}
    
    analysis: Dict[str, Any] = {
        "total_losses": len(losses),
        "patterns": {},
        "statistics": {},
        "issues": []
    }
    
    # Статистика по зонам
    zones: Dict[str, int] = defaultdict(int)
    for loss in losses:
        zone = str(loss.get('ball_zone', 'UNKNOWN'))
        zones[zone] += 1
    patterns_dict = cast(Dict[str, Any], analysis['patterns'])
    patterns_dict['zones'] = dict(zones)
    
    # Статистика по расстояниям
    distances = [loss.get('horizontal_distance', 0) for loss in losses if 'horizontal_distance' in loss]
    if distances:
        stats_dict = cast(Dict[str, Any], analysis['statistics'])
        stats_dict['avg_horizontal_distance'] = sum(distances) / len(distances)
        stats_dict['max_horizontal_distance'] = max(distances)
        stats_dict['min_horizontal_distance'] = min(distances)
    
    # Статистика по ошибкам предсказания
    prediction_errors = [loss.get('prediction_error', 0) for loss in losses if 'prediction_error' in loss]
    if prediction_errors:
        stats_dict = cast(Dict[str, Any], analysis['statistics'])
        stats_dict['avg_prediction_error'] = sum(prediction_errors) / len(prediction_errors)
        stats_dict['max_prediction_error'] = max(prediction_errors)
    
    # Статистика по расстоянию до оптимальной позиции
    distances_to_optimal = [loss.get('distance_to_optimal', 0) for loss in losses if 'distance_to_optimal' in loss]
    if distances_to_optimal:
        stats_dict = cast(Dict[str, Any], analysis['statistics'])
        stats_dict['avg_distance_to_optimal'] = sum(distances_to_optimal) / len(distances_to_optimal)
        stats_dict['max_distance_to_optimal'] = max(distances_to_optimal)
        stats_dict['min_distance_to_optimal'] = min(distances_to_optimal)
    
    # Разница между optimal_x и saved_target_position
    target_differences = []
    for loss in losses:
        if 'optimal_x' in loss and 'saved_target_position' in loss:
            diff = abs(loss['optimal_x'] - loss['saved_target_position'])
            target_differences.append(diff)
            if diff > 100:  # Большая разница - проблема!
                issues_list = cast(List[Dict[str, Any]], analysis['issues'])
                issues_list.append({
                    'type': 'TARGET_MISMATCH',
                    'description': f'Большая разница между optimal_x ({loss["optimal_x"]:.1f}) и saved_target ({loss["saved_target_position"]:.1f}): {diff:.1f}px',
                    'loss': loss
                })
    
    if target_differences:
        stats_dict = cast(Dict[str, Any], analysis['statistics'])
        stats_dict['avg_target_difference'] = sum(target_differences) / len(target_differences)
        stats_dict['max_target_difference'] = max(target_differences)
    
    # Проблема: платформа не успевает доехать
    for loss in losses:
        if 'distance_to_optimal' in loss and 'paddle_adjusted_speed' in loss:
            distance = loss['distance_to_optimal']
            speed = loss['paddle_adjusted_speed']
            if distance > 200 and speed > 0:  # Большое расстояние
                # Рассчитываем время до приземления мяча
                if 'ball_y' in loss and 'paddle_start' in loss and 'ball_vel_y' in loss:
                    ball_y = loss['ball_y']
                    paddle_y = loss['paddle_start']
                    ball_vel_y = loss['ball_vel_y']
                    if ball_vel_y > 0:
                        time_to_paddle = (paddle_y - ball_y) / ball_vel_y
                        frames_to_reach = distance / speed if speed > 0 else float('inf')
                        if frames_to_reach > time_to_paddle * 1.2:  # Платформа не успеет
                            issues_list = cast(List[Dict[str, Any]], analysis['issues'])
                            issues_list.append({
                                'type': 'PADDLE_TOO_SLOW',
                                'description': f'Платформа не успевает: нужно {frames_to_reach:.1f} кадров, но есть только {time_to_paddle:.1f} кадров',
                                'loss': loss
                            })
    
    # Проблема: целевая позиция установлена, но неправильная
    for loss in losses:
        if loss.get('target_position_set') and 'saved_target_position' in loss and 'optimal_x' in loss:
            saved = loss['saved_target_position']
            optimal = loss['optimal_x']
            if abs(saved - optimal) > 50:  # Разница больше 50px
                issues_list = cast(List[Dict[str, Any]], analysis['issues'])
                issues_list.append({
                    'type': 'WRONG_TARGET_SET',
                    'description': f'Целевая позиция установлена неправильно: saved={saved:.1f}, optimal={optimal:.1f}, разница={abs(saved-optimal):.1f}px',
                    'loss': loss
                })
    
    return analysis


def print_analysis(analysis: Dict[str, Any]) -> None:
    """Выводит анализ в читаемом формате."""
    print("=" * 80)
    print("АНАЛИЗ ПОТЕРИ МЯЧА")
    print("=" * 80)
    print(f"\nВсего потерь мяча: {analysis['total_losses']}")
    
    if 'statistics' in analysis:
        print("\n--- СТАТИСТИКА ---")
        stats = analysis['statistics']
        if 'avg_horizontal_distance' in stats:
            print(f"Среднее горизонтальное расстояние: {stats['avg_horizontal_distance']:.1f}px")
            print(f"Максимальное: {stats['max_horizontal_distance']:.1f}px")
            print(f"Минимальное: {stats['min_horizontal_distance']:.1f}px")
        
        if 'avg_prediction_error' in stats:
            print(f"\nСредняя ошибка предсказания: {stats['avg_prediction_error']:.1f}px")
            print(f"Максимальная: {stats['max_prediction_error']:.1f}px")
        
        if 'avg_distance_to_optimal' in stats:
            print(f"\nСреднее расстояние до оптимальной позиции: {stats['avg_distance_to_optimal']:.1f}px")
            print(f"Максимальное: {stats['max_distance_to_optimal']:.1f}px")
            print(f"Минимальное: {stats['min_distance_to_optimal']:.1f}px")
        
        if 'avg_target_difference' in stats:
            print(f"\nСредняя разница между optimal_x и saved_target: {stats['avg_target_difference']:.1f}px")
            print(f"Максимальная: {stats['max_target_difference']:.1f}px")
    
    if 'patterns' in analysis and 'zones' in analysis['patterns']:
        print("\n--- РАСПРЕДЕЛЕНИЕ ПО ЗОНАМ ---")
        for zone, count in analysis['patterns']['zones'].items():
            print(f"{zone}: {count}")
    
    if 'issues' in analysis and analysis['issues']:
        print("\n--- ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ ---")
        issue_types = defaultdict(list)
        for issue in analysis['issues']:
            issue_types[issue['type']].append(issue)
        
        for issue_type, issues in issue_types.items():
            print(f"\n{issue_type} ({len(issues)} случаев):")
            for issue in issues[:5]:  # Показываем первые 5
                print(f"  - {issue['description']}")
            if len(issues) > 5:
                print(f"  ... и еще {len(issues) - 5} случаев")
    else:
        print("\n--- ПРОБЛЕМЫ НЕ ВЫЯВЛЕНЫ ---")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Пример использования
    log_text = """
    [BALL LOST] ========== ДИАГНОСТИКА ПОТЕРИ МЯЧА ==========
      Мяч: pos=(728.0, 533.0) bottom=541.0 vel=(8.0, 8.0) speed=8.0
      Платформа: center_x=365.0 top=540.0 left=305.0 right=425.0
      Расстояние: horizontal=363.0px vertical=1.0px
      Мяч относительно платформы: RIGHT (справа от платформы) (offset=363.0px)
      Мяч ударился о платформу: False (если False - мяч пролетел мимо)
      Целевая позиция AI: optimal_x=710.0 distance_to_optimal=345.0px
      🔴 ПРЕДСКАЗАНИЕ: Предсказанная позиция приземления: 742.0px
      🔴 ПРЕДСКАЗАНИЕ: Фактическая позиция мяча: 728.0px
      🔴 ПРЕДСКАЗАНИЕ: Ошибка предсказания: 14.0px
      🔴 ПРЕДСКАЗАНИЕ: Мяч пролетел мимо на: 363.0px от центра платформы
      Скорость платформы: base=45 adjusted=45
      Зоны: separation_start=226 paddle_start=540 ball_was_in_zone=True
      Целевая позиция установлена: True
      Сохраненная целевая позиция: 375.0 distance=10.0px
      Жизни: 3
    ========================================================
    """
    
    losses = parse_ball_loss_log(log_text)
    analysis = analyze_losses(losses)
    print_analysis(analysis)
