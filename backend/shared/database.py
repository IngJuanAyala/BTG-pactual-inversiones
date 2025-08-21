"""
Configuración de base de datos MongoDB para la plataforma BTG Pactual
"""
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .config import settings


class DatabaseManager:
    """Gestor de conexión a MongoDB"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Conectar a MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Verificar conexión
            await self.client.admin.command('ping')
            
            self.database = self.client[settings.mongodb_database]
            
            # Crear índices necesarios
            await self._create_indexes()
            
            print(f"✅ Conectado a MongoDB: {settings.mongodb_database}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Desconectar de MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Desconectado de MongoDB")
    
    async def _create_indexes(self):
        """Crear índices para optimizar consultas"""
        try:
            # Índices para usuarios
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("is_active")
            
            # Índices para fondos
            await self.database.funds.create_index("id", unique=True)
            await self.database.funds.create_index("is_active")
            await self.database.funds.create_index("category")
            
            # Índices para transacciones
            await self.database.transactions.create_index("user_id")
            await self.database.transactions.create_index("fund_id")
            await self.database.transactions.create_index("created_at")
            await self.database.transactions.create_index([("user_id", 1), ("created_at", -1)])
            
            # Índices para suscripciones
            await self.database.user_subscriptions.create_index([("user_id", 1), ("fund_id", 1)], unique=True)
            await self.database.user_subscriptions.create_index("is_active")
            
            # Índices para notificaciones
            await self.database.notifications.create_index("user_id")
            await self.database.notifications.create_index("status")
            await self.database.notifications.create_index("created_at")
            
            print("✅ Índices creados correctamente")
            
        except Exception as e:
            print(f"⚠️ Error creando índices: {e}")
    
    async def initialize_data(self):
        """Inicializar datos básicos en la base de datos"""
        try:
            # Verificar si ya existen fondos
            funds_count = await self.database.funds.count_documents({})
            
            if funds_count == 0:
                from .config import INITIAL_FUNDS
                
                # Insertar fondos iniciales
                await self.database.funds.insert_many(INITIAL_FUNDS)
                print(f"✅ {len(INITIAL_FUNDS)} fondos iniciales creados")
            
        except Exception as e:
            print(f"⚠️ Error inicializando datos: {e}")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """Obtener instancia de la base de datos"""
        if self.database is None:
            raise RuntimeError("Base de datos no conectada")
        return self.database


# Instancia global del gestor de base de datos
db_manager = DatabaseManager()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency para obtener la base de datos"""
    return db_manager.get_database()


# Colecciones de la base de datos
class Collections:
    """Nombres de las colecciones"""
    USERS = "users"
    FUNDS = "funds"
    TRANSACTIONS = "transactions"
    USER_SUBSCRIPTIONS = "user_subscriptions"
    NOTIFICATIONS = "notifications"


# Funciones de utilidad para la base de datos
async def health_check() -> bool:
    """Verificar salud de la base de datos"""
    try:
        if db_manager.client is None:
            return False
        await db_manager.client.admin.command('ping')
        return True
    except Exception:
        return False


async def get_collection_stats():
    """Obtener estadísticas de las colecciones"""
    stats = {}
    
    for collection_name in [
        Collections.USERS,
        Collections.FUNDS,
        Collections.TRANSACTIONS,
        Collections.USER_SUBSCRIPTIONS,
        Collections.NOTIFICATIONS
    ]:
        try:
            count = await db_manager.database[collection_name].count_documents({})
            stats[collection_name] = count
        except Exception as e:
            stats[collection_name] = f"Error: {e}"
    
    return stats
