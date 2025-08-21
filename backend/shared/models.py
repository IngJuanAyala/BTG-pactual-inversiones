"""
Modelos de datos compartidos para la plataforma BTG Pactual
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr, validator


class TransactionType(str, Enum):
    """Tipos de transacciones"""
    SUBSCRIPTION = "subscription"
    CANCELLATION = "cancellation"


class FundCategory(str, Enum):
    """Categorías de fondos"""
    FPV = "FPV"
    FIC = "FIC"


class NotificationType(str, Enum):
    """Tipos de notificación"""
    EMAIL = "email"
    SMS = "sms"


class UserRole(str, Enum):
    """Roles de usuario"""
    CLIENT = "client"
    ADMIN = "admin"
    ADVISOR = "advisor"


class Fund(BaseModel):
    """Modelo de fondo de inversión"""
    id: int = Field(..., description="ID único del fondo")
    name: str = Field(..., description="Nombre del fondo")
    min_amount: Decimal = Field(..., description="Monto mínimo de vinculación")
    category: FundCategory = Field(..., description="Categoría del fondo")
    is_active: bool = Field(default=True, description="Estado activo del fondo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class User(BaseModel):
    """Modelo de usuario"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))  # Cambiar a string para aceptar ObjectId
    email: EmailStr = Field(..., description="Email del usuario")
    first_name: str = Field(..., description="Nombre del usuario")
    last_name: str = Field(..., description="Apellido del usuario")
    phone: Optional[str] = Field(None, description="Teléfono del usuario")
    password_hash: Optional[str] = Field(None, description="Hash de la contraseña")
    role: UserRole = Field(default=UserRole.CLIENT)
    balance: Decimal = Field(default=Decimal("500000"), description="Saldo inicial")
    notification_preference: NotificationType = Field(
        default=NotificationType.EMAIL,
        description="Preferencia de notificación"
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+57'):
            raise ValueError('El teléfono debe incluir código de país (+57)')
        return v

    def dict(self, **kwargs):
        """Convertir a diccionario con UUID serializado como string y Decimal como float"""
        data = super().dict(**kwargs)
        # El id ya es string, no necesita conversión
        # Convertir Decimal a float para MongoDB
        if 'balance' in data and isinstance(data['balance'], Decimal):
            data['balance'] = float(data['balance'])
        return data

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class Transaction(BaseModel):
    """Modelo de transacción"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="ID del usuario")
    fund_id: int = Field(..., description="ID del fondo")
    transaction_type: TransactionType = Field(..., description="Tipo de transacción")
    amount: Decimal = Field(..., description="Monto de la transacción")
    balance_before: Decimal = Field(..., description="Saldo antes de la transacción")
    balance_after: Decimal = Field(..., description="Saldo después de la transacción")
    status: str = Field(default="completed", description="Estado de la transacción")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class UserSubscription(BaseModel):
    """Modelo de suscripción de usuario a fondo"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="ID del usuario")
    fund_id: int = Field(..., description="ID del fondo")
    amount: Decimal = Field(..., description="Monto invertido")
    is_active: bool = Field(default=True, description="Estado de la suscripción")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class Notification(BaseModel):
    """Modelo de notificación"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="ID del usuario")
    type: NotificationType = Field(..., description="Tipo de notificación")
    subject: str = Field(..., description="Asunto de la notificación")
    message: str = Field(..., description="Mensaje de la notificación")
    sent_at: Optional[datetime] = Field(None, description="Fecha de envío")
    status: str = Field(default="pending", description="Estado de la notificación")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


# Modelos para requests/responses
class SubscriptionRequest(BaseModel):
    """Request para suscripción a fondo"""
    fund_id: int = Field(..., description="ID del fondo")
    amount: Decimal = Field(..., description="Monto a invertir")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('El monto debe ser mayor a 0')
        return v


class CancellationRequest(BaseModel):
    """Request para cancelación de suscripción"""
    fund_id: int = Field(..., description="ID del fondo a cancelar")


class UserCreateRequest(BaseModel):
    """Request para crear usuario"""
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8, description="Contraseña del usuario (mínimo 8 caracteres)")
    phone: Optional[str] = None
    notification_preference: NotificationType = NotificationType.EMAIL

    @validator('password')
    def validate_password(cls, v):
        """Validar que la contraseña cumpla con los requisitos de seguridad"""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserUpdateRequest(BaseModel):
    """Request para actualizar usuario"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = None
    notification_preference: Optional[NotificationType] = None


class TransactionResponse(BaseModel):
    """Response de transacción"""
    id: str
    fund_name: str
    transaction_type: str
    amount: str
    balance_after: str
    status: str
    created_at: str


class UserBalanceResponse(BaseModel):
    """Response de saldo de usuario"""
    user_id: str
    balance: str
    active_subscriptions: List[dict]
    total_invested: str


class FundResponse(BaseModel):
    """Response de fondo"""
    id: int
    name: str
    min_amount: str
    category: str
    is_active: bool


class NotificationResponse(BaseModel):
    """Response de notificación"""
    id: str
    type: str
    subject: str
    message: str
    status: str
    created_at: str
