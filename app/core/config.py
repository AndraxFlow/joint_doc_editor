from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    
    # PostgreSQL variables for Docker
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()