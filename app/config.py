from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://docuser:docpass@db:5432/docdb"
    JWT_SECRET: str = "change_this_in_prod"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()
