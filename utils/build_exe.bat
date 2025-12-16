@echo off
REM Скрипт для сборки exe файла игры Arkanoid
REM Использование: build_exe.bat

REM Устанавливаем кодировку UTF-8 для корректного отображения русских символов
chcp 65001 >nul 2>&1

REM Переходим в корневую директорию проекта (где находится spec файл)
cd /d "%~dp0.."

echo ========================================
echo Сборка Arkanoid в EXE файл
echo ========================================
echo.

REM Проверка наличия spec файла
if not exist arkanoid.spec (
    echo [ОШИБКА] Файл arkanoid.spec не найден!
    echo Убедитесь, что вы запускаете скрипт из корня проекта.
    pause
    exit /b 1
)

REM Проверка наличия PyInstaller
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller не установлен!
    echo Устанавливаю PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo [ШАГ 1/3] Очистка предыдущих сборок...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo Готово!

echo.
echo [ШАГ 2/3] Сборка exe файла...
echo Это может занять несколько минут...
echo.

REM Запускаем PyInstaller с spec файлом
python -m PyInstaller arkanoid.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась!
    echo Проверьте сообщения об ошибках выше.
    pause
    exit /b 1
)

echo.
echo [ШАГ 3/3] Проверка результата...
if exist dist\Arkanoid.exe (
    echo.
    echo ========================================
    echo [УСПЕХ] Сборка завершена успешно!
    echo ========================================
    echo.
    echo EXE файл находится в: dist\Arkanoid.exe
    echo Размер файла:
    dir dist\Arkanoid.exe | find "Arkanoid.exe"
    echo.
    echo Вы можете запустить игру двойным кликом по файлу dist\Arkanoid.exe
    echo.
) else (
    echo.
    echo [ОШИБКА] EXE файл не найден в папке dist!
    pause
    exit /b 1
)

echo Нажмите любую клавишу для выхода...
pause >nul

