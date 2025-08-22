# CONFIGURACIÓN DE POSTMAN PARA BTG PACTUAL

## 🔧 CONFIGURACIÓN BÁSICA

### 1. Variables de Entorno

Crear las siguientes variables en Postman:

```
notification_base_url: http://localhost:8001
auth_base_url: http://localhost:8002
funds_base_url: http://localhost:8000
api_gateway_url: http://localhost:8080
```

### 2. Configuración SSL/TLS

- **Settings** → **General** → **SSL certificate verification**: **OFF**
- **Settings** → **General** → **Request timeout**: **5000ms**

### 3. Headers por defecto

```
Content-Type: application/json
Accept: application/json
```

## 🚀 ENDPOINTS DE PRUEBA

### Health Checks

```
GET {{notification_base_url}}/health
GET {{auth_base_url}}/health
GET {{funds_base_url}}/health
GET {{api_gateway_url}}/health
```

### Configuración de Notificaciones

```
GET {{notification_base_url}}/config/validate
GET {{notification_base_url}}/config/env-vars
```

### Autenticación

```
POST {{auth_base_url}}/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "Password123",
  "first_name": "Usuario",
  "last_name": "Prueba",
  "phone": "+573001234567",
  "notification_preference": "email"
}
```

### Login (para obtener token)

```
POST {{auth_base_url}}/auth/login
Content-Type: application/x-www-form-urlencoded

username=test@example.com&password=Password123
```

### Fondos

```
GET {{funds_base_url}}/funds
```

### Notificaciones

```
GET {{notification_base_url}}/notifications/user/test
```

### Notificaciones de Fondos (CORREGIDO)

```
POST {{notification_base_url}}/notifications/fund-subscription
Content-Type: application/json
Authorization: Bearer {{access_token}}

{
  "user_id": "{{user_id}}",
  "fund_name": "FPV_BTG_PACTUAL_RECAUDADORA",
  "amount": 100000
}
```

```
POST {{notification_base_url}}/notifications/fund-cancellation
Content-Type: application/json
Authorization: Bearer {{access_token}}

{
  "user_id": "{{user_id}}",
  "fund_name": "FPV_BTG_PACTUAL_RECAUDADORA",
  "amount": 100000
}
```

## 🔐 FLUJO COMPLETO DE AUTENTICACIÓN

### Paso 1: Registrar Usuario

```bash
curl -X POST "http://localhost:8002/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123",
    "first_name": "Usuario",
    "last_name": "Prueba",
    "phone": "+573001234567",
    "notification_preference": "email"
  }'
```

### Paso 2: Obtener Token de Login

```bash
curl -X POST "http://localhost:8002/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Password123"
```

### Paso 3: Extraer user_id del Token

El `user_id` está en el campo `sub` del JWT token. Puedes decodificarlo en:

- https://jwt.io/
- O usar herramientas de línea de comandos

**Ejemplo de token decodificado:**

```json
{
  "sub": "68a7b49b0a3f442c4fbe49fe",
  "email": "test@example.com",
  "role": "client",
  "exp": 1755823048
}
```

### Paso 4: Usar el user_id en Notificaciones

```bash
curl -X POST "http://localhost:8001/notifications/fund-subscription" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token>" \
  -d '{
    "user_id": "68a7b49b0a3f442c4fbe49fe",
    "fund_name": "FPV_BTG_PACTUAL_RECAUDADORA",
    "amount": 100000
  }'
```

## ⚠️ SOLUCIÓN AL ERROR SSL

Si sigues viendo el error `WRONG_VERSION_NUMBER`:

1. **Verificar URL**: Asegúrate de usar `http://` NO `https://`
2. **Limpiar caché**: Postman → Settings → General → Clear cache
3. **Reiniciar Postman**
4. **Usar curl como alternativa**:

```bash
# Health check
curl -X GET "http://localhost:8001/health"

# Configuración
curl -X GET "http://localhost:8001/config/validate"

# Variables de entorno
curl -X GET "http://localhost:8001/config/env-vars"

# Fund subscription (requiere autenticación)
curl -X POST "http://localhost:8001/notifications/fund-subscription" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token>" \
  -d '{
    "user_id": "68a7b49b0a3f442c4fbe49fe",
    "fund_name": "FPV_BTG_PACTUAL_RECAUDADORA",
    "amount": 100000
  }'
```

## 📚 DOCUMENTACIÓN SWAGGER

Acceder directamente en el navegador:

- **Auth Service**: http://localhost:8002/docs
- **Funds Service**: http://localhost:8000/docs
- **Notification Service**: http://localhost:8001/docs

## 🔐 AUTENTICACIÓN

**Nota importante**: Los endpoints de notificaciones requieren autenticación. Para probarlos:

1. **Primero registrar un usuario** usando `/auth/register`
2. **Obtener un token** usando `/auth/login` (con formato x-www-form-urlencoded)
3. **Extraer el user_id** del token JWT (campo `sub`)
4. **Incluir el token** en el header `Authorization: Bearer <token>`
5. **Usar el user_id** en el body de la petición

## 📋 VARIABLES DE POSTMAN

Configura estas variables en Postman:

```
access_token: <token_del_login>
user_id: <sub_del_token_jwt>
```
