# 🚀 Configuración de Infraestructura AWS con Terraform

Configuración completa de infraestructura como código para desplegar la aplicación BTG Pactual en AWS.

## 📋 Prerrequisitos

- **AWS CLI** configurado con credenciales
- **Terraform** instalado (versión >= 1.0)
- **Docker** instalado
- **Git** instalado

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Route53 DNS   │    │   ALB (HTTP)    │    │   ECS Cluster   │
│                 │    │                 │    │                 │
│ auth.btg-...    │───▶│   Target Groups │───▶│ Auth Service    │
│ funds.btg-...   │    │                 │    │ Funds Service   │
│ notif.btg-...   │    │                 │    │ Notif Service   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   VPC/Subnets   │
                       │   Security      │
                       │   Groups        │
                       └─────────────────┘
```

## 🔧 Configuración Inicial

### 1. Configurar AWS CLI

```bash
aws configure
```

Ingresa tus credenciales:

- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

### 2. Crear archivo de variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars` con tus valores reales:

- MongoDB Atlas connection string
- JWT secret key
- SendGrid API key
- Twilio credentials
- Email configuration

### 3. Inicializar Terraform

```bash
cd terraform
terraform init
```

### 4. Verificar el plan

```bash
terraform plan
```

### 5. Aplicar la configuración

```bash
terraform apply
```

## 🐳 Despliegue de Imágenes Docker

### 1. Autenticarse con ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 249867185796.dkr.ecr.us-east-1.amazonaws.com
```

### 2. Construir y etiquetar imágenes

```bash
# Auth Service
docker build -t btg-pactual-production-auth-service:latest backend/
docker tag btg-pactual-production-auth-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-auth-service:latest

# Funds Service
docker build -t btg-pactual-production-funds-service:latest backend/
docker tag btg-pactual-production-funds-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-funds-service:latest

# Notification Service
docker build -t btg-pactual-production-notification-service:latest backend/
docker tag btg-pactual-production-notification-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-notification-service:latest
```

### 3. Subir imágenes a ECR

```bash
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-auth-service:latest
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-funds-service:latest
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-notification-service:latest
```

## 🗄️ Configurar MongoDB Atlas

### 1. Ejecutar script de inicialización

```bash
cd scripts
python init-mongodb.py
```

Este script:

- Crea las colecciones necesarias
- Define índices
- Inserta datos iniciales
- Crea usuario administrador

## 🔄 Actualizar Servicios ECS

### 1. Forzar nuevo deployment

```bash
aws ecs update-service --cluster btg-pactual-production --service auth-service --force-new-deployment
aws ecs update-service --cluster btg-pactual-production --service funds-service --force-new-deployment
aws ecs update-service --cluster btg-pactual-production --service notification-service --force-new-deployment
```

### 2. Verificar estado de servicios

```bash
aws ecs describe-services --cluster btg-pactual-production --services auth-service funds-service notification-service
```

## 🌐 URLs de Acceso

Una vez desplegado:

- **ALB Principal**: `http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com`
- **Auth Service**: `/auth/*`
- **Funds Service**: `/funds/*`
- **Notification Service**: `/notifications/*`

### URLs de Swagger/OpenAPI:

- **Auth Service**: `http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/auth/docs`
- **Funds Service**: `http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/funds/docs`
- **Notification Service**: `http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/notifications/docs`

## 📁 Estructura de Archivos

```
terraform/
├── main.tf              # Configuración principal (VPC, subnets, security groups)
├── loadbalancer.tf      # Application Load Balancer y target groups
├── ecs.tf              # ECS cluster, task definitions y servicios
├── iam.tf              # Roles y políticas IAM
├── database.tf         # Configuración de base de datos
├── ssl.tf              # Certificados SSL (comentado para pruebas)
├── terraform.tfvars.example  # Ejemplo de variables
└── README.md           # Este archivo
```

## 🔒 Seguridad

**NUNCA** subir a Git:

- `terraform.tfvars` - Contiene valores reales
- `*.tfvars` - Archivos con credenciales
- `.terraform/` - Estado local
- `terraform.tfstate` - Estado de Terraform

## 🧹 Limpieza

Para destruir toda la infraestructura:

```bash
terraform destroy
```

**⚠️ ADVERTENCIA**: Esto eliminará todos los recursos creados.

## 📝 Notas Importantes

1. **SSL**: Configurado para HTTP únicamente (para pruebas técnicas)
2. **Dominio**: Usa URLs del ALB directamente
3. **Base de datos**: MongoDB Atlas externo
4. **Logs**: CloudWatch Logs habilitados
5. **Monitoreo**: Health checks configurados

## 🔍 Verificación

### Verificar servicios ECS:

```bash
aws ecs list-services --cluster btg-pactual-production
```

### Verificar logs:

```bash
aws logs describe-log-groups --log-group-name-prefix "/ecs/btg-pactual-production"
```

### Probar endpoints:

```bash
curl http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/auth/health
curl http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/funds/health
curl http://btg-pactual-production-alb-xxx.us-east-1.elb.amazonaws.com/notifications/health
```
