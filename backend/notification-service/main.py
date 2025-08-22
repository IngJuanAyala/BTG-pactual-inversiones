"""
Servicio de Notificaciones - BTG Pactual
"""
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime
import os

from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from shared.config import settings
from shared.database import db_manager, get_database, Collections
from shared.models import (
    Notification, NotificationResponse, NotificationType,
    UserCreateRequest, UserUpdateRequest
)
from shared.auth import get_current_active_user, TokenData, check_rate_limit
from bson import ObjectId


# Configuración de logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Inicio
    logger.info("🚀 Iniciando servicio de notificaciones...")
    
    # Conectar a la base de datos
    await db_manager.connect()
    
    logger.info("✅ Servicio de notificaciones iniciado correctamente")
    
    yield
    
    # Cierre
    logger.info("🔄 Cerrando servicio de notificaciones...")
    await db_manager.disconnect()
    logger.info("✅ Servicio de notificaciones cerrado")


# Crear aplicación FastAPI
app = FastAPI(
    title="BTG Pactual - Servicio de Notificaciones",
    description="API para gestión de notificaciones",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/notifications/docs",
    redoc_url="/notifications/redoc",
    openapi_url="/notifications/openapi.json"
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
        "service": "notification-service",
        "version": settings.app_version
    }


@app.get("/config/validate")
async def validate_configuration():
    """Validar configuración de notificaciones"""
    config_status = {
        "sendgrid": {
            "configured": bool(settings.sendgrid_api_key),
            "api_key_length": len(settings.sendgrid_api_key) if settings.sendgrid_api_key else 0,
            "status": "✅ Configurado" if settings.sendgrid_api_key else "❌ No configurado"
        },
        "twilio": {
            "configured": bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_phone_number),
            "account_sid": bool(settings.twilio_account_sid),
            "auth_token": bool(settings.twilio_auth_token),
            "phone_number": settings.twilio_phone_number,
            "status": "✅ Configurado" if all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_phone_number]) else "❌ No configurado"
        },
        "smtp": {
            "configured": bool(settings.smtp_username and settings.smtp_password),
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "use_tls": settings.smtp_use_tls,
            "status": "✅ Configurado" if settings.smtp_username and settings.smtp_password else "❌ No configurado"
        },
        "environment": {
            "env": os.getenv("ENVIRONMENT", "development"),
            "debug": settings.debug,
            "log_level": settings.log_level
        }
    }
    
    return {
        "message": "Validación de configuración",
        "timestamp": datetime.utcnow().isoformat(),
        "config": config_status
    }


@app.get("/config/env-vars")
async def show_environment_variables():
    """Mostrar variables de entorno cargadas"""
    env_vars = {
        "mongodb_url": settings.mongodb_url,
        "redis_url": settings.redis_url,
        "jwt_secret_key": settings.jwt_secret_key[:10] + "..." if settings.jwt_secret_key else None,
        "sendgrid_api_key": settings.sendgrid_api_key[:10] + "..." if settings.sendgrid_api_key else None,
        "twilio_account_sid": settings.twilio_account_sid[:10] + "..." if settings.twilio_account_sid else None,
        "twilio_auth_token": settings.twilio_auth_token[:10] + "..." if settings.twilio_auth_token else None,
        "twilio_phone_number": settings.twilio_phone_number,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username,
        "smtp_password": "***" if settings.smtp_password else None,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": settings.debug,
        "log_level": settings.log_level
    }
    
    return {
        "message": "Variables de entorno cargadas",
        "timestamp": datetime.utcnow().isoformat(),
        "environment_variables": env_vars
    }


