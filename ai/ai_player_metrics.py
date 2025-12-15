"""
Модуль для вывода и сохранения метрик AI системы.

Содержит методы для вывода метрик ML системы, сохранения сессий и сравнения прогресса обучения.
"""

from typing import Any, Dict


class AIPlayerMetricsMixin:
    """
    Миксин для методов вывода и сохранения метрик.
    Добавляет методы для анализа и логирования метрик производительности AI.
    """

    def _print_ml_system_metrics(self, success: bool, final_score: int) -> None:
        """
        Выводит метрики оценки работы системы scikit-learn в лог.
        
        Args:
            success: True, если игра выиграна.
            final_score: Итоговый счёт игры.
        """
        try:
            self._logger.info("\n" + "=" * 70)
            self._logger.info("МЕТРИКИ ОЦЕНКИ РАБОТЫ СИСТЕМЫ AI (scikit-learn)")
            self._logger.info("=" * 70)
            
            # Базовые метрики игры
            self._logger.info(f"\n[РЕЗУЛЬТАТЫ] Результаты игры:")
            result_text = "[+] ПОБЕДА" if success else "[-] ПОРАЖЕНИЕ"
            self._logger.info(f"   Результат: {result_text}")
            self._logger.info(f"   Финальный счёт: {final_score}")
            self._logger.info(f"   Всего игр: {self.performance_metrics['games_played']}")
            self._logger.info(f"   Побед: {self.performance_metrics['games_won']}")
            if self.performance_metrics["games_played"] > 0:
                win_rate = (
                    self.performance_metrics["games_won"]
                    / self.performance_metrics["games_played"]
                ) * 100
                self._logger.info(f"   Процент побед: {win_rate:.1f}%")
            
            # Метрики текущей игры
            self._logger.info(f"\n[МЕТРИКИ] Метрики текущей игры:")
            self._logger.info(
                f"   Уничтожено кубиков: {self.current_game_stats['bricks_destroyed']}"
            )
            self._logger.info(
                f"   Всего предсказаний: {self.current_game_stats['total_predictions']}"
            )
            if self.current_game_stats["total_predictions"] > 0:
                prediction_accuracy = (
                    self.current_game_stats["successful_predictions"]
                    / self.current_game_stats["total_predictions"]
                ) * 100
                self._logger.info(f"   Точность предсказаний: {prediction_accuracy:.1f}%")
            self._logger.info(f"   Всего ходов: {self.current_game_stats['total_moves']}")
            if self.current_game_stats["total_moves"] > 0:
                optimal_move_rate = (
                    self.current_game_stats["optimal_moves"]
                    / self.current_game_stats["total_moves"]
                ) * 100
                self._logger.info(f"   Оптимальных ходов: {optimal_move_rate:.1f}%")
            
            # Метрики обучения и scikit-learn
            learning_progress = self.learning_system.get_learning_progress()
            
            if (
                isinstance(learning_progress, dict)
                and learning_progress.get("total_iterations", 0) > 0
            ):
                self._logger.info(f"\n[ОБУЧЕНИЕ] Система обучения (scikit-learn):")
                self._logger.info(
                    f"   Всего итераций обучения: {learning_progress.get('total_iterations', 0)}"
                )
                self._logger.info(
                    f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                )
                self._logger.info(
                    f"   Средний прогресс: {learning_progress.get('average_improvement', 0.0):.2%}"
                )
                
                # Кластеризация траекторий (KMeans)
                self._logger.info(f"\n[КЛАСТЕРИЗАЦИЯ] Кластеризация траекторий (KMeans):")
                trajectory_clusters = self.learning_system.cluster_trajectories()
                unique_clusters = learning_progress.get("trajectory_clusters_count", 0)
                cluster_diversity = learning_progress.get("cluster_diversity", 0.0)
                trajectory_patterns = learning_progress.get("trajectory_patterns", 0)
                
                self._logger.info(f"   Найдено паттернов траекторий: {trajectory_patterns}")
                self._logger.info(f"   Количество кластеров: {unique_clusters}")
                self._logger.info(f"   Разнообразие кластеров: {cluster_diversity:.3f}")
                
                if trajectory_clusters:
                    # Анализ распределения по кластерам
                    cluster_counts: Dict[int, int] = {}
                    for item in trajectory_clusters:
                        cluster_id = item.get("cluster", -1)
                        cluster_counts[cluster_id] = (
                            cluster_counts.get(cluster_id, 0) + 1
                        )
                    
                    self._logger.info(f"   Распределение по кластерам:")
                    for cluster_id, count in sorted(cluster_counts.items()):
                        percentage = (count / len(trajectory_clusters)) * 100
                        self._logger.info(
                            f"      Кластер {cluster_id}: {count} паттернов ({percentage:.1f}%)"
                        )
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для кластеризации")
                
                # Модель предсказания успеха (RandomForestClassifier)
                self._logger.info(f"\n[МОДЕЛЬ] Модель предсказания успеха (RandomForestClassifier):")
                model = self.learning_system.learning_data.get(
                    "success_prediction_model"
                )
                model_metrics = self.learning_system.learning_data.get(
                    "model_metrics", {}
                )
                
                if model is not None:
                    self._logger.info(f"   [+] Модель обучена и готова к использованию")
                    
                    # Показываем метрики модели
                    model_accuracy = model_metrics.get("last_accuracy")
                    if model_accuracy is not None:
                        self._logger.info(f"   Точность модели (accuracy): {model_accuracy:.2%}")
                    
                    training_samples = model_metrics.get("training_samples", 0)
                    test_samples = model_metrics.get("test_samples", 0)
                    features_count = model_metrics.get("features_count", 0)
                    
                    if training_samples > 0:
                        self._logger.info(f"   Образцов для обучения: {training_samples}")
                        self._logger.info(f"   Образцов для тестирования: {test_samples}")
                        self._logger.info(f"   Количество признаков: {features_count}")
                    
                    # Получаем информацию о факторах успеха
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        self._logger.info(f"   Факторы успеха:")
                        for factor_name, factor_data in success_factors.items():
                            total = factor_data.get("total_cases", 0)
                            successful = factor_data.get("successful_cases", 0)
                            if total > 0:
                                success_rate = (successful / total) * 100
                                self._logger.info(
                                    f"      {factor_name}: {successful}/{total} успешных ({success_rate:.1f}%)"
                                )
                else:
                    self._logger.info(
                        f"   [ВНИМАНИЕ]  Модель ещё не обучена (требуется минимум 100 итераций)"
                    )
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        total_cases = sum(
                            f.get("total_cases", 0) for f in success_factors.values()
                        )
                        self._logger.info(f"   Накоплено данных: {total_cases} случаев")
                        iterations_needed = max(
                            0,
                            100 - (learning_progress.get("total_iterations", 0) % 100),
                        )
                        self._logger.info(
                            f"   До следующего обучения: {iterations_needed} итераций"
                        )
                
                # Веса стратегий
                strategy_weights = learning_progress.get("strategy_weights", {})
                if strategy_weights:
                    self._logger.info(f"\n[ВЕСА]  Веса стратегий:")
                    for strategy, weight in strategy_weights.items():
                        bar_length = int(weight * 20)
                        bar = "█" * bar_length + "░" * (20 - bar_length)
                        self._logger.info(f"   {strategy:12s}: {bar} {weight:.3f}")
                
            else:
                self._logger.info(f"\n[ВНИМАНИЕ]  Система обучения ещё не накопила достаточно данных")
                self._logger.info(
                    f"   Продолжайте играть для активации кластеризации и предсказания"
                )
            
            # Общая оценка системы
            self._logger.info(f"\n[ОЦЕНКА] Общая оценка системы:")
            if isinstance(learning_progress, dict):
                avg_accuracy = self.performance_metrics.get("average_accuracy", 0.0)
                learning_prog = self.performance_metrics.get("learning_progress", 0.0)
                
                # Комплексная оценка
                if learning_progress.get("total_iterations", 0) > 0:
                    # Базовые компоненты оценки
                    prediction_accuracy_weight = 0.3
                    learning_progress_weight = 0.25
                    success_rate_weight = 0.25
                    model_accuracy_weight = 0.2
                    
                    system_score = (
                        avg_accuracy * prediction_accuracy_weight
                        + learning_prog * learning_progress_weight
                        + (learning_progress.get("success_rate", 0.0))
                        * success_rate_weight
                    ) * 100
                    
                    # Добавляем оценку модели предсказания, если она обучена
                    model_accuracy = learning_progress.get("prediction_model_accuracy")
                    if model_accuracy is not None:
                        system_score += model_accuracy * model_accuracy_weight * 100
                        self._logger.info(f"   Точность ML модели: {model_accuracy:.2%}")
                    else:
                        # Если модель не обучена, перераспределяем веса
                        adjusted_weight = (
                            prediction_accuracy_weight
                            + learning_progress_weight
                            + success_rate_weight
                        )
                        system_score = (
                            system_score / (1 - model_accuracy_weight) * adjusted_weight
                        )
                    
                    self._logger.info(f"   Средняя точность предсказаний: {avg_accuracy:.2%}")
                    self._logger.info(f"   Прогресс обучения: {learning_prog:.2%}")
                    self._logger.info(
                        f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                    )
                    self._logger.info(f"   Комплексная оценка системы: {system_score:.1f}/100")
                    
                    if system_score >= 80:
                        self._logger.info(f"   [ОТЛИЧНО] Система работает эффективно")
                    elif system_score >= 60:
                        self._logger.info(f"   [ХОРОШО] Система работает стабильно")
                    elif system_score >= 40:
                        self._logger.info(f"   [УДОВЛЕТВОРИТЕЛЬНО] Система обучается")
                    else:
                        self._logger.info(f"   [ТРЕБУЕТ УЛУЧШЕНИЯ] Недостаточно данных")
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для комплексной оценки")
            
            self._logger.info("=" * 70 + "\n")
        except (AttributeError, TypeError, KeyError) as e:
            # В случае ошибки выводим минимальную информацию
            try:
                self._logger.error(f"\n[ОШИБКА] Ошибка типов при выводе метрик: {e}\n", exc_info=True)
            except (UnicodeError, ValueError) as e2:
                # Если даже это не работает, выводим без форматирования
                self._logger.error(f"\n[ОШИБКА] Ошибка при выводе метрик: {e}\n", exc_info=True)
                self._logger.error(f"[ОШИБКА] Дополнительная ошибка: {e2}\n", exc_info=True)
        except (UnicodeError, ValueError) as e:
            # Ошибка форматирования/кодировки
            self._logger.error(f"\n[ОШИБКА] Ошибка форматирования при выводе метрик: {e}\n", exc_info=True)

    def _save_session_metrics(self, success: bool, final_score: int) -> None:
        """
        Сохраняет агрегированные метрики по завершённой игре в список сессий.
        """
        session_data = {
            "session_id": self.session_counter,
            "success": success,
            "final_score": final_score,
            "average_accuracy": self.performance_metrics["average_accuracy"],
            "learning_progress": self.performance_metrics["learning_progress"],
            "bricks_destroyed": self.current_game_stats["bricks_destroyed"],
            "total_moves": self.current_game_stats["total_moves"],
            "optimal_moves": self.current_game_stats["optimal_moves"],
        }

        self.session_metrics.append(session_data)
        self.session_counter += 1

        # Опционально: можно печатать прогресс каждые N игр
        if self.session_counter % 10 == 0:
            self._print_learning_progress_comparison()

    def _print_learning_progress_comparison(self) -> None:
        """
        Печатает краткий обзор прогресса обучения по последним сессиям.
        Никакой логики игры не меняет, только вывод/анализ.
        """
        if not self.session_metrics:
            return

        last_sessions = self.session_metrics[-10:]
        avg_score = sum(s["final_score"] for s in last_sessions) / len(last_sessions)
        avg_accuracy = sum(s["average_accuracy"] for s in last_sessions) / len(
            last_sessions
        )
        avg_learning = sum(s["learning_progress"] for s in last_sessions) / len(
            last_sessions
        )

        # Логируем статистику последних игр
        self._logger.info(
            f"[AI] Последние {len(last_sessions)} игр: "
            f"средний счёт={avg_score:.1f}, "
            f"точность={avg_accuracy:.2f}, "
            f"прогресс обучения={avg_learning:.2f}"
        )
