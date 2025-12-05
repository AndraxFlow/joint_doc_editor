from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.domains.collaboration.entities import OperationType


class OperationBase(BaseModel):
    """Базовая схема операции"""
    type: OperationType
    position: int = Field(..., ge=0)
    content: str = ""
    length: int = Field(default=0, ge=0)
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v, info):
        values = info.data if hasattr(info, 'data') else {}
        operation_type = values.get('type')
        if operation_type == OperationType.INSERT and not v:
            raise ValueError('Insert operation must have content')
        if operation_type == OperationType.DELETE and v:
            raise ValueError('Delete operation should not have content')
        return v
    
    @field_validator('length')
    @classmethod
    def validate_length(cls, v, info):
        values = info.data if hasattr(info, 'data') else {}
        operation_type = values.get('type')
        if operation_type == OperationType.DELETE and v <= 0:
            raise ValueError('Delete operation must have positive length')
        return v


class OperationCreate(OperationBase):
    """Схема для создания операции"""
    author_id: uuid.UUID
    version: int = 0


class OperationResponse(OperationBase):
    """Схема для ответа с данными операции"""
    uuid: uuid.UUID
    author_id: uuid.UUID
    timestamp: datetime
    version: int
    
    model_config = ConfigDict(from_attributes=True)


class OperationTransform(BaseModel):
    """Схема для трансформации операций"""
    operation1: OperationResponse
    operation2: OperationResponse


class OperationTransformResponse(BaseModel):
    """Схема для ответа с трансформированными операциями"""
    transformed1: OperationResponse
    transformed2: OperationResponse


class DocumentSessionBase(BaseModel):
    """Базовая схема сессии документа"""
    cursor_position: int = Field(default=0, ge=0)
    selection_start: int = Field(default=0, ge=0)
    selection_end: int = Field(default=0, ge=0)
    
    @field_validator('selection_end')
    @classmethod
    def validate_selection(cls, v, info):
        values = info.data if hasattr(info, 'data') else {}
        selection_start = values.get('selection_start', 0)
        if v < selection_start:
            raise ValueError('Selection end must be greater or equal to selection start')
        return v


class DocumentSessionCreate(DocumentSessionBase):
    """Схема для создания сессии документа"""
    document_id: uuid.UUID
    user_id: uuid.UUID


class DocumentSessionUpdate(BaseModel):
    """Схема для обновления сессии документа"""
    cursor_position: Optional[int] = Field(None, ge=0)
    selection_start: Optional[int] = Field(None, ge=0)
    selection_end: Optional[int] = Field(None, ge=0)
    
    @field_validator('selection_end')
    @classmethod
    def validate_selection(cls, v, info):
        values = info.data if hasattr(info, 'data') else {}
        selection_start = values.get('selection_start')
        if selection_start is not None and v is not None and v < selection_start:
            raise ValueError('Selection end must be greater or equal to selection start')
        return v


class DocumentSessionResponse(DocumentSessionBase):
    """Схема для ответа с данными сессии"""
    uuid: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    color: str
    joined_at: datetime
    last_activity: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class ActiveUsersResponse(BaseModel):
    """Схема для ответа со списком активных пользователей"""
    document_id: uuid.UUID
    active_sessions: List[DocumentSessionResponse]
    total_users: int


class WebSocketMessage(BaseModel):
    """Базовая схема WebSocket сообщения"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]


class OperationMessage(WebSocketMessage):
    """Схема для сообщения с операцией"""
    type: str = "operation"
    data: Dict[str, Any] = Field(..., description="Operation data")


class CursorMessage(WebSocketMessage):
    """Схема для сообщения с позицией курсора"""
    type: str = "cursor"
    data: Dict[str, Any] = Field(..., description="Cursor position data")


class UserJoinedMessage(WebSocketMessage):
    """Схема для сообщения о присоединении пользователя"""
    type: str = "user_joined"
    data: Dict[str, Any] = Field(..., description="User session data")


class UserLeftMessage(WebSocketMessage):
    """Схема для сообщения о выходе пользователя"""
    type: str = "user_left"
    data: Dict[str, Any] = Field(..., description="User session data")


class DocumentSyncRequest(BaseModel):
    """Схема для запроса синхронизации документа"""
    document_id: uuid.UUID
    client_version: int = 0


class DocumentSyncResponse(BaseModel):
    """Схема для ответа с данными синхронизации"""
    document_id: uuid.UUID
    current_version: int
    current_content: str
    pending_operations: List[OperationResponse]
    active_users: List[DocumentSessionResponse]


class ConflictResolutionRequest(BaseModel):
    """Схема для запроса разрешения конфликтов"""
    document_id: uuid.UUID
    conflicting_operations: List[OperationResponse]


class ConflictResolutionResponse(BaseModel):
    """Схема для ответа с разрешенными конфликтами"""
    document_id: uuid.UUID
    resolved_operations: List[OperationResponse]
    final_version: int


class CollaborationStatsResponse(BaseModel):
    """Схема для статистики совместной работы"""
    document_id: uuid.UUID
    total_operations: int
    active_users: int
    total_editing_time_minutes: int
    most_active_user: Optional[uuid.UUID]
    last_activity: datetime


class OperationBatch(BaseModel):
    """Схема для пакета операций"""
    document_id: uuid.UUID
    operations: List[OperationCreate]
    batch_id: uuid.UUID = Field(default_factory=uuid.uuid4)


class OperationBatchResponse(BaseModel):
    """Схема для ответа об обработке пакета операций"""
    batch_id: uuid.UUID
    document_id: uuid.UUID
    processed_operations: List[OperationResponse]
    failed_operations: List[Dict[str, Any]]
    final_version: int