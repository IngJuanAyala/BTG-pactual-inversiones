# Script de desarrollo para BTG Pactual
# Inicia todos los servicios con hot-reload

Write-Host "🚀 Iniciando entorno de desarrollo BTG Pactual..." -ForegroundColor Green

# Detener contenedores existentes
Write-Host "🛑 Deteniendo contenedores existentes..." -ForegroundColor Yellow
docker-compose down

# Iniciar servicios
Write-Host "🔧 Iniciando servicios..." -ForegroundColor Yellow
docker-compose up -d mongodb redis

# Esperar a que MongoDB esté listo
Write-Host "⏳ Esperando a que MongoDB esté listo..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Iniciar servicios de aplicación
Write-Host "📱 Iniciando servicios de aplicación..." -ForegroundColor Yellow
docker-compose up -d auth-service funds-service notification-service

# Iniciar nginx
Write-Host "🌐 Iniciando API Gateway..." -ForegroundColor Yellow
docker-compose up -d nginx

# Mostrar estado
Write-Host "✅ Entorno de desarrollo iniciado!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Servicios disponibles:" -ForegroundColor Cyan
Write-Host "  • Auth Service: http://localhost:8002" -ForegroundColor White
Write-Host "  • Funds Service: http://localhost:8000" -ForegroundColor White
Write-Host "  • Notification Service: http://localhost:8001" -ForegroundColor White
Write-Host "  • API Gateway: http://localhost:8080" -ForegroundColor White
Write-Host "  • MongoDB: localhost:27017" -ForegroundColor White
Write-Host "  • Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Para ver logs en tiempo real:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f auth-service" -ForegroundColor Gray
Write-Host ""
Write-Host "🛠️  Para debugging:" -ForegroundColor Yellow
Write-Host "  Puerto 5678 disponible para debugpy" -ForegroundColor Gray
Write-Host ""
Write-Host "🔄 Los cambios en el código se reflejarán automáticamente!" -ForegroundColor Green
