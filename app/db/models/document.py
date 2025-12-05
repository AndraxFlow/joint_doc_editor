from sqlalchemy import Column, String, Text, Integer, ForeignKey, UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, default="")
    version = Column(Integer, default=1)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="owned_documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    sessions = relationship("DocumentSession", back_populates="document", cascade="all, delete-orphan")
    operations = relationship("Operation", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.uuid"), nullable=False)
    content = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="versions")
    creator = relationship("User")