from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owned_documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("DocumentSession", back_populates="user", cascade="all, delete-orphan")
    operations = relationship("Operation", back_populates="user", cascade="all, delete-orphan")