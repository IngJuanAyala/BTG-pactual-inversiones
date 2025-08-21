# Script para detener el entorno de desarrollo BTG Pactual

Write-Host "🛑 Deteniendo entorno de desarrollo..." -ForegroundColor Yellow

# Detener todos los contenedores
docker-compose down

Write-Host "✅ Entorno de desarrollo detenido!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Para iniciar nuevamente ejecuta: .\dev-start.ps1" -ForegroundColor Cyan
