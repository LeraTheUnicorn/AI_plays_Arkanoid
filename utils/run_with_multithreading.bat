@echo off
REM Скрипт для запуска игры в многопоточном режиме
REM Использование: run_with_multithreading.bat

echo Запуск игры в многопоточном режиме...
echo Количество потоков: 2
echo.
echo Примечание: Многопоточность теперь включена по умолчанию.
echo Для отключения установите: set AI_USE_ASYNC_TRAJECTORY=false
echo.

set AI_USE_ASYNC_TRAJECTORY=true
set AI_ASYNC_MAX_WORKERS=2

cd /d "%~dp0"
python game\PyGameBall.py

pause
