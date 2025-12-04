from contextlib import asynccontextmanager
from app.core.db import AsyncSessionLocal

@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
