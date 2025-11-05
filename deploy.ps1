# deploy.ps1 - Скрипт для быстрого деплоя

param(
    [string]$CommitMessage = "Update: 2025-11-05 16:39"
)

Write-Host "🚀 Starting deployment..." -ForegroundColor Cyan

# Шаг 1: Git операции
Write-Host "1. Committing changes..." -ForegroundColor Yellow
git add .
git commit -m "$CommitMessage"
git push origin main

Write-Host "2. Changes pushed to GitHub. Render will auto-deploy..." -ForegroundColor Green

# Шаг 2: Ожидание деплоя (опционально)
Write-Host "3. Waiting 30 seconds for deploy to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Шаг 3: Проверка статуса
$RENDER_URL = "https://ai-education-platform-mh01.onrender.com"
try {
    $health = Invoke-RestMethod -Uri "$RENDER_URL/health" -ErrorAction Stop
    Write-Host "✅ Deploy successful! Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Deploy check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "🎉 Deployment process completed!" -ForegroundColor Cyan
