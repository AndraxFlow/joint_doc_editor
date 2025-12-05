from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
import time

from app.db.repositories.document_repository import DocumentRepository, DocumentVersionRepository
from app.domains.documents.entities import Document, DocumentVersion, DocumentAccess
from app.domains.documents.schemas import (
    DocumentCreate, DocumentUpdate, DocumentSearchRequest,
    DocumentVersionCreate
)


class DocumentService:
    """Сервис для работы с документами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repository = DocumentRepository(session)
        self.version_repository = DocumentVersionRepository(session)
    
    async def create_document(self, document_data: DocumentCreate, owner_id: uuid.UUID) -> Document:
        """Создание нового документа"""
        document = Document.create_document(
            title=document_data.title,
            owner_id=owner_id,
            content=document_data.content
        )
        
        created_document = await self.document_repository.create(document)
        
        # Создаем начальную версию
        initial_version = DocumentVersion.create_version(
            document_id=created_document.uuid,
            content=document_data.content,
            version_number=1,
            created_by=owner_id
        )
        await self.version_repository.create(initial_version)
        
        return created_document
    
    async def get_document(self, document_uuid: uuid.UUID) -> Optional[Document]:
        """Получение документа по UUID"""
        return await self.document_repository.get_by_uuid(document_uuid)
    
    async def update_document(
        self, 
        document_uuid: uuid.UUID, 
        update_data: DocumentUpdate,
        user_id: uuid.UUID
    ) -> Optional[Document]:
        """Обновление документа"""
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return None
        
        # Проверка прав доступа
        access = DocumentAccess(document_uuid, document.owner_id)
        if not access.can_edit(user_id):
            raise PermissionError("You don't have permission to edit this document")
        
        # Обновление заголовка
        if update_data.title:
            document.update_title(update_data.title)
        
        # Обновление содержимого с созданием новой версии
        if update_data.content is not None:
            new_version = document.update_content(update_data.content)
            await self.version_repository.create(new_version)
        
        return await self.document_repository.update(document)
    
    async def delete_document(self, document_uuid: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Удаление документа"""
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return False
        
        # Только владелец может удалить документ
        if document.owner_id != user_id:
            raise PermissionError("Only the owner can delete this document")
        
        return await self.document_repository.delete(document_uuid)
    
    async def get_user_documents(
        self, 
        user_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Document]:
        """Получение документов пользователя"""
        return await self.document_repository.get_by_owner(user_id, limit, offset)
    
    async def search_documents(
        self, 
        search_request: DocumentSearchRequest,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        """Поиск документов"""
        start_time = time.time()
        
        documents = await self.document_repository.search(
            query=search_request.query,
            owner_id=user_id,
            search_in_title=search_request.search_in_title,
            search_in_content=search_request.search_in_content,
            limit=limit,
            offset=offset
        )
        
        search_time = int((time.time() - start_time) * 1000)  # в миллисекундах
        
        return documents, search_time
    
    async def get_document_stats(self, document_uuid: uuid.UUID) -> Optional[dict]:
        """Получение статистики документа"""
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return None
        
        version_count = await self.version_repository.count_by_document(document_uuid)
        
        return {
            "document_id": document.uuid,
            "title": document.title,
            "word_count": document.get_word_count(),
            "character_count": document.get_content_length(),
            "paragraph_count": len([p for p in document.content.split('\n') if p.strip()]),
            "version_count": version_count,
            "last_modified": document.updated_at,
            "created_at": document.created_at
        }
    
    async def check_document_access(
        self, 
        document_uuid: uuid.UUID, 
        user_id: uuid.UUID
    ) -> dict:
        """Проверка доступа к документу"""
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return {"can_access": False, "can_edit": False, "is_owner": False}
        
        access = DocumentAccess(document_uuid, document.owner_id)
        
        return {
            "can_access": access.can_access(user_id),
            "can_edit": access.can_edit(user_id),
            "is_owner": access.is_owner(user_id)
        }
    
    async def export_document(
        self, 
        document_uuid: uuid.UUID, 
        format_type: str,
        include_versions: bool = False
    ) -> Optional[dict]:
        """Экспорт документа в различных форматах"""
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return None
        
        content = document.content
        filename = f"{document.title}.{format_type}"
        
        if format_type == "txt":
            exported_content = content
        elif format_type == "md":
            exported_content = f"# {document.title}\n\n{content}"
        elif format_type == "html":
            exported_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{document.title}</title>
            </head>
            <body>
                <h1>{document.title}</h1>
                <pre>{content}</pre>
            </body>
            </html>
            """
        elif format_type == "pdf":
            # Упрощенная реализация - в реальном приложении использовать библиотеку для PDF
            exported_content = f"PDF export not implemented yet. Title: {document.title}\n\n{content}"
            filename = f"{document.title}.txt"
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        if include_versions:
            versions = await self.version_repository.get_by_document(document_uuid)
            version_info = "\n\n".join([
                f"--- Version {v.version_number} ({v.created_at}) ---\n{v.content}"
                for v in versions
            ])
            exported_content += f"\n\n=== VERSION HISTORY ===\n{version_info}"
        
        return {
            "document_id": document.uuid,
            "format": format_type,
            "filename": filename,
            "content": exported_content,
            "exported_at": datetime.utcnow()
        }


class DocumentVersionService:
    """Сервис для работы с версиями документов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.version_repository = DocumentVersionRepository(session)
        self.document_repository = DocumentRepository(session)
    
    async def get_document_versions(
        self, 
        document_uuid: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[DocumentVersion]:
        """Получение версий документа"""
        return await self.version_repository.get_by_document(document_uuid, limit, offset)
    
    async def get_document_version(
        self, 
        document_uuid: uuid.UUID, 
        version_number: int
    ) -> Optional[DocumentVersion]:
        """Получение конкретной версии документа"""
        return await self.version_repository.get_version_by_number(document_uuid, version_number)
    
    async def get_latest_version(self, document_uuid: uuid.UUID) -> Optional[DocumentVersion]:
        """Получение последней версии документа"""
        return await self.version_repository.get_latest_version(document_uuid)
    
    async def compare_versions(
        self, 
        document_uuid: uuid.UUID,
        from_version: int,
        to_version: int
    ) -> Optional[str]:
        """Сравнение двух версий документа"""
        from_doc = await self.version_repository.get_version_by_number(document_uuid, from_version)
        to_doc = await self.version_repository.get_version_by_number(document_uuid, to_version)
        
        if not from_doc or not to_doc:
            return None
        
        return from_doc.get_diff(to_doc.content)
    
    async def restore_version(
        self, 
        document_uuid: uuid.UUID,
        version_number: int,
        user_id: uuid.UUID
    ) -> Optional[Document]:
        """Восстановление документа из версии"""
        version = await self.version_repository.get_version_by_number(document_uuid, version_number)
        
        if not version:
            return None
        
        document = await self.document_repository.get_by_uuid(document_uuid)
        
        if not document:
            return None
        
        # Проверка прав доступа
        access = DocumentAccess(document_uuid, document.owner_id)
        if not access.can_edit(user_id):
            raise PermissionError("You don't have permission to restore this document")
        
        # Восстановление содержимого
        new_version = document.update_content(version.content)
        await self.version_repository.create(new_version)
        
        return await self.document_repository.update(document)