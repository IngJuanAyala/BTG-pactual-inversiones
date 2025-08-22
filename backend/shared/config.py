"""
Configuración centralizada para la plataforma BTG Pactual
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Configuración de la aplicación
    app_name: str = "BTG Pactual Inversiones"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Configuración de la base de datos MongoDB
    mongodb_url: str = Field(
        default="mongodb://admin:password123@localhost:27017/btg_pactual?authSource=admin",
        env="MONGODB_URL"
    )
    mongodb_database: str = Field(default="btg_pactual", env="MONGODB_DATABASE")
    
    # Configuración de Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Configuración de JWT
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Configuración de AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Configuración de SQS/SNS
    sqs_queue_url: Optional[str] = None
    sns_topic_arn: Optional[str] = None
    
    # Configuración de notificaciones
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    twilio_account_sid: Optional[str] = Field(default=None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, env="TWILIO_PHONE_NUMBER")
    
    # Configuración de email
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    from_email: str = Field(default="noreply@btgpactual.com", env="FROM_EMAIL")
    
    # Configuración de Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Configuración de logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuración de seguridad
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    rate_limit_per_minute: int = 60
    
    # Configuración de fondos (datos iniciales)
    initial_balance: float = 500000.0
    
    # Configuración de monitoreo
    sentry_dsn: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()


# Configuración específica por entorno
class DevelopmentSettings(Settings):
    """Configuración para desarrollo"""
    debug: bool = True
    log_level: str = "DEBUG"


class ProductionSettings(Settings):
    """Configuración para producción"""
    debug: bool = False
    log_level: str = "WARNING"
    
    # En producción, todas las variables deben estar en el entorno
    class Config:
        env_file = None


class TestingSettings(Settings):
    """Configuración para testing"""
    debug: bool = True
    mongodb_database: str = "btg_pactual_test"
    redis_db: int = 1
    celery_broker_url: str = "redis://localhost:6379/3"
    celery_result_backend: str = "redis://localhost:6379/4"


def get_settings() -> Settings:
    """Obtener configuración según el entorno"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Configuración de fondos iniciales
INITIAL_FUNDS = [
    {
        "id": 1,
        "name": "FPV_BTG_PACTUAL_RECAUDADORA",
        "min_amount": 75000.0,
        "category": "FPV",
        "is_active": True
    },
    {
        "id": 2,
        "name": "FPV_BTG_PACTUAL_ECOPETROL",
        "min_amount": 125000.0,
        "category": "FPV",
        "is_active": True
    },
    {
        "id": 3,
        "name": "DEUDAPRIVADA",
        "min_amount": 50000.0,
        "category": "FIC",
        "is_active": True
    },
    {
        "id": 4,
        "name": "FDO-ACCIONES",
        "min_amount": 250000.0,
        "category": "FIC",
        "is_active": True
    },
    {
        "id": 5,
        "name": "FPV_BTG_PACTUAL_DINAMICA",
        "min_amount": 100000.0,
        "category": "FPV",
        "is_active": True
    }
]
