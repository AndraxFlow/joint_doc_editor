from sqlalchemy import Column, String, Integer, ForeignKey, UUID, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
import enum

from app.db.base import BaseModel


class OperationType(enum.Enum):
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"


class DocumentSession(BaseModel):
    __tablename__ = "document_sessions"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.uuid"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    cursor_position = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default="now()")
    
    # Relationships
    document = relationship("Document", back_populates="sessions")
    user = relationship("User", back_populates="sessions")


class Operation(BaseModel):
    __tablename__ = "operations"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.uuid"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False)
    position = Column(Integer, nullable=False)
    content = Column(String(1000), default="")
    length = Column(Integer, default=0)
    version = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default="now()")
    
    # Relationships
    document = relationship("Document", back_populates="operations")
    user = relationship("User", back_populates="operations")


class UserCursor(BaseModel):
    __tablename__ = "user_cursors"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.uuid"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    position = Column(Integer, nullable=False)
    selection_start = Column(Integer, nullable=False)
    selection_end = Column(Integer, nullable=False)
    color = Column(String(7), default="#FF0000")  # Hex color code
    
    # Relationships
    document = relationship("Document")
    user = relationship("User")