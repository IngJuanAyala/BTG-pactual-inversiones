"""
Sistema de autenticación y autorización para la plataforma BTG Pactual
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings
from .models import User, UserRole

# Configuración de seguridad
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """Modelo de token"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Datos del token"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class AuthService:
    """Servicio de autenticación"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generar hash de contraseña"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Crear token de acceso"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Crear token de refresco"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Verificar token"""
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            role: str = payload.get("role")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(user_id=user_id, email=email, role=role)
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def create_tokens(user: User) -> Token:
        """Crear tokens de acceso y refresco"""
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        access_token = AuthService.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value
            },
            expires_delta=access_token_expires
        )
        
        refresh_token = AuthService.create_refresh_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value
            }
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            refresh_token=refresh_token
        )


# Dependencies para FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Obtener usuario actual desde token"""
    token = credentials.credentials
    return AuthService.verify_token(token)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Obtener usuario activo actual"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo"
        )
    return current_user


def require_role(required_role: UserRole):
    """Decorator para requerir rol específico"""
    def role_checker(current_user: TokenData = Depends(get_current_active_user)):
        if current_user.role != required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {required_role.value}"
            )
        return current_user
    return role_checker


def require_any_role(required_roles: list[UserRole]):
    """Decorator para requerir cualquiera de los roles especificados"""
    def role_checker(current_user: TokenData = Depends(get_current_active_user)):
        if current_user.role not in [role.value for role in required_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los roles: {[role.value for role in required_roles]}"
            )
        return current_user
    return role_checker


# Funciones de utilidad
def is_admin(user: TokenData) -> bool:
    """Verificar si el usuario es administrador"""
    return user.role == UserRole.ADMIN.value


def is_advisor(user: TokenData) -> bool:
    """Verificar si el usuario es asesor"""
    return user.role == UserRole.ADVISOR.value


def is_client(user: TokenData) -> bool:
    """Verificar si el usuario es cliente"""
    return user.role == UserRole.CLIENT.value


# Rate limiting
class RateLimiter:
    """Limitador de tasa de requests"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, user_id: str) -> bool:
        """Verificar si el usuario puede hacer una request"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Limpiar requests antiguas
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id] 
            if req_time > minute_ago
        ]
        
        # Verificar límite
        if len(self.requests[user_id]) >= settings.rate_limit_per_minute:
            return False
        
        # Agregar nueva request
        self.requests[user_id].append(now)
        return True


# Instancia global del rate limiter
rate_limiter = RateLimiter()


async def check_rate_limit(current_user: TokenData = Depends(get_current_active_user)):
    """Verificar límite de tasa"""
    if not rate_limiter.is_allowed(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas requests. Intente más tarde."
        )
    return current_user
