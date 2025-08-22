# 🚀 Guía de Despliegue - BTG Pactual Inversiones

## 📋 Resumen del Proyecto

Aplicación de microservicios para gestión de fondos de inversión con:
- **Auth Service**: Autenticación y gestión de usuarios
- **Funds Service**: Gestión de fondos y transacciones
- **Notification Service**: Sistema de notificaciones

## 🏗️ Arquitectura AWS

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Route53 DNS   │    │   CloudWatch    │    │   ECR Registry  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                    │
│                         (ALB)                                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ECS Cluster (Fargate)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Auth Service│  │Funds Service│  │Notification │            │
│  │   :8002     │  │   :8003     │  │   :8001     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VPC + Subnets                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Public Sub  │  │ Private Sub │  │ Security    │            │
│  │   (ALB)     │  │   (ECS)     │  │   Groups    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MongoDB Atlas                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Users     │  │   Funds     │  │Transactions │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Prerrequisitos

### 1. Herramientas Instaladas
```bash
# AWS CLI
aws --version

# Terraform
terraform --version

# Docker
docker --version

# Python 3.8+
python --version
```

### 2. Configuración AWS
```bash
# Configurar credenciales AWS
aws configure
# Access Key ID: [TU_ACCESS_KEY]
# Secret Access Key: [TU_SECRET_KEY]
# Region: us-east-1
# Output format: json
```

### 3. Variables de Entorno
Crear archivo `.env` en el directorio `terraform/`:
```bash
export TF_VAR_mongodb_atlas_connection_string="mongodb+srv://btg_admin:bgt_pactual_2025@cluster0.qjzcu.mongodb.net/"
export TF_VAR_jwt_secret_key="tu_jwt_secret_super_seguro_2025"
export TF_VAR_sendgrid_api_key="tu_sendgrid_api_key"
export TF_VAR_twilio_account_sid="tu_twilio_account_sid"
export TF_VAR_twilio_auth_token="tu_twilio_auth_token"
export TF_VAR_email_from="noreply@btg-pactual.com"
```

## 🚀 Pasos de Despliegue

### Paso 1: Preparar el Entorno
```bash
# Navegar al directorio del proyecto
cd "C:\Repos\test\BTG Inversiones\BTG-pactual-inversiones"

# Cargar variables de entorno
source terraform/.env  # Linux/Mac
# O ejecutar: terraform\setup-env.ps1  # Windows
```

### Paso 2: Inicializar Terraform
```bash
cd terraform

# Inicializar Terraform
terraform init

# Verificar configuración
terraform plan
```

### Paso 3: Crear Infraestructura Base
```bash
# Aplicar configuración base (sin servicios ECS)
terraform apply -auto-approve
```

### Paso 4: Preparar Imágenes Docker
```bash
# Autenticarse con ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 249867185796.dkr.ecr.us-east-1.amazonaws.com

# Etiquetar imágenes existentes
docker tag btg-pactual-inversiones-auth-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-auth-service:latest
docker tag btg-pactual-inversiones-funds-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-funds-service:latest
docker tag btg-pactual-inversiones-notification-service:latest 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-notification-service:latest

# Subir imágenes a ECR
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-auth-service:latest
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-funds-service:latest
docker push 249867185796.dkr.ecr.us-east-1.amazonaws.com/btg-pactual-production-notification-service:latest
```

### Paso 5: Inicializar MongoDB Atlas
```bash
# Ejecutar script de inicialización
cd ..
python scripts/init-mongodb.py
```

### Paso 6: Desplegar Servicios ECS
```bash
cd terraform

# Opción A: Usar script automatizado
.\deploy-services.ps1

# Opción B: Comandos manuales
terraform apply -target="aws_ecs_service.auth_service" -auto-approve
terraform apply -target="aws_ecs_service.funds_service" -auto-approve
terraform apply -target="aws_ecs_service.notification_service" -auto-approve
```

## 🌐 URLs de Acceso

Una vez desplegado, los servicios estarán disponibles en:

```
Load Balancer Principal:
http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com

Servicios:
- Auth Service: http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/auth/
- Funds Service: http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/funds/
- Notifications: http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/notifications/
```

## 🔧 Comandos de Verificación

### Verificar Estado de Infraestructura
```bash
# Estado de Terraform
terraform state list

# Outputs
terraform output

# Verificar servicios ECS
aws ecs list-services --cluster btg-pactual-production-cluster --region us-east-1

# Verificar Load Balancer
aws elbv2 describe-load-balancers --names btg-pactual-production-alb --region us-east-1
```

### Verificar Servicios
```bash
# Health Check
curl -X GET "http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/health"

# Auth Service
curl -X GET "http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/auth/health"

# Funds Service
curl -X GET "http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/funds/health"

# Notifications Service
curl -X GET "http://btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com/notifications/health"
```

### Verificar Logs
```bash
# Logs de Auth Service
aws logs describe-log-groups --log-group-name-prefix "/ecs/btg-pactual-production-auth-service" --region us-east-1

# Ver logs en tiempo real
aws logs tail "/ecs/btg-pactual-production-auth-service" --follow --region us-east-1
```

## 📊 Recursos Creados

### AWS Resources
- **VPC**: `vpc-0c44f6bc0912d5364`
- **Load Balancer**: `btg-pactual-production-alb-376975977.us-east-1.elb.amazonaws.com`
- **ECS Cluster**: `btg-pactual-production-cluster`
- **ECR Repositories**: 3 repositorios para los microservicios
- **Security Groups**: Para ALB, ECS y EC2
- **IAM Roles**: Para ejecución y tareas de ECS
- **CloudWatch Log Groups**: Para logging de servicios

### MongoDB Atlas
- **Database**: `btg_pactual`
- **Collections**: `users`, `funds`, `transactions`, `user_subscriptions`, `notifications`
- **Datos Iniciales**: 5 fondos de inversión
- **Usuario Admin**: `admin@btg-pactual.com` / `admin123`

## 🧹 Limpieza (Destruir Infraestructura)

```bash
# Destruir toda la infraestructura
terraform destroy -auto-approve

# Verificar que se eliminó todo
terraform state list
```

## ⚠️ Notas Importantes

1. **Certificado SSL**: No se configuró SSL porque requiere dominio real
2. **Costo**: Los recursos AWS generan costos mensuales
3. **Seguridad**: Las credenciales están en variables de entorno
4. **Escalabilidad**: Los servicios están configurados para escalar automáticamente

## 🆘 Solución de Problemas

### Error: "S3 bucket does not exist"
```bash
# Crear bucket manualmente
aws s3 mb s3://btg-pactual-terraform-state --region us-east-1
aws s3api put-bucket-versioning --bucket btg-pactual-terraform-state --versioning-configuration Status=Enabled
```

### Error: "Access Denied"
```bash
# Verificar permisos IAM
aws iam get-user
aws sts get-caller-identity
```

### Error: "Certificate validation failed"
```bash
# Para pruebas, usar HTTP en lugar de HTTPS
# O configurar dominio real en Route53
```

### Servicios no responden
```bash
# Verificar estado de tareas ECS
aws ecs describe-tasks --cluster btg-pactual-production-cluster --region us-east-1

# Verificar logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/" --region us-east-1
```

## 📞 Contacto

Para soporte técnico o preguntas sobre el despliegue, contactar al equipo de desarrollo.
