from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError
import uuid

from app.db.models.document import Document as DocumentModel, DocumentVersion as DocumentVersionModel

if TYPE_CHECKING:
    from app.domains.documents.entities import Document, DocumentVersion


class DocumentRepository:
    """Репозиторий для работы с документами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, document: "Document") -> "Document":
        """Создание нового документа"""
        db_document = DocumentModel(
            uuid=document.uuid,
            title=document.title,
            content=document.content,
            version=document.version,
            owner_id=document.owner_id
        )
        
        self.session.add(db_document)
        try:
            await self.session.commit()
            await self.session.refresh(db_document)
            return self._to_domain(db_document)
        except IntegrityError:
            await self.session.rollback()
            raise ValueError("Invalid owner_id")
    
    async def get_by_uuid(self, document_uuid: uuid.UUID) -> Optional["Document"]:
        """Получение документа по UUID"""
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.uuid == document_uuid)
        )
        db_document = result.scalar_one_or_none()
        return self._to_domain(db_document) if db_document else None
    
    async def get_by_owner(self, owner_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List["Document"]:
        """Получение документов по владельцу"""
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.owner_id == owner_id)
            .order_by(DocumentModel.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        db_documents = result.scalars().all()
        return [self._to_domain(doc) for doc in db_documents]
    
    async def update(self, document: "Document") -> "Document":
        """Обновление документа"""
        stmt = (
            update(DocumentModel)
            .where(DocumentModel.uuid == document.uuid)
            .values(
                title=document.title,
                content=document.content,
                version=document.version,
                updated_at=document.updated_at
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_by_uuid(document.uuid)
    
    async def delete(self, document_uuid: uuid.UUID) -> bool:
        """Удаление документа"""
        stmt = delete(DocumentModel).where(DocumentModel.uuid == document_uuid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def search(
        self,
        query: str,
        owner_id: Optional[uuid.UUID] = None,
        search_in_title: bool = True,
        search_in_content: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List["Document"]:
        """Поиск документов"""
        conditions = []
        
        if search_in_title:
            conditions.append(DocumentModel.title.ilike(f"%{query}%"))
        
        if search_in_content:
            conditions.append(DocumentModel.content.ilike(f"%{query}%"))
        
        if not conditions:
            return []
        
        base_query = select(DocumentModel).where(or_(*conditions))
        
        if owner_id:
            base_query = base_query.where(DocumentModel.owner_id == owner_id)
        
        result = await self.session.execute(
            base_query
            .order_by(DocumentModel.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        db_documents = result.scalars().all()
        return [self._to_domain(doc) for doc in db_documents]
    
    async def count_by_owner(self, owner_id: uuid.UUID) -> int:
        """Подсчет количества документов владельца"""
        result = await self.session.execute(
            select(func.count(DocumentModel.uuid)).where(DocumentModel.owner_id == owner_id)
        )
        return result.scalar()
    
    async def count_search_results(
        self, 
        query: str, 
        owner_id: Optional[uuid.UUID] = None,
        search_in_title: bool = True,
        search_in_content: bool = True
    ) -> int:
        """Подсчет результатов поиска"""
        conditions = []
        
        if search_in_title:
            conditions.append(DocumentModel.title.ilike(f"%{query}%"))
        
        if search_in_content:
            conditions.append(DocumentModel.content.ilike(f"%{query}%"))
        
        if not conditions:
            return 0
        
        base_query = select(func.count(DocumentModel.uuid)).where(or_(*conditions))
        
        if owner_id:
            base_query = base_query.where(DocumentModel.owner_id == owner_id)
        
        result = await self.session.execute(base_query)
        return result.scalar()
    
    def _to_domain(self, db_document: DocumentModel) -> "Document":
        """Преобразование модели БД в доменную сущность"""
        from app.domains.documents.entities import Document
        
        return Document(
            uuid=db_document.uuid,
            title=db_document.title,
            content=db_document.content,
            version=db_document.version,
            owner_id=db_document.owner_id,
            created_at=db_document.created_at,
            updated_at=db_document.updated_at
        )


class DocumentVersionRepository:
    """Репозиторий для работы с версиями документов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, version: "DocumentVersion") -> "DocumentVersion":
        """Создание новой версии документа"""
        db_version = DocumentVersionModel(
            uuid=version.uuid,
            document_id=version.document_id,
            content=version.content,
            version_number=version.version_number,
            created_by=version.created_by
        )
        
        self.session.add(db_version)
        await self.session.commit()
        await self.session.refresh(db_version)
        return self._to_domain(db_version)
    
    async def get_by_uuid(self, version_uuid: uuid.UUID) -> Optional["DocumentVersion"]:
        """Получение версии по UUID"""
        result = await self.session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.uuid == version_uuid)
        )
        db_version = result.scalar_one_or_none()
        return self._to_domain(db_version) if db_version else None
    
    async def get_by_document(
        self,
        document_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List["DocumentVersion"]:
        """Получение версий документа"""
        result = await self.session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        db_versions = result.scalars().all()
        return [self._to_domain(version) for version in db_versions]
    
    async def get_latest_version(self, document_id: uuid.UUID) -> Optional["DocumentVersion"]:
        """Получение последней версии документа"""
        result = await self.session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .limit(1)
        )
        db_version = result.scalar_one_or_none()
        return self._to_domain(db_version) if db_version else None
    
    async def get_version_by_number(
        self,
        document_id: uuid.UUID,
        version_number: int
    ) -> Optional["DocumentVersion"]:
        """Получение версии по номеру"""
        result = await self.session.execute(
            select(DocumentVersionModel)
            .where(
                and_(
                    DocumentVersionModel.document_id == document_id,
                    DocumentVersionModel.version_number == version_number
                )
            )
        )
        db_version = result.scalar_one_or_none()
        return self._to_domain(db_version) if db_version else None
    
    async def count_by_document(self, document_id: uuid.UUID) -> int:
        """Подсчет количества версий документа"""
        result = await self.session.execute(
            select(func.count(DocumentVersionModel.uuid))
            .where(DocumentVersionModel.document_id == document_id)
        )
        return result.scalar()
    
    def _to_domain(self, db_version: DocumentVersionModel) -> "DocumentVersion":
        """Преобразование модели БД в доменную сущность"""
        from app.domains.documents.entities import DocumentVersion
        
        return DocumentVersion(
            uuid=db_version.uuid,
            document_id=db_version.document_id,
            content=db_version.content,
            version_number=db_version.version_number,
            created_by=db_version.created_by,
            created_at=db_version.created_at,
            updated_at=db_version.updated_at
        )