# Clase para manejo de notificaciones
class NotificationService:
    """Servicio de notificaciones"""
    
    @staticmethod
    async def send_email_notification(
        to_email: str,
        subject: str,
        message: str
    ) -> bool:
        """Enviar notificación por email"""
        try:
            if settings.sendgrid_api_key:
                # Usar SendGrid
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail
                
                sg = SendGridAPIClient(api_key=settings.sendgrid_api_key)
                mail = Mail(
                    from_email=settings.from_email,
                    to_emails=to_email,
                    subject=subject,
                    html_content=message
                )
                
                response = sg.send(mail)
                logger.info(
                    "Email enviado via SendGrid",
                    to_email=to_email,
                    status_code=response.status_code
                )
                return response.status_code == 202
                
            elif settings.smtp_username and settings.smtp_password:
                # Usar SMTP
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart()
                msg['From'] = settings.smtp_username
                msg['To'] = to_email
                msg['Subject'] = subject
                
                msg.attach(MIMEText(message, 'html'))
                
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
                if settings.smtp_use_tls:
                    server.starttls()
                
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
                server.quit()
                
                logger.info("Email enviado via SMTP", to_email=to_email)
                return True
                
            else:
                logger.warning("No hay configuración de email disponible")
                return False
                
        except Exception as e:
            logger.error("Error enviando email", to_email=to_email, error=str(e))
            return False
    
    @staticmethod
    async def send_sms_notification(
        to_phone: str,
        message: str
    ) -> bool:
        """Enviar notificación por SMS"""
        try:
            if settings.twilio_account_sid and settings.twilio_auth_token:
                from twilio.rest import Client
                
                client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                
                message = client.messages.create(
                    body=message,
                    from_=settings.twilio_phone_number,
                    to=to_phone
                )
                
                logger.info("SMS enviado via Twilio", to_phone=to_phone, sid=message.sid)
                return True
                
            else:
                logger.warning("No hay configuración de SMS disponible")
                return False
                
        except Exception as e:
            logger.error("Error enviando SMS", to_phone=to_phone, error=str(e))
            return False
    
    @staticmethod
    async def create_notification(
        user_id: str,
        notification_type: NotificationType,
        subject: str,
        message: str
    ) -> Notification:
        """Crear notificación en la base de datos"""
        try:
            db = await get_database()
            
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                subject=subject,
                message=message,
                status="pending"
            )
            
            result = await db[Collections.NOTIFICATIONS].insert_one(notification.dict())
            notification.id = result.inserted_id
            
            logger.info(
                "Notificación creada",
                notification_id=str(notification.id),
                user_id=user_id,
                type=notification_type.value
            )
            
            return notification
            
        except Exception as e:
            logger.error("Error creando notificación", error=str(e))
            raise
    
    @staticmethod
    async def send_notification(
        user_id: str,
        notification_type: NotificationType,
        subject: str,
        message: str
    ) -> bool:
        """Enviar notificación completa"""
        try:
            # Obtener información del usuario
            db = await get_database()
            user = await db[Collections.USERS].find_one({"_id": ObjectId(user_id)})
            
            if not user:
                logger.error("Usuario no encontrado para notificación", user_id=user_id)
                return False
            
            # Crear notificación en BD
            notification = await NotificationService.create_notification(
                user_id, notification_type, subject, message
            )
            
            # Enviar según preferencia del usuario
            success = False
            
            if notification_type == NotificationType.EMAIL:
                success = await NotificationService.send_email_notification(
                    user["email"], subject, message
                )
            elif notification_type == NotificationType.SMS and user.get("phone"):
                success = await NotificationService.send_sms_notification(
                    user["phone"], message
                )
            
            # Actualizar estado de la notificación
            await db[Collections.NOTIFICATIONS].update_one(
                {"_id": notification.id},
                {
                    "$set": {
                        "status": "sent" if success else "failed",
                        "sent_at": datetime.utcnow() if success else None
                    }
                }
            )
            
            return success
            
        except Exception as e:
            logger.error("Error enviando notificación", user_id=user_id, error=str(e))
            return False


# Endpoints de notificaciones
@app.post("/notifications/send")
async def send_notification(
    user_id: str,
    notification_type: NotificationType,
    subject: str,
    message: str,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Enviar notificación"""
    try:
        # Ejecutar en background para no bloquear la respuesta
        background_tasks.add_task(
            NotificationService.send_notification,
            user_id, notification_type, subject, message
        )
        
        return {
            "message": "Notificación programada para envío",
            "user_id": user_id,
            "type": notification_type.value
        }
        
    except Exception as e:
        logger.error("Error programando notificación", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error programando notificación"
        )


@app.get("/notifications/user/{user_id}", response_model=List[NotificationResponse])
async def get_user_notifications(
    user_id: str,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener notificaciones de un usuario"""
    try:
        db = await get_database()
        
        # Verificar que el usuario puede ver sus notificaciones
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede ver notificaciones de otros usuarios"
            )
        
        cursor = db[Collections.NOTIFICATIONS].find(
            {"user_id": user_id}
        ).sort("created_at", -1)
        
        notifications = await cursor.to_list(length=None)
        
        return [
            NotificationResponse(
                id=str(notif["_id"]),
                type=notif["type"],
                subject=notif["subject"],
                message=notif["message"],
                status=notif["status"],
                created_at=str(notif["created_at"])
            )
            for notif in notifications
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo notificaciones", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo notificaciones"
        )


