from fastapi import HTTPException
from sqlalchemy import select
from app.domains.identity.entities import User
from app.core.db import SessionLocal
from app.core.security import hash_password, verify_password, create_jwt

class IdentityService:

    @staticmethod
    async def register(email: str, password: str):
        async with SessionLocal() as session:
            existing = await session.execute(select(User).where(User.email == email))
            if existing.scalar_one_or_none():
                raise HTTPException(400, "Email already registered")

            user = User(
                email=email,
                hashed_password=hash_password(password)
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    @staticmethod
    async def login(email: str, password: str):
        async with SessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.hashed_password):
                raise HTTPException(401, "Invalid credentials")

            token = create_jwt({"sub": str(user.id)})
            return token, user
