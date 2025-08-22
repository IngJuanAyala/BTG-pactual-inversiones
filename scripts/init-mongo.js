// Script de inicialización de MongoDB para BTG Pactual
// Este script se ejecuta automáticamente cuando se inicia el contenedor de MongoDB

// Conectar a la base de datos
db = db.getSiblingDB('btg_pactual');

// Crear usuario para la aplicación
db.createUser({
  user: 'btg_user',
  pwd: 'btg_password',
  roles: [
    { role: 'readWrite', db: 'btg_pactual' }
  ]
});

// Crear colecciones
db.createCollection('users');
db.createCollection('funds');
db.createCollection('transactions');
db.createCollection('user_subscriptions');
db.createCollection('notifications');

// Crear índices para optimizar consultas
db.users.createIndex({ "email": 1 }, { unique: true });
// Eliminado el índice problemático de username
db.funds.createIndex({ "fund_id": 1 }, { unique: true });
db.transactions.createIndex({ "transaction_id": 1 }, { unique: true });
db.transactions.createIndex({ "user_id": 1 });
db.transactions.createIndex({ "fund_id": 1 });
db.user_subscriptions.createIndex({ "user_id": 1, "fund_id": 1 }, { unique: true });
db.notifications.createIndex({ "user_id": 1 });
db.notifications.createIndex({ "created_at": 1 });

// Insertar fondos iniciales
db.funds.insertMany([
  {
    fund_id: 1,
    name: "FPV_BTG_PACTUAL_RECAUDADORA",
    minimum_amount: 75000,
    category: "FPV",
    description: "Fondo de Pensiones Voluntarias BTG Pactual Recaudadora",
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    fund_id: 2,
    name: "FPV_BTG_PACTUAL_ECOPETROL",
    minimum_amount: 125000,
    category: "FPV",
    description: "Fondo de Pensiones Voluntarias BTG Pactual Ecopetrol",
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    fund_id: 3,
    name: "DEUDAPRIVADA",
    minimum_amount: 50000,
    category: "FIC",
    description: "Fondo de Inversión Colectiva Deuda Privada",
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    fund_id: 4,
    name: "FDO-ACCIONES",
    minimum_amount: 250000,
    category: "FIC",
    description: "Fondo de Inversión Colectiva Acciones",
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    fund_id: 5,
    name: "FPV_BTG_PACTUAL_DINAMICA",
    minimum_amount: 100000,
    category: "FPV",
    description: "Fondo de Pensiones Voluntarias BTG Pactual Dinámica",
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

print("✅ Base de datos BTG Pactual inicializada correctamente");
print("📊 Fondos insertados: " + db.funds.countDocuments());
print("🔐 Usuario de aplicación creado: btg_user");
