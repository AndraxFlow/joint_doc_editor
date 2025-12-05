from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db import get_db
from app.core.security import extract_token_from_header
from app.domains.identity.schemas import (
    UserCreate, UserLogin, UserResponse, Token, UserUpdate, PasswordChange
)
from app.domains.identity.services import IdentityService

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Зависимость для получения текущего пользователя"""
    token = credentials.credentials
    identity_service = IdentityService(db)
    user = await identity_service.get_current_user_from_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    """Зависимость для получения активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    identity_service = IdentityService(db)
    
    try:
        user = await identity_service.register_user(user_data)
        return UserResponse(
            uuid=user.uuid,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            word_count=0,  # Для пользователей не применимо
            content_length=0  # Для пользователей не применимо
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Вход пользователя"""
    identity_service = IdentityService(db)
    
    token = await identity_service.login_user(login_data)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о текущем пользователе (демо режим)"""
    # В демо режиме возвращаем фиктивного пользователя
    import uuid
    from datetime import datetime
    
    return UserResponse(
        uuid=uuid.UUID("12345678-1234-5678-9abc-123456789abc"),
        email="demo@example.com",
        username="demo_user",
        is_active=True,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        word_count=0,
        content_length=0
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление информации о текущем пользователе (демо режим)"""
    # В демо режиме просто возвращаем обновленные данные
    import uuid
    from datetime import datetime
    
    return UserResponse(
        uuid=uuid.UUID("12345678-1234-5678-9abc-123456789abc"),
        email=update_data.email or "demo@example.com",
        username=update_data.username or "demo_user",
        is_active=True,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        word_count=0,
        content_length=0
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db)
):
    """Смена пароля (демо режим)"""
    # В демо режиме просто возвращаем успех
    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout():
    """Выход пользователя"""
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: AsyncSession = Depends(get_db)
):
    """Обновление токена (демо режим)"""
    # В демо режиме создаем фиктивный токен
    from app.core.security import create_access_token
    import uuid
    
    token_data = {
        "sub": str(uuid.UUID("12345678-1234-5678-9abc-123456789abc")),
        "username": "demo_user",
        "email": "demo@example.com"
    }
    
    new_token = create_access_token(data=token_data)
    
    return {"access_token": new_token, "token_type": "bearer"}