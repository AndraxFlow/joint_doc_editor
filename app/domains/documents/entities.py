import uuid
from datetime import datetime
from typing import Optional, List


class Document:
    """Сущность документа домена Documents"""
    
    def __init__(
        self,
        uuid: uuid.UUID,
        title: str,
        content: str = "",
        version: int = 1,
        owner_id: uuid.UUID = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.uuid = uuid
        self.title = title
        self.content = content
        self.version = version
        self.owner_id = owner_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def update_content(self, new_content: str) -> "DocumentVersion":
        """Обновление содержимого документа и создание новой версии"""
        old_content = self.content
        self.content = new_content
        self.version += 1
        self.updated_at = datetime.utcnow()
        
        return DocumentVersion.create_version(
            document_id=self.uuid,
            content=new_content,
            version_number=self.version,
            created_by=self.owner_id
        )
    
    def update_title(self, new_title: str) -> None:
        """Обновление заголовка документа"""
        self.title = new_title
        self.updated_at = datetime.utcnow()
    
    def get_content_length(self) -> int:
        """Получение длины содержимого документа"""
        return len(self.content)
    
    def get_word_count(self) -> int:
        """Подсчет количества слов в документе"""
        if not self.content.strip():
            return 0
        return len(self.content.split())
    
    @classmethod
    def create_document(cls, title: str, owner_id: uuid.UUID, content: str = "") -> "Document":
        """Создание нового документа"""
        return cls(
            uuid=uuid.uuid4(),
            title=title,
            content=content,
            version=1,
            owner_id=owner_id
        )
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Document):
            return False
        return self.uuid == other.uuid
    
    def __repr__(self) -> str:
        return f"Document(uuid={self.uuid}, title={self.title}, version={self.version})"


class DocumentVersion:
    """Сущность версии документа"""
    
    def __init__(
        self,
        uuid: uuid.UUID,
        document_id: uuid.UUID,
        content: str,
        version_number: int,
        created_by: uuid.UUID,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.uuid = uuid
        self.document_id = document_id
        self.content = content
        self.version_number = version_number
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def get_diff(self, other_content: str) -> str:
        """Получение разницы между версиями (упрощенная реализация)"""
        # В реальном приложении здесь можно использовать difflib
        if self.content == other_content:
            return "No changes"
        
        lines1 = self.content.splitlines()
        lines2 = other_content.splitlines()
        
        diff_lines = []
        for i, (line1, line2) in enumerate(zip(lines1, lines2)):
            if line1 != line2:
                diff_lines.append(f"Line {i+1}: '{line1}' -> '{line2}'")
        
        # Обработка разной длины
        if len(lines1) > len(lines2):
            for i in range(len(lines2), len(lines1)):
                diff_lines.append(f"Line {i+1}: REMOVED '{lines1[i]}'")
        elif len(lines2) > len(lines1):
            for i in range(len(lines1), len(lines2)):
                diff_lines.append(f"Line {i+1}: ADDED '{lines2[i]}'")
        
        return "\n".join(diff_lines) if diff_lines else "Content changed"
    
    @classmethod
    def create_version(
        cls, 
        document_id: uuid.UUID, 
        content: str, 
        version_number: int, 
        created_by: uuid.UUID
    ) -> "DocumentVersion":
        """Создание новой версии документа"""
        return cls(
            uuid=uuid.uuid4(),
            document_id=document_id,
            content=content,
            version_number=version_number,
            created_by=created_by
        )
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, DocumentVersion):
            return False
        return self.uuid == other.uuid
    
    def __repr__(self) -> str:
        return f"DocumentVersion(uuid={self.uuid}, document_id={self.document_id}, version={self.version_number})"


class DocumentAccess:
    """Сущность для управления доступом к документу"""
    
    def __init__(self, document_id: uuid.UUID, owner_id: uuid.UUID):
        self.document_id = document_id
        self.owner_id = owner_id
        self._collaborators = set()
    
    def add_collaborator(self, user_id: uuid.UUID) -> None:
        """Добавление соавтора"""
        self._collaborators.add(user_id)
    
    def remove_collaborator(self, user_id: uuid.UUID) -> None:
        """Удаление соавтора"""
        self._collaborators.discard(user_id)
    
    def can_access(self, user_id: uuid.UUID) -> bool:
        """Проверка доступа пользователя к документу"""
        return user_id == self.owner_id or user_id in self._collaborators
    
    def can_edit(self, user_id: uuid.UUID) -> bool:
        """Проверка прав на редактирование"""
        return self.can_access(user_id)  # Упрощенно - все кто имеет доступ могут редактировать
    
    def is_owner(self, user_id: uuid.UUID) -> bool:
        """Проверка является ли пользователь владельцем"""
        return user_id == self.owner_id
    
    def get_collaborators(self) -> List[uuid.UUID]:
        """Получение списка соавторов"""
        return list(self._collaborators)