from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Базовый класс для моделей
Base = declarative_base()

# Асинхронный движок
engine = create_async_engine(settings.DATABASE_URL, future=True, echo=True)

# Сессии
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Функция для dependency injection в FastAPI
async def get_db():
    async with SessionLocal() as session:
        yield session
