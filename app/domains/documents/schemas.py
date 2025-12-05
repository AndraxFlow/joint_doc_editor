from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime


class DocumentBase(BaseModel):
    """Базовая схема документа"""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(default="", max_length=1000000)  # 1MB max content
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class DocumentCreate(DocumentBase):
    """Схема для создания документа"""
    pass


class DocumentUpdate(BaseModel):
    """Схема для обновления документа"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, max_length=1000000)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


class DocumentResponse(DocumentBase):
    """Схема для ответа с данными документа"""
    uuid: uuid.UUID
    version: int
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    word_count: int
    content_length: int
    
    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Схема для списка документов"""
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int


class DocumentVersionBase(BaseModel):
    """Базовая схема версии документа"""
    content: str = Field(..., max_length=1000000)
    version_number: int


class DocumentVersionResponse(DocumentVersionBase):
    """Схема для ответа с данными версии документа"""
    uuid: uuid.UUID
    document_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    word_count: int
    content_length: int
    
    model_config = ConfigDict(from_attributes=True)


class DocumentVersionCreate(BaseModel):
    """Схема для создания версии документа"""
    content: str = Field(..., max_length=1000000)


class DocumentDiffResponse(BaseModel):
    """Схема для ответа с разницей между версиями"""
    document_id: uuid.UUID
    from_version: int
    to_version: int
    diff: str
    created_at: datetime


class DocumentAccessResponse(BaseModel):
    """Схема для ответа с информацией о доступе к документу"""
    document_id: uuid.UUID
    owner_id: uuid.UUID
    can_edit: bool
    is_owner: bool
    collaborators_count: int


class DocumentShareRequest(BaseModel):
    """Схема для запроса на предоставление доступа к документу"""
    user_email: str
    can_edit: bool = True


class DocumentShareResponse(BaseModel):
    """Схема для ответа о предоставлении доступа"""
    document_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    can_edit: bool
    shared_at: datetime


class DocumentSearchRequest(BaseModel):
    """Схема для поиска документов"""
    query: str = Field(..., min_length=1, max_length=100)
    search_in_title: bool = True
    search_in_content: bool = True
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Search query cannot be empty')
        return v.strip()


class DocumentSearchResponse(BaseModel):
    """Схема для ответа с результатами поиска"""
    documents: List[DocumentResponse]
    total_found: int
    query: str
    search_time_ms: int


class DocumentStatsResponse(BaseModel):
    """Схема для статистики документа"""
    document_id: uuid.UUID
    title: str
    word_count: int
    character_count: int
    paragraph_count: int
    version_count: int
    last_modified: datetime
    created_at: datetime


class DocumentExportRequest(BaseModel):
    """Схема для запроса на экспорт документа"""
    format: str = Field(..., pattern="^(txt|md|html|pdf)$")
    include_versions: bool = False


class DocumentExportResponse(BaseModel):
    """Схема для ответа с экспортированным документом"""
    document_id: uuid.UUID
    format: str
    filename: str
    content: str
    exported_at: datetime