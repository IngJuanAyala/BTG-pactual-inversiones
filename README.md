# BTG Pactual - Plataforma de Gestión de Fondos

## Descripción del Proyecto

Plataforma web para gestión de fondos de inversión que permite a los clientes de BTG Pactual suscribirse, cancelar suscripciones y consultar historial de transacciones sin necesidad de contacto directo con asesores.

## Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Load Balancer │
│   (React/Vue)   │◄──►│   (AWS)         │◄──►│   (AWS ALB)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Microservicios                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Auth      │  │   Funds     │  │ Transaction │  │ Notify  │ │
│  │   Service   │  │   Service   │  │   Service   │  │ Service │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infraestructura AWS                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   MongoDB   │  │   SQS/SNS   │  │   Cognito   │  │ CloudWatch│ │
│  │   Atlas     │  │   (Events)  │  │   (Auth)    │  │ (Monitoring)│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Justificación de la Arquitectura

#### **¿Por qué Microservicios?**

1. **Escalabilidad Independiente**: Cada servicio puede escalar según su demanda específica
2. **Desarrollo Paralelo**: Equipos pueden trabajar en diferentes servicios simultáneamente
3. **Tecnología Específica**: Cada servicio puede usar la tecnología más apropiada
4. **Fault Isolation**: Fallos en un servicio no afectan al sistema completo
5. **Despliegue Continuo**: Actualizaciones independientes sin downtime

#### **¿Por qué FastAPI + Python?**

1. **Rendimiento**: Comparable a Node.js y Go
2. **Documentación Automática**: OpenAPI/Swagger integrado
3. **Validación Automática**: Pydantic para validación de datos
4. **Async/Await**: Soporte nativo para operaciones asíncronas

#### **¿Por qué MongoDB?**

1. **Flexibilidad**: Esquema flexible para diferentes tipos de fondos
2. **Geodistribución**: Replicación global con MongoDB Atlas

#### **¿Por qué AWS?**

1. **Servicios Gestionados**: Menos overhead operacional
2. **Escalabilidad Automática**: Auto-scaling basado en demanda
3. **Integración Nativa**: Servicios que se integran perfectamente
4. **Costos Optimizados**: Pay-per-use y reservas

## Estructura del Proyecto

```
btg-pactual-inversiones/
├── backend/
│   ├── auth-service/
│   ├── funds-service/
│   ├── transaction-service/
│   ├── notification-service/
│   └── shared/
├── infrastructure/
│   ├── terraform/
│   └── docker/
├── frontend/
├── docs/
├── tests/
└── postman/
```

## Funcionalidades Implementadas

### 1. Gestión de Fondos
- ✅ Suscripción a fondos
- ✅ Cancelación de suscripciones
- ✅ Consulta de fondos disponibles
- ✅ Validación de montos mínimos

### 2. Gestión de Transacciones
- ✅ Historial de transacciones
- ✅ Identificadores únicos
- ✅ Validación de saldo
- ✅ Rollback automático

### 3. Notificaciones
- ✅ Email automático
- ✅ SMS (opcional)
- ✅ Preferencias de usuario
- ✅ Templates personalizados

### 4. Seguridad
- ✅ Autenticación JWT
- ✅ Autorización por roles
- ✅ Encriptación de datos sensibles
- ✅ Rate limiting
- ✅ Validación de entrada

## Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **Pydantic**: Validación de datos
- **MongoDB**: Base de datos NoSQL
- **Redis**: Cache y sesiones

### Infraestructura
- **AWS ECS**: Contenedores
- **AWS RDS**: Base de datos
- **AWS SQS/SNS**: Mensajería
- **AWS Cognito**: Autenticación
- **Terraform**: Infraestructura como código

### Monitoreo
- **AWS CloudWatch**: Logs y métricas
- **Sentry**: Error tracking
- **Prometheus**: Métricas personalizadas

## Instalación y Despliegue

### Requisitos Previos
- Python 3.9+
- Docker
- Terraform
- AWS CLI

### Instalación Local
```bash
# Clonar repositorio
git clone <repository-url>
cd btg-pactual-inversiones

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar servicios
docker-compose up -d
```

### Despliegue en AWS
```bash
# Configurar AWS credentials
aws configure

# Desplegar infraestructura
cd infrastructure/terraform
terraform init
terraform plan
terraform apply

# Desplegar aplicaciones
./deploy.sh
```

## API Documentation

La documentación completa de la API está disponible en:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Testing

```bash
# Ejecutar tests unitarios
pytest

# Ejecutar tests de integración
pytest tests/integration/

# Ejecutar tests de carga
locust -f tests/load/locustfile.py
```

## Licencia

IngJuanAyala. Todos los derechos reservados.
