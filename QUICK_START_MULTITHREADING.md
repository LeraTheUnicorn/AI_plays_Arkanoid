# Быстрый старт: Многопоточный режим

## 🚀 Самый простой способ

### Windows
Просто запустите:
```bash
run_with_multithreading.bat
```

### Linux/Mac
```bash
chmod +x run_with_multithreading.sh
./run_with_multithreading.sh
```

## ⚙️ Ручная настройка

### Вариант 1: Через переменные окружения

**Windows (PowerShell):**
```powershell
$env:AI_USE_ASYNC_TRAJECTORY="true"
$env:AI_ASYNC_MAX_WORKERS="2"
python game/PyGameBall.py
```

**Windows (CMD):**
```cmd
set AI_USE_ASYNC_TRAJECTORY=true
set AI_ASYNC_MAX_WORKERS=2
python game/PyGameBall.py
```

**Linux/Mac:**
```bash
AI_USE_ASYNC_TRAJECTORY=true AI_ASYNC_MAX_WORKERS=2 python game/PyGameBall.py
```

### Вариант 2: Изменить код напрямую

Откройте `game/PyGameBall.py` и найдите строки:
```python
USE_ASYNC_TRAJECTORY = os.getenv("AI_USE_ASYNC_TRAJECTORY", "false").lower() == "true"
ASYNC_MAX_WORKERS = int(os.getenv("AI_ASYNC_MAX_WORKERS", "2"))
```

Измените на:
```python
USE_ASYNC_TRAJECTORY = True   # Включить многопоточность
ASYNC_MAX_WORKERS = 2          # Количество потоков
```

## 📊 Рекомендации по количеству потоков

- **1 поток**: Минимальная нагрузка
- **2 потока** ⭐ (рекомендуется): Оптимальный баланс
- **3-4 потока**: Для мощных систем
- **>4 потока**: Обычно избыточно

## ✅ Проверка работы

После запуска проверьте:
1. Игра работает плавно без задержек
2. В диспетчере задач видно использование нескольких ядер CPU
3. Нет ошибок в логах

## 🔧 Отключение

Чтобы отключить многопоточность:
- Удалите переменные окружения, или
- Установите `USE_ASYNC_TRAJECTORY = False` в коде

## 📖 Подробная документация

См. `MULTITHREADING_GUIDE.md` для полной документации.

