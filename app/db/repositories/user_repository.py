from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
import uuid

from app.db.models.user import User as UserModel
from app.domains.identity.entities import User


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: User) -> User:
        """Создание нового пользователя"""
        db_user = UserModel(
            uuid=user.uuid,
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            is_active=user.is_active
        )
        
        self.session.add(db_user)
        try:
            await self.session.commit()
            await self.session.refresh(db_user)
            return self._to_domain(db_user)
        except IntegrityError:
            await self.session.rollback()
            raise ValueError("User with this email or username already exists")
    
    async def get_by_uuid(self, user_uuid: uuid.UUID) -> Optional[User]:
        """Получение пользователя по UUID"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.uuid == user_uuid)
        )
        db_user = result.scalar_one_or_none()
        return self._to_domain(db_user) if db_user else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Получение пользователя по email"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        db_user = result.scalar_one_or_none()
        return self._to_domain(db_user) if db_user else None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        db_user = result.scalar_one_or_none()
        return self._to_domain(db_user) if db_user else None
    
    async def update(self, user: User) -> User:
        """Обновление пользователя"""
        stmt = (
            update(UserModel)
            .where(UserModel.uuid == user.uuid)
            .values(
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                updated_at=user.updated_at
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_by_uuid(user.uuid)
    
    async def delete(self, user_uuid: uuid.UUID) -> bool:
        """Удаление пользователя"""
        stmt = delete(UserModel).where(UserModel.uuid == user_uuid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Получение списка пользователей"""
        result = await self.session.execute(
            select(UserModel).offset(offset).limit(limit)
        )
        db_users = result.scalars().all()
        return [self._to_domain(user) for user in db_users]
    
    async def email_exists(self, email: str) -> bool:
        """Проверка существования email"""
        result = await self.session.execute(
            select(UserModel.uuid).where(UserModel.email == email)
        )
        return result.scalar_one_or_none() is not None
    
    async def username_exists(self, username: str) -> bool:
        """Проверка существования username"""
        result = await self.session.execute(
            select(UserModel.uuid).where(UserModel.username == username)
        )
        return result.scalar_one_or_none() is not None
    
    def _to_domain(self, db_user: UserModel) -> User:
        """Преобразование модели БД в доменную сущность"""
        return User(
            uuid=db_user.uuid,
            email=db_user.email,
            username=db_user.username,
            password_hash=db_user.password_hash,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
    
    def _to_model(self, user: User) -> UserModel:
        """Преобразование доменной сущности в модель БД"""
        return UserModel(
            uuid=user.uuid,
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )