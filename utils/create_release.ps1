# PowerShell скрипт для подготовки GitHub Release
# Использование: .\create_release.ps1 -Version "v2.3.161" -Branch "develop"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$Branch = "develop",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTag,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateArchive
)

Write-Host "🚀 Подготовка GitHub Release $Version" -ForegroundColor Cyan
Write-Host ""

# Проверка рабочего дерева
Write-Host "📋 Проверка состояния репозитория..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  ВНИМАНИЕ: Обнаружены незакоммиченные изменения:" -ForegroundColor Red
    Write-Host $status
    $continue = Read-Host "Продолжить? (y/n)"
    if ($continue -ne "y") {
        Write-Host "❌ Отменено пользователем" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Рабочее дерево чистое" -ForegroundColor Green
}

# Получение текущей ветки
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "📍 Текущая ветка: $currentBranch" -ForegroundColor Cyan

# Переключение на целевую ветку (если нужно)
if ($currentBranch -ne $Branch) {
    Write-Host "🔄 Переключение на ветку $Branch..." -ForegroundColor Yellow
    git checkout $Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка переключения на ветку $Branch" -ForegroundColor Red
        exit 1
    }
}

# Обновление из удаленного репозитория
Write-Host "📥 Обновление из удаленного репозитория..." -ForegroundColor Yellow
git fetch origin
git pull origin $Branch
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка обновления из удаленного репозитория" -ForegroundColor Red
    exit 1
}

# Проверка существования тега
$tagExists = git tag -l $Version
if ($tagExists) {
    Write-Host "⚠️  Тег $Version уже существует" -ForegroundColor Yellow
    $continue = Read-Host "Создать новый тег или использовать существующий? (new/existing/skip)"
    if ($continue -eq "skip") {
        $SkipTag = $true
    } elseif ($continue -ne "existing") {
        git tag -d $Version 2>$null
        git push origin :refs/tags/$Version 2>$null
    }
}

# Создание тега
if (-not $SkipTag) {
    Write-Host "🏷️  Создание тега $Version..." -ForegroundColor Yellow
    $tagMessage = "Release $Version"
    $tagInput = Read-Host "Сообщение для тега (Enter для '$tagMessage')"
    if ($tagInput) {
        $tagMessage = $tagInput
    }
    
    git tag -a $Version -m $tagMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка создания тега" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "📤 Отправка тега в удаленный репозиторий..." -ForegroundColor Yellow
    git push origin $Version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка отправки тега" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Тег $Version успешно создан и отправлен" -ForegroundColor Green
} else {
    Write-Host "⏭️  Пропуск создания тега" -ForegroundColor Yellow
}

# Создание архива исходного кода
if ($CreateArchive) {
    Write-Host "📦 Создание архива исходного кода..." -ForegroundColor Yellow
    $archiveName = "AI_plays_Arkanoid-$Version-source.zip"
    git archive --format=zip --output=$archiveName HEAD
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Архив создан: $archiveName" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Не удалось создать архив" -ForegroundColor Yellow
    }
}

# Получение информации для Release Notes
Write-Host ""
Write-Host "📝 Информация для Release Notes:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Последние коммиты
Write-Host "`n📌 Последние 10 коммитов:" -ForegroundColor Yellow
git log --oneline -10

# Статистика изменений
Write-Host "`n📊 Статистика изменений (с последнего тега):" -ForegroundColor Yellow
$lastTag = git describe --tags --abbrev=0 2>$null
if ($lastTag) {
    Write-Host "Сравнение с последним тегом: $lastTag"
    git log --oneline $lastTag..HEAD
    git diff --stat $lastTag..HEAD
} else {
    Write-Host "Предыдущие теги не найдены"
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Инструкции для следующего шага
Write-Host "✅ Подготовка завершена!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Перейдите на страницу релизов:" -ForegroundColor White
Write-Host "   https://github.com/LeraTheUnicorn/AI_plays_Arkanoid/releases/new" -ForegroundColor Blue
Write-Host ""
Write-Host "2. Выберите тег: $Version" -ForegroundColor White
Write-Host "3. Выберите ветку: $Branch" -ForegroundColor White
Write-Host "4. Заполните Release Notes (используйте информацию выше)" -ForegroundColor White
Write-Host "5. Нажмите 'Publish release'" -ForegroundColor White
Write-Host ""
Write-Host "Или используйте GitHub CLI:" -ForegroundColor Yellow
Write-Host "   gh release create $Version --title 'Release $Version' --target $Branch" -ForegroundColor Blue

