from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)

def create_jwt(data: dict, expires_minutes=60):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
