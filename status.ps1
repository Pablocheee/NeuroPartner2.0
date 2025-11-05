# status.ps1 - Проверка статуса приложения

$RENDER_URL = "https://ai-education-platform-mh01.onrender.com"

Write-Host "🔍 Checking application status..." -ForegroundColor Cyan

# Проверка health endpoint
try {
    $health = Invoke-RestMethod -Uri "$RENDER_URL/health" -ErrorAction Stop
    Write-Host "✅ Health: $($health.status)" -ForegroundColor Green
    Write-Host "🤖 AI Provider: $($health.ai)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Проверка main endpoint
try {
    $main = Invoke-RestMethod -Uri "$RENDER_URL/" -ErrorAction Stop
    Write-Host "✅ Main endpoint: $($main.status)" -ForegroundColor Green
    Write-Host "📊 Version: $($main.version)" -ForegroundColor Green
} catch {
    Write-Host "❌ Main endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Проверка webhook (если установлен токен)
if ($env:TELEGRAM_TOKEN) {
    try {
        $webhookInfo = Invoke-RestMethod -Uri "https://api.telegram.org/bot$($env:TELEGRAM_TOKEN)/getWebhookInfo" -ErrorAction Stop
        Write-Host "✅ Webhook URL: $($webhookInfo.result.url)" -ForegroundColor Green
        Write-Host "📱 Pending updates: $($webhookInfo.result.pending_update_count)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Webhook check failed" -ForegroundColor Red
    }
}

Write-Host "---" -ForegroundColor Gray
Write-Host "Application URL: $RENDER_URL" -ForegroundColor Cyan
