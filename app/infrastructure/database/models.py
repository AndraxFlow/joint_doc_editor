from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
import uuid
from app.core.db import Base

class UserModel(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(512), nullable=False)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # store latest snapshot as jsonb or bytea; here use text for prototype
    latest_snapshot = Column(String, nullable=True)  # for prototype: JSON/base64 encoded state
