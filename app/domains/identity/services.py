from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, timedelta

from app.db.repositories.user_repository import UserRepository
from app.domains.identity.entities import User
from app.domains.identity.schemas import UserCreate, UserUpdate, UserLogin
from app.core.security import create_access_token, verify_token


class IdentityService:
    """Сервис для работы с идентификацией и аутентификацией пользователей"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Регистрация нового пользователя"""
        # Проверка существования email и username
        if await self.user_repository.email_exists(user_data.email):
            raise ValueError("Email already registered")
        
        if await self.user_repository.username_exists(user_data.username):
            raise ValueError("Username already taken")
        
        # Создание пользователя
        user = User.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password
        )
        
        return await self.user_repository.create(user)
    
    async def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Аутентификация пользователя"""
        user = await self.user_repository.get_by_email(login_data.email)
        
        if not user or not user.is_active:
            return None
        
        if not user.authenticate(login_data.password):
            return None
        
        return user
    
    async def login_user(self, login_data: UserLogin) -> Optional[str]:
        """Вход пользователя и создание JWT токена"""
        user = await self.authenticate_user(login_data)
        
        if not user:
            return None
        
        # Создание JWT токена
        token_data = {
            "sub": str(user.uuid),
            "username": user.username,
            "email": user.email
        }
        
        return create_access_token(data=token_data)
    
    async def get_user_by_uuid(self, user_uuid: uuid.UUID) -> Optional[User]:
        """Получение пользователя по UUID"""
        return await self.user_repository.get_by_uuid(user_uuid)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Получение пользователя по email"""
        return await self.user_repository.get_by_email(email)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        return await self.user_repository.get_by_username(username)
    
    async def update_user_profile(self, user_uuid: uuid.UUID, update_data: UserUpdate) -> Optional[User]:
        """Обновление профиля пользователя"""
        user = await self.user_repository.get_by_uuid(user_uuid)
        
        if not user:
            return None
        
        # Проверка уникальности email и username при изменении
        if update_data.email and update_data.email != user.email:
            if await self.user_repository.email_exists(update_data.email):
                raise ValueError("Email already registered")
        
        if update_data.username and update_data.username != user.username:
            if await self.user_repository.username_exists(update_data.username):
                raise ValueError("Username already taken")
        
        # Обновление данных
        user.update_profile(
            username=update_data.username,
            email=update_data.email
        )
        
        return await self.user_repository.update(user)
    
    async def change_user_password(self, user_uuid: uuid.UUID, current_password: str, new_password: str) -> bool:
        """Смена пароля пользователя"""
        user = await self.user_repository.get_by_uuid(user_uuid)
        
        if not user:
            return False
        
        # Проверка текущего пароля
        if not user.authenticate(current_password):
            raise ValueError("Current password is incorrect")
        
        # Установка нового пароля
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user.password_hash = pwd_context.hash(new_password[:72])
        user.updated_at = datetime.utcnow()
        
        await self.user_repository.update(user)
        return True
    
    async def deactivate_user(self, user_uuid: uuid.UUID) -> bool:
        """Деактивация пользователя"""
        user = await self.user_repository.get_by_uuid(user_uuid)
        
        if not user:
            return False
        
        user.deactivate()
        await self.user_repository.update(user)
        return True
    
    async def activate_user(self, user_uuid: uuid.UUID) -> bool:
        """Активация пользователя"""
        user = await self.user_repository.get_by_uuid(user_uuid)
        
        if not user:
            return False
        
        user.activate()
        await self.user_repository.update(user)
        return True
    
    async def delete_user(self, user_uuid: uuid.UUID) -> bool:
        """Удаление пользователя"""
        return await self.user_repository.delete(user_uuid)
    
    async def get_current_user_from_token(self, token: str) -> Optional[User]:
        """Получение текущего пользователя из JWT токена"""
        try:
            payload = verify_token(token)
            user_uuid = uuid.UUID(payload.get("sub"))
            
            if user_uuid is None:
                return None
            
            user = await self.user_repository.get_by_uuid(user_uuid)
            
            if user is None or not user.is_active:
                return None
            
            return user
            
        except Exception:
            return None
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Получение списка пользователей"""
        return await self.user_repository.get_all(limit, offset)