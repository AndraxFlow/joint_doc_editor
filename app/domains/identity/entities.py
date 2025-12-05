import uuid
from datetime import datetime
from typing import Optional
from passlib.context import CryptContext


class User:
    """Сущность пользователя домена Identity"""
    
    def __init__(
        self,
        uuid: uuid.UUID,
        email: str,
        username: str,
        password_hash: str,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.uuid = uuid
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def authenticate(self, password: str) -> bool:
        """Проверка пароля пользователя"""
        return self._pwd_context.verify(password[:72], self.password_hash)
    
    def update_profile(self, username: Optional[str] = None, email: Optional[str] = None) -> None:
        """Обновление профиля пользователя"""
        if username:
            self.username = username
        if email:
            self.email = email
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Деактивация пользователя"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Активация пользователя"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def create_user(cls, email: str, username: str, password: str) -> "User":
        """Создание нового пользователя с хешированием пароля"""
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # bcrypt имеет ограничение 72 байта, обрезаем пароль если нужно
        password_hash = pwd_context.hash(password[:72])
        
        return cls(
            uuid=uuid.uuid4(),
            email=email,
            username=username,
            password_hash=password_hash
        )
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self.uuid == other.uuid
    
    def __repr__(self) -> str:
        return f"User(uuid={self.uuid}, email={self.email}, username={self.username})"