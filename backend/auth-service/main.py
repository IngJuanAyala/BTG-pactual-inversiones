"""
Servicio de Autenticación - BTG Pactual
"""
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import structlog
from pydantic import EmailStr
from bson import ObjectId

from shared.config import settings
from shared.database import db_manager, get_database, Collections
from shared.models import (
    User, UserCreateRequest, UserUpdateRequest, UserRole, NotificationType
)
from shared.auth import (
    AuthService, Token, TokenData, get_current_active_user,
    check_rate_limit, require_role, require_any_role
)


# Configuración de logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Inicio
    logger.info("🚀 Iniciando servicio de autenticación...")
    
    # Conectar a la base de datos
    await db_manager.connect()
    
    logger.info("✅ Servicio de autenticación iniciado correctamente")
    
    yield
    
    # Cierre
    logger.info("🔄 Cerrando servicio de autenticación...")
    await db_manager.disconnect()
    logger.info("✅ Servicio de autenticación cerrado")


# Crear aplicación FastAPI
app = FastAPI(
    title="BTG Pactual - Servicio de Autenticación",
    description="API para autenticación y gestión de usuarios",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/auth/docs",
    redoc_url="/auth/redoc",
    openapi_url="/auth/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para logging
@app.middleware("http")
async def log_requests(request, call_next):
    """Log de requests"""
    start_time = asyncio.get_event_loop().time()
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    
    logger.info(
        "Request procesada",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
    logger.error(
        "Error no manejado",
        error=str(exc),
        url=str(request.url),
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Manejador de excepciones HTTP"""
    logger.warning(
        "Error HTTP",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Endpoints de salud
@app.get("/health")
async def health_check():
    """Verificar salud del servicio"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": settings.app_version,
        "hot_reload": "✅ Funcionando correctamente!"
    }


@app.get("/auth/health")
async def auth_health_check():
    """Verificar salud del servicio (ruta con prefijo auth)"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": settings.app_version,
        "hot_reload": "✅ Funcionando correctamente!"
    }


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "BTG Pactual - Servicio de Autenticación",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "/auth/register",
            "/auth/login",
            "/auth/me",
            "/auth/refresh"
        ]
    }


@app.get("/auth/")
async def auth_root():
    """Endpoint raíz del auth service"""
    return {
        "message": "BTG Pactual - Servicio de Autenticación",
        "version": settings.app_version,
        "docs": "/auth/docs",
        "health": "/auth/health",
        "endpoints": [
            "/auth/register",
            "/auth/login",
            "/auth/me",
            "/auth/refresh"
        ]
    }


# Endpoints de autenticación
@app.post("/auth/register", response_model=Token)
async def register_user(
    user_data: UserCreateRequest
):
    """Registrar nuevo usuario"""
    try:
        db = await get_database()
        
        # Verificar que el email no esté registrado
        existing_user = await db[Collections.USERS].find_one({"email": user_data.email})
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # PLANTEAMIENTO PARA HASH DE CONTRASEÑA:
        # 
        # 1. Importar las librerías necesarias para hashear la contraseña
        #    from passlib.context import CryptContext
        #    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # 
        # 2. Hashear la contraseña antes de guardarla
        #    password_hash = pwd_context.hash(user_data.password)
        # 
        # 3. Crear el usuario con la contraseña hasheada
        #    new_user = User(
        #        email=user_data.email,
        #        first_name=user_data.first_name,
        #        last_name=user_data.last_name,
        #        phone=user_data.phone,
        #        password_hash=password_hash,  # Guardar el hash, no la contraseña en texto plano
        #        notification_preference=user_data.notification_preference,
        #        role=UserRole.CLIENT,
        #        balance=settings.initial_balance
        #    )
        # 
        # Por simplicidad en esta prueba técnica, simulamos el hash:
        password_hash = f"hashed_{user_data.password}_for_demo"
        
        # Crear nuevo usuario
        new_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            password_hash=password_hash,  # Guardar el hash de la contraseña
            notification_preference=user_data.notification_preference,
            role=UserRole.CLIENT,  # Por defecto es cliente
            balance=settings.initial_balance
        )
        
        # Insertar usuario en la base de datos
        user_dict = new_user.dict()
        
        result = await db[Collections.USERS].insert_one(user_dict)
        new_user.id = result.inserted_id
        
        # Generar tokens
        tokens = AuthService.create_tokens(new_user)
        
        logger.info(
            "Usuario registrado exitosamente",
            user_id=str(new_user.id),
            email=user_data.email
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error registrando usuario", email=user_data.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registrando usuario"
        )


@app.post("/auth/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Iniciar sesión de usuario"""
    try:
        db = await get_database()
        
        # Buscar usuario por email
        user = await db[Collections.USERS].find_one({"email": form_data.username})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Verificar que el usuario esté activo
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # Verificación básica de contraseña
        # En un entorno de producción, esto debería usar hashing real
        stored_password = user.get("password_hash", "")
        logger.info(f"Debug - stored_password: {stored_password}")
        logger.info(f"Debug - form_data.password: {form_data.password}")
        
        if not stored_password:
            # Si no hay contraseña hasheada, verificar contra la contraseña original
            # (esto es solo para desarrollo/demo)
            logger.info("Debug - No hay password_hash, verificando contra Password123")
            if form_data.password != "Password123":  # Contraseña por defecto para demo
                logger.info("Debug - Contraseña incorrecta, lanzando error 401")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
            else:
                logger.info("Debug - Contraseña correcta")
        else:
            # Aquí iría la verificación real con passlib
            # from passlib.context import CryptContext
            # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # if not pwd_context.verify(form_data.password, stored_password):
            #     raise HTTPException(
            #         status_code=status.HTTP_401_UNAUTHORIZED,
            #         detail="Credenciales inválidas"
            #     )
            logger.info("Debug - Hay password_hash, verificando contraseña")
            # Verificación temporal para demo
            if stored_password != f"hashed_{form_data.password}_for_demo":
                logger.info("Debug - Contraseña incorrecta (con hash), lanzando error 401")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
            else:
                logger.info("Debug - Contraseña correcta (con hash)")
        
        # 3. Verificar que la contraseña no haya expirado (si aplica)
        #    password_updated_at = user.get("password_updated_at")
        #    if password_updated_at and (datetime.utcnow() - password_updated_at).days > 90:
        #        raise HTTPException(
        #            status_code=status.HTTP_401_UNAUTHORIZED,
        #            detail="Contraseña expirada, debe cambiarla"
        #        )
        # 
        # 4. Registrar intento de login (para auditoría)
        #    await log_login_attempt(user["_id"], success=True, ip_address=request.client.host)
        # 
        # 5. Implementar rate limiting para prevenir ataques de fuerza bruta
        #    if await is_rate_limited(user["email"]):
        #        raise HTTPException(
        #            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        #            detail="Demasiados intentos de login, intente más tarde"
        #        )
        
        # Crear objeto User para generar tokens
        user_obj = User(
            id=str(user["_id"]),  # Convertir ObjectId a string
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user.get("phone"),
            role=UserRole(user["role"]),
            balance=user["balance"],
            notification_preference=NotificationType(user["notification_preference"])
        )
        
        # Generar tokens
        tokens = AuthService.create_tokens(user_obj)
        
        logger.info(
            "Usuario autenticado exitosamente",
            user_id=str(user["_id"]),
            email=user["email"]
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en login", email=form_data.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en autenticación"
        )


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Refrescar token de acceso"""
    try:
        # Verificar token de refresco
        token_data = AuthService.verify_token(refresh_token)
        
        if token_data.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido"
            )
        
        # Obtener usuario actualizado
        db = await get_database()
        user = await db[Collections.USERS].find_one({"id": current_user.user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Crear objeto User para generar tokens
        user_obj = User(
            id=str(user["_id"]),  # Convertir ObjectId a string
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user.get("phone"),
            role=UserRole(user["role"]),
            balance=user["balance"],
            notification_preference=NotificationType(user["notification_preference"])
        )
        
        # Generar nuevos tokens
        tokens = AuthService.create_tokens(user_obj)
        
        logger.info(
            "Token refrescado exitosamente",
            user_id=current_user.user_id
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error refrescando token", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refrescando token"
        )


@app.post("/auth/logout")
async def logout_user(
    current_user: TokenData = Depends(get_current_active_user)
):
    """Cerrar sesión de usuario"""
    try:
        # En un sistema real, aquí invalidarías el token
        # Por simplicidad, solo registramos el logout
        
        logger.info(
            "Usuario cerró sesión",
            user_id=current_user.user_id,
            email=current_user.email
        )
        
        return {"message": "Sesión cerrada exitosamente"}
        
    except Exception as e:
        logger.error("Error en logout", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cerrando sesión"
        )


# Endpoints de gestión de usuarios
@app.get("/users/me")
async def get_current_user_info(
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener información del usuario actual"""
    try:
        db = await get_database()
        
        logger.info(f"Debug - Buscando usuario con user_id: {current_user.user_id}")
        
        # Convertir string a ObjectId y buscar por _id
        try:
            object_id = ObjectId(current_user.user_id)
            user = await db[Collections.USERS].find_one({"_id": object_id})
        except Exception as e:
            logger.error(f"Debug - Error convirtiendo a ObjectId: {e}")
            user = None
        
        logger.info(f"Debug - Usuario encontrado: {user is not None}")
        
        if not user:
            # Intentar buscar por id personalizado también para debug
            logger.info(f"Debug - Intentando buscar por id personalizado: {current_user.user_id}")
            user_by_id = await db[Collections.USERS].find_one({"id": current_user.user_id})
            logger.info(f"Debug - Usuario encontrado por id personalizado: {user_by_id is not None}")
            
            # Listar todos los usuarios para debug
            all_users = await db[Collections.USERS].find().to_list(length=10)
            logger.info(f"Debug - Total usuarios en BD: {len(all_users)}")
            for u in all_users:
                logger.info(f"Debug - Usuario en BD: id={u.get('id')}, _id={u.get('_id')}, email={u.get('email')}")
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone": user.get("phone"),
            "role": user["role"],
            "balance": str(user["balance"]),
            "notification_preference": user["notification_preference"],
            "is_active": user.get("is_active", True),
            "created_at": str(user["created_at"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo usuario", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo información del usuario"
        )


@app.put("/users/me")
async def update_current_user(
    user_data: UserUpdateRequest,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Actualizar información del usuario actual"""
    try:
        db = await get_database()
        
        # Preparar datos a actualizar
        update_data = {}
        
        if user_data.first_name is not None:
            update_data["first_name"] = user_data.first_name
        if user_data.last_name is not None:
            update_data["last_name"] = user_data.last_name
        if user_data.phone is not None:
            update_data["phone"] = user_data.phone
        if user_data.notification_preference is not None:
            update_data["notification_preference"] = user_data.notification_preference.value
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay datos para actualizar"
            )
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Actualizar usuario
        try:
            object_id = ObjectId(current_user.user_id)
            result = await db[Collections.USERS].update_one(
                {"_id": object_id},  # Usar ObjectId
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"Error convirtiendo user_id a ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        logger.info(
            "Usuario actualizado",
            user_id=current_user.user_id,
            updated_fields=list(update_data.keys())
        )
        
        return {"message": "Usuario actualizado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando usuario", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando usuario"
        )


# Endpoints administrativos
@app.get("/users", response_model=List[dict])
async def get_all_users(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """Obtener todos los usuarios (solo administradores)"""
    try:
        db = await get_database()
        
        cursor = db[Collections.USERS].find({})
        users = await cursor.to_list(length=None)
        
        return [
            {
                "id": str(user["_id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone": user.get("phone"),
                "role": user["role"],
                "balance": str(user["balance"]),
                "notification_preference": user["notification_preference"],
                "is_active": user.get("is_active", True),
                "created_at": str(user["created_at"])
            }
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo usuarios", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo usuarios"
        )


@app.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: TokenData = Depends(require_any_role([UserRole.ADMIN, UserRole.ADVISOR]))
):
    """Obtener usuario por ID (solo administradores y asesores)"""
    try:
        db = await get_database()
        
        user = await db[Collections.USERS].find_one({"id": user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone": user.get("phone"),
            "role": user["role"],
            "balance": str(user["balance"]),
            "notification_preference": user["notification_preference"],
            "is_active": user.get("is_active", True),
            "created_at": str(user["created_at"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo usuario", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo usuario"
        )


@app.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """Actualizar rol de usuario (solo administradores)"""
    try:
        db = await get_database()
        
        # Verificar que el usuario existe
        user = await db[Collections.USERS].find_one({"id": user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar rol
        result = await db[Collections.USERS].update_one(
            {"id": user_id},
            {"$set": {"role": new_role.value, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar el rol"
            )
        
        logger.info(
            "Rol de usuario actualizado",
            user_id=user_id,
            new_role=new_role.value,
            updated_by=current_user.user_id
        )
        
        return {"message": f"Rol actualizado a {new_role.value}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando rol", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando rol"
        )


@app.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """Actualizar estado de usuario (solo administradores)"""
    try:
        db = await get_database()
        
        # Verificar que el usuario existe
        user = await db[Collections.USERS].find_one({"id": user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar estado
        result = await db[Collections.USERS].update_one(
            {"id": user_id},
            {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar el estado"
            )
        
        status_text = "activado" if is_active else "desactivado"
        
        logger.info(
            "Estado de usuario actualizado",
            user_id=user_id,
            new_status=is_active,
            updated_by=current_user.user_id
        )
        
        return {"message": f"Usuario {status_text} exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando estado", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando estado"
        )


# Endpoint para verificar token
@app.get("/auth/verify")
async def verify_token(
    current_user: TokenData = Depends(get_current_active_user)
):
    """Verificar que el token es válido"""
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