@app.get("/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener detalles de una notificación específica"""
    try:
        db = await get_database()
        
        notification = await db[Collections.NOTIFICATIONS].find_one({"_id": notification_id})
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación no encontrada"
            )
        
        # Verificar que el usuario puede ver esta notificación
        if notification["user_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede ver esta notificación"
            )
        
        return NotificationResponse(
            id=str(notification["_id"]),
            type=notification["type"],
            subject=notification["subject"],
            message=notification["message"],
            status=notification["status"],
            created_at=str(notification["created_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo notificación", notification_id=notification_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo notificación"
        )


@app.put("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Marcar notificación como leída"""
    try:
        db = await get_database()
        
        # Verificar que la notificación existe y pertenece al usuario
        notification = await db[Collections.NOTIFICATIONS].find_one({"_id": notification_id})
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación no encontrada"
            )
        
        if notification["user_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede modificar esta notificación"
            )
        
        # Marcar como leída
        await db[Collections.NOTIFICATIONS].update_one(
            {"_id": notification_id},
            {"$set": {"status": "read"}}
        )
        
        return {"message": "Notificación marcada como leída"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error marcando notificación como leída", notification_id=notification_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marcando notificación como leída"
        )


# Endpoints para gestión de preferencias de usuario
@app.put("/users/{user_id}/notification-preference")
async def update_notification_preference(
    user_id: str,
    preference: NotificationType,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Actualizar preferencia de notificación del usuario"""
    try:
        db = await get_database()
        
        # Verificar que el usuario puede modificar sus preferencias
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede modificar preferencias de otros usuarios"
            )
        
                # Actualizar preferencia
        result = await db[Collections.USERS].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"notification_preference": preference.value}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        logger.info(
            "Preferencia de notificación actualizada",
            user_id=user_id,
            preference=preference.value
        )
        
        return {"message": "Preferencia de notificación actualizada"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando preferencia", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando preferencia"
        )


# Endpoint para enviar notificación de suscripción a fondo
@app.post("/notifications/fund-subscription")
async def send_fund_subscription_notification(
    request: dict,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Enviar notificación de suscripción a fondo"""
    try:
        # Extraer parámetros del body
        user_id = request.get("user_id")
        fund_name = request.get("fund_name")
        amount = request.get("amount")
        
        # Validar parámetros requeridos
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id es requerido"
            )
        if not fund_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fund_name es requerido"
            )
        if not amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount es requerido"
            )
        
        # Obtener preferencia del usuario
        db = await get_database()
        user = await db[Collections.USERS].find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        notification_type = NotificationType(user["notification_preference"])
        
        # Crear mensaje personalizado
        subject = "Suscripción Exitosa - BTG Pactual"
        message = f"""
        <h2>¡Suscripción Exitosa!</h2>
        <p>Estimado/a {user['first_name']} {user['last_name']},</p>
        <p>Su suscripción al fondo <strong>{fund_name}</strong> ha sido procesada exitosamente.</p>
        <p><strong>Detalles de la transacción:</strong></p>
        <ul>
            <li>Fondo: {fund_name}</li>
            <li>Monto invertido: ${amount:,.0f} COP</li>
            <li>Fecha: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        <p>Gracias por confiar en BTG Pactual para sus inversiones.</p>
        <p>Saludos cordiales,<br>Equipo BTG Pactual</p>
        """
        
        # Enviar notificación en background
        background_tasks.add_task(
            NotificationService.send_notification,
            user_id, notification_type, subject, message
        )
        
        return {
            "message": "Notificación de suscripción programada",
            "user_id": user_id,
            "fund_name": fund_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error enviando notificación de suscripción", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enviando notificación de suscripción"
        )


# Endpoint para enviar notificación de cancelación de fondo
@app.post("/notifications/fund-cancellation")
async def send_fund_cancellation_notification(
    request: dict,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Enviar notificación de cancelación de fondo"""
    try:
        # Extraer parámetros del body
        user_id = request.get("user_id")
        fund_name = request.get("fund_name")
        amount = request.get("amount")
        
        # Validar parámetros requeridos
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id es requerido"
            )
        if not fund_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fund_name es requerido"
            )
        if not amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount es requerido"
            )
        
        # Obtener preferencia del usuario
        db = await get_database()
        user = await db[Collections.USERS].find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        notification_type = NotificationType(user["notification_preference"])
        
        # Crear mensaje personalizado
        subject = "Cancelación de Suscripción - BTG Pactual"
        message = f"""
        <h2>Cancelación Procesada</h2>
        <p>Estimado/a {user['first_name']} {user['last_name']},</p>
        <p>Su cancelación de suscripción al fondo <strong>{fund_name}</strong> ha sido procesada exitosamente.</p>
        <p><strong>Detalles de la transacción:</strong></p>
        <ul>
            <li>Fondo: {fund_name}</li>
            <li>Monto devuelto: ${amount:,.0f} COP</li>
            <li>Fecha: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        <p>El monto ha sido devuelto a su cuenta disponible.</p>
        <p>Gracias por haber confiado en BTG Pactual.</p>
        <p>Saludos cordiales,<br>Equipo BTG Pactual</p>
        """
        
        # Enviar notificación en background
        background_tasks.add_task(
            NotificationService.send_notification,
            user_id, notification_type, subject, message
        )
        
        return {
            "message": "Notificación de cancelación programada",
            "user_id": user_id,
            "fund_name": fund_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error enviando notificación de cancelación", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enviando notificación de cancelación"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
