# MongoDB Atlas (Gratis) - Configuración externa
# No creamos recursos aquí, solo outputs para la conexión

# Outputs para MongoDB Atlas
output "mongodb_connection_string" {
  description = "Connection string de MongoDB Atlas"
  value       = var.mongodb_atlas_connection_string
  sensitive   = true
}

# Nota: MongoDB Atlas se configura manualmente en https://cloud.mongodb.com
# 1. Crear cuenta gratuita
# 2. Crear cluster gratuito (M0 - 512MB)
# 3. Crear usuario de base de datos
# 4. Obtener connection string
# 5. Agregar IP 0.0.0.0/0 para acceso desde cualquier lugar (solo para pruebas)

# Redis se ejecutará localmente en los contenedores para ahorrar costos
output "redis_info" {
  description = "Información de Redis local"
  value       = "Redis ejecutándose localmente en cada contenedor para ahorrar costos"
}
