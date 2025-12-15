#!/bin/bash
# Скрипт для запуска игры в многопоточном режиме (Linux/Mac)
# Использование: ./run_with_multithreading.sh

echo "Запуск игры в многопоточном режиме..."
echo "Количество потоков: 2"
echo ""

export AI_USE_ASYNC_TRAJECTORY=true
export AI_ASYNC_MAX_WORKERS=2

cd "$(dirname "$0")"
python game/PyGameBall.py







