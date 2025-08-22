"""
Servicio de Gestión de Fondos - BTG Pactual
"""
import asyncio
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from bson import ObjectId  # Agregar import para ObjectId
from decimal import Decimal  # Agregar import para Decimal
import uuid  # Agregar import para UUID

from shared.config import settings
from shared.database import db_manager, get_database, Collections
from shared.models import (
    Fund, FundResponse, SubscriptionRequest, CancellationRequest,
    TransactionResponse, UserBalanceResponse, TransactionType
)
from shared.auth import get_current_active_user, TokenData, check_rate_limit


# Configuración de logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Inicio
    logger.info("🚀 Iniciando servicio de fondos...")
    
    # Conectar a la base de datos
    await db_manager.connect()
    await db_manager.initialize_data()
    
    logger.info("✅ Servicio de fondos iniciado correctamente")
    
    yield
    
    # Cierre
    logger.info("🔄 Cerrando servicio de fondos...")
    await db_manager.disconnect()
    logger.info("✅ Servicio de fondos cerrado")


# Crear aplicación FastAPI
app = FastAPI(
    title="BTG Pactual - Servicio de Fondos",
    description="API para gestión de fondos de inversión",
    version="1.0.0",
    lifespan=lifespan
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
        "service": "funds-service",
        "version": settings.app_version
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Verificación detallada de salud"""
    from shared.database import health_check, get_collection_stats
    
    db_healthy = await health_check()
    collection_stats = await get_collection_stats()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": "funds-service",
        "version": settings.app_version,
        "database": {
            "status": "connected" if db_healthy else "disconnected",
            "collections": collection_stats
        }
    }


# Endpoints de fondos
@app.get("/funds", response_model=List[FundResponse])
async def get_funds(
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener lista de fondos disponibles"""
    try:
        db = await get_database()
        
        # Obtener fondos activos
        cursor = db[Collections.FUNDS].find({"is_active": True})
        funds = await cursor.to_list(length=None)
        
        return [
            FundResponse(
                id=fund["fund_id"],  # Cambiar de "id" a "fund_id"
                name=fund["name"],
                min_amount=str(fund["minimum_amount"]),  # Cambiar de "min_amount" a "minimum_amount"
                category=fund["category"],
                is_active=fund["is_active"]
            )
            for fund in funds
        ]
        
    except Exception as e:
        logger.error("Error obteniendo fondos", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo fondos"
        )


@app.get("/funds/{fund_id}", response_model=FundResponse)
async def get_fund(
    fund_id: int,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener detalles de un fondo específico"""
    try:
        db = await get_database()
        
        fund = await db[Collections.FUNDS].find_one({"fund_id": fund_id, "is_active": True})
        
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fondo con ID {fund_id} no encontrado"
            )
        
        return FundResponse(
            id=fund["fund_id"],  # Cambiar de "id" a "fund_id"
            name=fund["name"],
            min_amount=str(fund["minimum_amount"]),  # Cambiar de "min_amount" a "minimum_amount"
            category=fund["category"],
            is_active=fund["is_active"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo fondo", fund_id=fund_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo fondo"
        )


# Endpoints de transacciones
@app.post("/funds/subscribe", response_model=TransactionResponse)
async def subscribe_to_fund(
    subscription: SubscriptionRequest,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Suscribirse a un fondo"""
    try:
        db = await get_database()
        
        # Verificar que el fondo existe y está activo
        fund = await db[Collections.FUNDS].find_one({
            "fund_id": subscription.fund_id,  # Cambiar de "id" a "fund_id"
            "is_active": True
        })
        
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fondo con ID {subscription.fund_id} no encontrado"
            )
        
        # Convertir monto a Decimal para compatibilidad
        amount_decimal = Decimal(str(subscription.amount))
        
        # Verificar monto mínimo
        if amount_decimal < fund["minimum_amount"]:  # Cambiar de "min_amount" a "minimum_amount"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El monto mínimo para este fondo es ${fund['minimum_amount']:,.0f} COP"
            )
        
        # Obtener usuario y verificar saldo
        try:
            object_id = ObjectId(current_user.user_id)
            user = await db[Collections.USERS].find_one({"_id": object_id})
        except Exception as e:
            logger.error(f"Error convirtiendo user_id a ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Convertir balance del usuario a Decimal después de obtener el usuario
        user_balance_decimal = Decimal(str(user["balance"]))
        
        if user_balance_decimal < amount_decimal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No tiene saldo disponible para vincularse al fondo {fund['name']}"
            )
        
        # Verificar que no tenga suscripción activa al mismo fondo
        existing_subscription = await db[Collections.USER_SUBSCRIPTIONS].find_one({
            "user_id": current_user.user_id,
            "fund_id": subscription.fund_id,
            "is_active": True
        })
        
        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya tiene una suscripción activa al fondo {fund['name']}"
            )
        
        # Crear transacción con transaction_id único
        transaction_id = str(uuid.uuid4())
        transaction = {
            "transaction_id": transaction_id,  # Generar ID único
            "user_id": current_user.user_id,
            "fund_id": subscription.fund_id,
            "transaction_type": TransactionType.SUBSCRIPTION.value,
            "amount": float(amount_decimal),  # Convertir a float para MongoDB
            "balance_before": float(user_balance_decimal),  # Convertir a float para MongoDB
            "balance_after": float(user_balance_decimal - amount_decimal),  # Usar Decimal para la operación
            "status": "completed",
            "created_at": asyncio.get_event_loop().time(),
            "updated_at": asyncio.get_event_loop().time()
        }
        
        # Ejecutar transacción en una sesión
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                # Insertar transacción
                result = await db[Collections.TRANSACTIONS].insert_one(transaction)
                
                # Actualizar saldo del usuario
                await db[Collections.USERS].update_one(
                    {"_id": object_id},  # Usar ObjectId en lugar de "id"
                    {"$set": {"balance": float(user_balance_decimal - amount_decimal)}}  # Convertir a float para MongoDB
                )
                
                # Crear suscripción
                subscription_doc = {
                    "user_id": current_user.user_id,
                    "fund_id": subscription.fund_id,
                    "amount": float(amount_decimal),  # Convertir a float para MongoDB
                    "is_active": True,
                    "created_at": asyncio.get_event_loop().time(),
                    "updated_at": asyncio.get_event_loop().time()
                }
                await db[Collections.USER_SUBSCRIPTIONS].insert_one(subscription_doc)
                
                await session.commit_transaction()
        
        logger.info(
            "Suscripción creada exitosamente",
            user_id=current_user.user_id,
            fund_id=subscription.fund_id,
            amount=subscription.amount
        )
        
        return TransactionResponse(
            id=transaction_id,  # Usar el transaction_id generado
            fund_name=fund["name"],
            transaction_type=TransactionType.SUBSCRIPTION.value,
            amount=str(amount_decimal),
            balance_after=str(user_balance_decimal - amount_decimal),
            status="completed",
            created_at=str(transaction["created_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(
            "Error en suscripción",
            user_id=current_user.user_id,
            fund_id=subscription.fund_id,
            error=str(e),
            traceback=traceback.format_exc()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando suscripción"
        )


@app.post("/funds/cancel", response_model=TransactionResponse)
async def cancel_subscription(
    cancellation: CancellationRequest,
    current_user: TokenData = Depends(check_rate_limit)
):
    """Cancelar suscripción a un fondo"""
    try:
        db = await get_database()
        
        # Verificar que el fondo existe
        fund = await db[Collections.FUNDS].find_one({"fund_id": cancellation.fund_id})
        
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fondo con ID {cancellation.fund_id} no encontrado"
            )
        
        # Verificar que tiene suscripción activa
        subscription = await db[Collections.USER_SUBSCRIPTIONS].find_one({
            "user_id": current_user.user_id,
            "fund_id": cancellation.fund_id,
            "is_active": True
        })
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No tiene suscripción activa al fondo {fund['name']}"
            )
        
        # Obtener usuario
        try:
            object_id = ObjectId(current_user.user_id)
            user = await db[Collections.USERS].find_one({"_id": object_id})
        except Exception as e:
            logger.error(f"Error convirtiendo user_id a ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Crear transacción de cancelación con transaction_id único
        transaction_id = str(uuid.uuid4())
        transaction = {
            "transaction_id": transaction_id,  # Generar ID único
            "user_id": current_user.user_id,
            "fund_id": cancellation.fund_id,
            "transaction_type": TransactionType.CANCELLATION.value,
            "amount": subscription["amount"],
            "balance_before": user["balance"],
            "balance_after": user["balance"] + subscription["amount"],
            "status": "completed",
            "created_at": asyncio.get_event_loop().time(),
            "updated_at": asyncio.get_event_loop().time()
        }
        
        # Ejecutar cancelación en una sesión
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                # Insertar transacción
                result = await db[Collections.TRANSACTIONS].insert_one(transaction)
                
                # Actualizar saldo del usuario
                await db[Collections.USERS].update_one(
                    {"_id": object_id},  # Usar ObjectId en lugar de "id"
                    {"$set": {"balance": float(user["balance"] + subscription["amount"])}}  # Convertir a float para MongoDB
                )
                
                # Eliminar suscripción completamente
                await db[Collections.USER_SUBSCRIPTIONS].delete_one(
                    {"_id": subscription["_id"]}
                )
                
                await session.commit_transaction()
        
        logger.info(
            "Suscripción cancelada exitosamente",
            user_id=current_user.user_id,
            fund_id=cancellation.fund_id,
            amount=subscription["amount"]
        )
        
        return TransactionResponse(
            id=transaction_id,  # Usar el transaction_id generado
            fund_name=fund["name"],
            transaction_type=TransactionType.CANCELLATION.value,
            amount=str(subscription["amount"]),
            balance_after=str(user["balance"] + subscription["amount"]),
            status="completed",
            created_at=str(transaction["created_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error en cancelación",
            user_id=current_user.user_id,
            fund_id=cancellation.fund_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando cancelación"
        )


@app.get("/user/balance", response_model=UserBalanceResponse)
async def get_user_balance(
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener saldo y suscripciones del usuario"""
    try:
        db = await get_database()
        
        # Obtener usuario
        try:
            object_id = ObjectId(current_user.user_id)
            user = await db[Collections.USERS].find_one({"_id": object_id})
        except Exception as e:
            logger.error(f"Error convirtiendo user_id a ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Obtener suscripciones activas
        cursor = db[Collections.USER_SUBSCRIPTIONS].find({
            "user_id": current_user.user_id,
            "is_active": True
        })
        
        subscriptions = await cursor.to_list(length=None)
        
        # Calcular total invertido
        total_invested = sum(sub["amount"] for sub in subscriptions)
        
        # Obtener nombres de fondos
        active_subscriptions = []
        for sub in subscriptions:
            fund = await db[Collections.FUNDS].find_one({"fund_id": sub["fund_id"]})
            active_subscriptions.append({
                "fund_id": sub["fund_id"],
                "fund_name": fund["name"] if fund else "Fondo no encontrado",
                "amount": str(sub["amount"]),
                "created_at": str(sub["created_at"])
            })
        
        return UserBalanceResponse(
            user_id=current_user.user_id,
            balance=str(user["balance"]),
            active_subscriptions=active_subscriptions,
            total_invested=str(total_invested)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error obteniendo balance",
            user_id=current_user.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo balance"
        )


@app.get("/user/transactions", response_model=List[TransactionResponse])
async def get_user_transactions(
    current_user: TokenData = Depends(check_rate_limit)
):
    """Obtener historial de transacciones del usuario"""
    try:
        db = await get_database()
        
        # Obtener transacciones del usuario
        cursor = db[Collections.TRANSACTIONS].find(
            {"user_id": current_user.user_id}
        ).sort("created_at", -1)
        
        transactions = await cursor.to_list(length=None)
        
        # Obtener nombres de fondos
        transaction_responses = []
        for trans in transactions:
            fund = await db[Collections.FUNDS].find_one({"fund_id": trans["fund_id"]})
            transaction_responses.append(TransactionResponse(
                id=trans.get("transaction_id", str(trans["_id"])),  # Usar transaction_id si existe, sino _id
                fund_name=fund["name"] if fund else "Fondo no encontrado",
                transaction_type=trans["transaction_type"],
                amount=str(trans["amount"]),
                balance_after=str(trans["balance_after"]),
                status=trans["status"],
                created_at=str(trans["created_at"])
            ))
        
        return transaction_responses
        
    except Exception as e:
        logger.error(
            "Error obteniendo transacciones",
            user_id=current_user.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo transacciones"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
