#!/bin/bash
# Bash скрипт для подготовки GitHub Release
# Использование: ./create_release.sh v2.3.161 develop

set -e

VERSION="${1:-}"
BRANCH="${2:-develop}"
SKIP_TAG=false
CREATE_ARCHIVE=false

# Проверка аргументов
if [ -z "$VERSION" ]; then
    echo "❌ Ошибка: Укажите версию"
    echo "Использование: $0 <version> [branch]"
    echo "Пример: $0 v2.3.161 develop"
    exit 1
fi

echo "🚀 Подготовка GitHub Release $VERSION"
echo ""

# Проверка рабочего дерева
echo "📋 Проверка состояния репозитория..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  ВНИМАНИЕ: Обнаружены незакоммиченные изменения:"
    git status --short
    read -p "Продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Отменено пользователем"
        exit 1
    fi
else
    echo "✅ Рабочее дерево чистое"
fi

# Получение текущей ветки
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Текущая ветка: $CURRENT_BRANCH"

# Переключение на целевую ветку (если нужно)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "🔄 Переключение на ветку $BRANCH..."
    git checkout "$BRANCH"
fi

# Обновление из удаленного репозитория
echo "📥 Обновление из удаленного репозитория..."
git fetch origin
git pull origin "$BRANCH"

# Проверка существования тега
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "⚠️  Тег $VERSION уже существует"
    read -p "Создать новый тег, использовать существующий или пропустить? (new/existing/skip) " choice
    case "$choice" in
        skip) SKIP_TAG=true ;;
        new)
            git tag -d "$VERSION" 2>/dev/null || true
            git push origin ":refs/tags/$VERSION" 2>/dev/null || true
            ;;
        existing) SKIP_TAG=false ;;
    esac
fi

# Создание тега
if [ "$SKIP_TAG" = false ]; then
    echo "🏷️  Создание тега $VERSION..."
    read -p "Сообщение для тега (Enter для 'Release $VERSION'): " TAG_MESSAGE
    TAG_MESSAGE="${TAG_MESSAGE:-Release $VERSION}"
    
    git tag -a "$VERSION" -m "$TAG_MESSAGE"
    
    echo "📤 Отправка тега в удаленный репозиторий..."
    git push origin "$VERSION"
    
    echo "✅ Тег $VERSION успешно создан и отправлен"
else
    echo "⏭️  Пропуск создания тега"
fi

# Создание архива исходного кода
if [ "$CREATE_ARCHIVE" = true ]; then
    echo "📦 Создание архива исходного кода..."
    ARCHIVE_NAME="AI_plays_Arkanoid-$VERSION-source.tar.gz"
    git archive --format=tar.gz --output="$ARCHIVE_NAME" HEAD
    if [ $? -eq 0 ]; then
        echo "✅ Архив создан: $ARCHIVE_NAME"
    else
        echo "⚠️  Не удалось создать архив"
    fi
fi

# Получение информации для Release Notes
echo ""
echo "📝 Информация для Release Notes:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Последние коммиты
echo ""
echo "📌 Последние 10 коммитов:"
git log --oneline -10

# Статистика изменений
echo ""
echo "📊 Статистика изменений (с последнего тега):"
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    echo "Сравнение с последним тегом: $LAST_TAG"
    git log --oneline "$LAST_TAG..HEAD"
    git diff --stat "$LAST_TAG..HEAD"
else
    echo "Предыдущие теги не найдены"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Инструкции для следующего шага
echo "✅ Подготовка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Перейдите на страницу релизов:"
echo "   https://github.com/LeraTheUnicorn/AI_plays_Arkanoid/releases/new"
echo ""
echo "2. Выберите тег: $VERSION"
echo "3. Выберите ветку: $BRANCH"
echo "4. Заполните Release Notes (используйте информацию выше)"
echo "5. Нажмите 'Publish release'"
echo ""
echo "Или используйте GitHub CLI:"
echo "   gh release create $VERSION --title 'Release $VERSION' --target $BRANCH"

