import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class OperationType(Enum):
    """Типы операций для Operational Transformation"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"


class Operation:
    """Операция в системе совместного редактирования"""
    
    def __init__(
        self,
        operation_type: OperationType,
        position: int,
        content: str = "",
        length: int = 0,
        author_id: Optional[uuid.UUID] = None,
        timestamp: Optional[datetime] = None,
        version: int = 0
    ):
        self.uuid = uuid.uuid4()
        self.operation_type = operation_type
        self.position = position
        self.content = content
        self.length = length
        self.author_id = author_id
        self.timestamp = timestamp or datetime.utcnow()
        self.version = version
    
    def apply_to(self, text: str) -> str:
        """Применение операции к тексту"""
        if self.operation_type == OperationType.INSERT:
            return text[:self.position] + self.content + text[self.position:]
        elif self.operation_type == OperationType.DELETE:
            return text[:self.position] + text[self.position + self.length:]
        elif self.operation_type == OperationType.RETAIN:
            return text  # Retain не изменяет текст
        return text
    
    def transform(self, other: "Operation") -> "Operation":
        """Трансформация операции относительно другой операции"""
        if self.operation_type == OperationType.INSERT:
            if other.operation_type == OperationType.INSERT:
                if self.position <= other.position:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position,
                        content=self.content,
                        author_id=self.author_id,
                        version=self.version
                    )
                else:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position + len(other.content),
                        content=self.content,
                        author_id=self.author_id,
                        version=self.version
                    )
            elif other.operation_type == OperationType.DELETE:
                if self.position <= other.position:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position,
                        content=self.content,
                        author_id=self.author_id,
                        version=self.version
                    )
                elif self.position > other.position + other.length:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position - other.length,
                        content=self.content,
                        author_id=self.author_id,
                        version=self.version
                    )
                else:
                    return Operation(
                        operation_type=self.operation_type,
                        position=other.position,
                        content=self.content,
                        author_id=self.author_id,
                        version=self.version
                    )
        
        elif self.operation_type == OperationType.DELETE:
            if other.operation_type == OperationType.INSERT:
                if self.position < other.position:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position,
                        length=self.length,
                        author_id=self.author_id,
                        version=self.version
                    )
                elif self.position >= other.position:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position + len(other.content),
                        length=self.length,
                        author_id=self.author_id,
                        version=self.version
                    )
            elif other.operation_type == OperationType.DELETE:
                if self.position + self.length <= other.position:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position,
                        length=self.length,
                        author_id=self.author_id,
                        version=self.version
                    )
                elif self.position >= other.position + other.length:
                    return Operation(
                        operation_type=self.operation_type,
                        position=self.position - other.length,
                        length=self.length,
                        author_id=self.author_id,
                        version=self.version
                    )
                else:
                    # Пересекающиеся удаления
                    start = max(self.position, other.position)
                    end = min(self.position + self.length, other.position + other.length)
                    overlap = end - start
                    
                    if self.position < other.position:
                        return Operation(
                            operation_type=self.operation_type,
                            position=self.position,
                            length=max(0, self.length - overlap),
                            author_id=self.author_id,
                            version=self.version
                        )
                    else:
                        return Operation(
                            operation_type=self.operation_type,
                            position=other.position,
                            length=max(0, self.length - overlap),
                            author_id=self.author_id,
                            version=self.version
                        )
        
        # Для RETAIN и других случаев
        return Operation(
            operation_type=self.operation_type,
            position=self.position,
            content=self.content,
            length=self.length,
            author_id=self.author_id,
            version=self.version
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация операции в словарь"""
        return {
            "uuid": str(self.uuid),
            "type": self.operation_type.value,
            "position": self.position,
            "content": self.content,
            "length": self.length,
            "author_id": str(self.author_id) if self.author_id else None,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        """Десериализация операции из словаря"""
        return cls(
            operation_type=OperationType(data["type"]),
            position=data["position"],
            content=data.get("content", ""),
            length=data.get("length", 0),
            author_id=uuid.UUID(data["author_id"]) if data.get("author_id") else None,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data.get("version", 0)
        )
    
    def __repr__(self) -> str:
        return f"Operation({self.operation_type.value}, pos={self.position}, content='{self.content}', len={self.length})"


class DocumentSession:
    """Сессия совместного редактирования документа"""
    
    def __init__(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        cursor_position: int = 0,
        selection_start: int = 0,
        selection_end: int = 0
    ):
        self.uuid = uuid.uuid4()
        self.document_id = document_id
        self.user_id = user_id
        self.cursor_position = cursor_position
        self.selection_start = selection_start
        self.selection_end = selection_end
        self.joined_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_active = True
        self.color = self._generate_user_color()
    
    def update_cursor(self, position: int, selection_start: int = None, selection_end: int = None) -> None:
        """Обновление позиции курсора"""
        self.cursor_position = position
        if selection_start is not None:
            self.selection_start = selection_start
        if selection_end is not None:
            self.selection_end = selection_end
        self.last_activity = datetime.utcnow()
    
    def update_activity(self) -> None:
        """Обновление времени последней активности"""
        self.last_activity = datetime.utcnow()
    
    def leave_session(self) -> None:
        """Покинуть сессию"""
        self.is_active = False
    
    def _generate_user_color(self) -> str:
        """Генерация цвета для пользователя"""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", 
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"
        ]
        # Простой хеш от user_id для выбора цвета
        hash_value = int(str(self.user_id)[:8], 16) if self.user_id else 0
        return colors[hash_value % len(colors)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация сессии в словарь"""
        return {
            "uuid": str(self.uuid),
            "document_id": str(self.document_id),
            "user_id": str(self.user_id),
            "cursor_position": self.cursor_position,
            "selection_start": self.selection_start,
            "selection_end": self.selection_end,
            "color": self.color,
            "joined_at": self.joined_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active
        }
    
    def __repr__(self) -> str:
        return f"DocumentSession(doc={self.document_id}, user={self.user_id}, active={self.is_active})"


class OperationHistory:
    """История операций для документа"""
    
    def __init__(self, document_id: uuid.UUID):
        self.document_id = document_id
        self.operations: List[Operation] = []
        self.current_version = 0
    
    def add_operation(self, operation: Operation) -> None:
        """Добавление операции в историю"""
        operation.version = self.current_version + 1
        self.operations.append(operation)
        self.current_version += 1
    
    def get_operations_since(self, version: int) -> List[Operation]:
        """Получение операций с указанной версии"""
        return [op for op in self.operations if op.version > version]
    
    def get_last_operation(self) -> Optional[Operation]:
        """Получение последней операции"""
        return self.operations[-1] if self.operations else None
    
    def transform_operation(self, new_operation: Operation) -> Operation:
        """Трансформация новой операции относительно всех предыдущих"""
        transformed = new_operation
        
        for existing_op in self.operations:
            if existing_op.version > new_operation.version:
                transformed = transformed.transform(existing_op)
        
        return transformed
    
    def apply_operation_to_text(self, text: str, operation: Operation) -> str:
        """Применение операции к тексту"""
        return operation.apply_to(text)
    
    def get_current_text(self, initial_text: str) -> str:
        """Получение текущего текста после применения всех операций"""
        current = initial_text
        for operation in self.operations:
            current = self.apply_operation_to_text(current, operation)
        return current
    
    def clear(self) -> None:
        """Очистка истории"""
        self.operations.clear()
        self.current_version = 0
    
    def __len__(self) -> int:
        return len(self.operations)
    
    def __repr__(self) -> str:
        return f"OperationHistory(doc={self.document_id}, version={self.current_version}, ops={len(self)})"