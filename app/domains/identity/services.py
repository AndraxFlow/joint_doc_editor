from app.domains.identity.models import User
from app.core.security import hash_password, verify_password
from sqlalchemy.ext.asyncio import AsyncSession

class IdentityService:
    @staticmethod
    async def create_user(db: AsyncSession, email: str, password: str) -> User:
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
