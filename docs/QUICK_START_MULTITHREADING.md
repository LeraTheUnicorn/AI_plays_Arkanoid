# Быстрый старт: Многопоточный режим

## ✅ Многопоточность включена по умолчанию!

**Многопоточный режим теперь включен по умолчанию** для лучшей производительности. 
Просто запустите игру обычным способом:
```bash
python game/PyGameBall.py
```

## 🚀 Дополнительные скрипты (опционально)

### Windows
Для явного указания настроек:
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

Многопоточность уже включена по умолчанию в `game/game_utils.py`:
```python
USE_ASYNC_TRAJECTORY = os.getenv("AI_USE_ASYNC_TRAJECTORY", "true").lower() == "true"
ASYNC_MAX_WORKERS = int(os.getenv("AI_ASYNC_MAX_WORKERS", "2"))
```

Для отключения многопоточности установите переменную окружения:
```bash
# Windows
set AI_USE_ASYNC_TRAJECTORY=false
python game/PyGameBall.py

# Linux/Mac
AI_USE_ASYNC_TRAJECTORY=false python game/PyGameBall.py
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

## 🔧 Отключение многопоточности

Чтобы отключить многопоточность (если возникают проблемы):
- Удалите переменные окружения, или
- Установите `USE_ASYNC_TRAJECTORY = False` в коде

## 📖 Подробная документация

См. `MULTITHREADING_GUIDE.md` для полной документации.

