from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.db.models import Base  # импортируем Base всех моделей

config = context.config

fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = config.get_main_option("sqlalchemy.url")
engine = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)

async def run_migrations_online():
    async with engine.begin() as conn:
        await conn.run_sync(context.run_migrations)

if context.is_offline_mode():
    context.run_migrations()
else:
    import asyncio
    asyncio.run(run_migrations_online())
