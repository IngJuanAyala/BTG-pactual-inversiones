#!/usr/bin/env python3
"""
Script para inicializar las colecciones en MongoDB Atlas
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

# Configuración de MongoDB Atlas
MONGODB_URI = "mongodb+srv://btg_admin:bgt_pactual_2025@cluster0.qjzcu.mongodb.net/"
DATABASE_NAME = "btg_pactual"

# Datos iniciales de fondos
INITIAL_FUNDS = [
    {
        "fund_id": "FUND001",
        "name": "BTG Pactual Renta Fija",
        "description": "Fondo de renta fija con bajo riesgo y retornos estables",
        "category": "renta_fija",
        "risk_level": "bajo",
        "min_investment": 1000.0,
        "max_investment": 1000000.0,
        "annual_return": 8.5,
        "management_fee": 1.2,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "fund_id": "FUND002", 
        "name": "BTG Pactual Renta Variable",
        "description": "Fondo de renta variable con exposición a mercados emergentes",
        "category": "renta_variable",
        "risk_level": "medio",
        "min_investment": 5000.0,
        "max_investment": 2000000.0,
        "annual_return": 12.5,
        "management_fee": 1.8,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "fund_id": "FUND003",
        "name": "BTG Pactual Multimercado",
        "description": "Fondo multimercado con estrategia diversificada",
        "category": "multimercado", 
        "risk_level": "medio_alto",
        "min_investment": 2500.0,
        "max_investment": 1500000.0,
        "annual_return": 15.2,
        "management_fee": 2.1,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "fund_id": "FUND004",
        "name": "BTG Pactual Conservador",
        "description": "Fondo conservador con enfoque en preservación de capital",
        "category": "conservador",
        "risk_level": "muy_bajo",
        "min_investment": 500.0,
        "max_investment": 500000.0,
        "annual_return": 6.8,
        "management_fee": 0.9,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "fund_id": "FUND005",
        "name": "BTG Pactual Agresivo",
        "description": "Fondo agresivo con alto potencial de retorno",
        "category": "agresivo",
        "risk_level": "alto",
        "min_investment": 10000.0,
        "max_investment": 5000000.0,
        "annual_return": 18.5,
        "management_fee": 2.5,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

async def create_collections_and_indexes(db):
    """Crear colecciones e índices"""
    print("🔧 Creando colecciones e índices...")
    
    # Colecciones que necesitamos
    collections = [
        "users",
        "funds", 
        "transactions",
        "user_subscriptions",
        "notifications"
    ]
    
    for collection_name in collections:
        # Crear colección (se crea automáticamente al insertar)
        print(f"  ✅ Colección '{collection_name}' lista")
    
    # Crear índices
    print("  📊 Creando índices...")
    
    # Índices para usuarios
    await db.users.create_index("email", unique=True)
    await db.users.create_index("is_active")
    
    # Índices para fondos
    await db.funds.create_index("fund_id", unique=True)
    await db.funds.create_index("is_active")
    await db.funds.create_index("category")
    
    # Índices para transacciones
    await db.transactions.create_index("user_id")
    await db.transactions.create_index("fund_id")
    await db.transactions.create_index("created_at")
    await db.transactions.create_index([("user_id", 1), ("created_at", -1)])
    
    # Índices para suscripciones
    await db.user_subscriptions.create_index([("user_id", 1), ("fund_id", 1)], unique=True)
    await db.user_subscriptions.create_index("is_active")
    
    # Índices para notificaciones
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("status")
    await db.notifications.create_index("created_at")
    
    print("  ✅ Índices creados correctamente")

async def insert_initial_data(db):
    """Insertar datos iniciales"""
    print("📝 Insertando datos iniciales...")
    
    # Verificar si ya existen fondos
    funds_count = await db.funds.count_documents({})
    
    if funds_count == 0:
        # Insertar fondos iniciales
        result = await db.funds.insert_many(INITIAL_FUNDS)
        print(f"  ✅ {len(INITIAL_FUNDS)} fondos iniciales creados")
    else:
        print(f"  ℹ️ Ya existen {funds_count} fondos en la base de datos")

async def create_admin_user(db):
    """Crear usuario administrador inicial"""
    print("👤 Creando usuario administrador...")
    
    # Verificar si ya existe un admin
    admin_exists = await db.users.find_one({"email": "admin@btg-pactual.com"})
    
    if not admin_exists:
        admin_user = {
            "id": str(uuid4()),
            "email": "admin@btg-pactual.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KqQKqK",  # "admin123"
            "first_name": "Administrador",
            "last_name": "BTG Pactual",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.users.insert_one(admin_user)
        print("  ✅ Usuario administrador creado")
        print("  📧 Email: admin@btg-pactual.com")
        print("  🔑 Contraseña: admin123")
    else:
        print("  ℹ️ Usuario administrador ya existe")

async def main():
    """Función principal"""
    print("🚀 Inicializando MongoDB Atlas...")
    
    try:
        # Conectar a MongoDB Atlas
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        
        # Verificar conexión
        await client.admin.command('ping')
        print("✅ Conexión a MongoDB Atlas establecida")
        
        # Crear colecciones e índices
        await create_collections_and_indexes(db)
        
        # Insertar datos iniciales
        await insert_initial_data(db)
        
        # Crear usuario administrador
        await create_admin_user(db)
        
        # Mostrar estadísticas
        print("\n📊 Estadísticas de la base de datos:")
        for collection_name in ["users", "funds", "transactions", "user_subscriptions", "notifications"]:
            count = await db[collection_name].count_documents({})
            print(f"  {collection_name}: {count} documentos")
        
        print("\n✅ Inicialización completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        client.close()
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
