from typing import Optional
from uuid import UUID
from sqlalchemy import select, insert, update
from app.infrastructure.database.models import DocumentModel
from app.infrastructure.database.session import get_session
from app.domains.entities.document import DocumentEntity
from sqlalchemy.ext.asyncio import AsyncSession

class DocumentRepository:
    async def get_by_id(self, doc_id: UUID) -> Optional[DocumentEntity]:
        async with get_session() as session:  
            result = await session.execute(select(DocumentModel).where(DocumentModel.id == doc_id))
            model = result.scalar_one_or_none()
            if not model:
                return None
            return DocumentEntity(
                id=model.id,
                title=model.title,
                owner_id=model.owner_id,
                created_at=model.created_at,
                updated_at=model.updated_at,
                content_preview=(model.latest_snapshot[:200] if model.latest_snapshot else None)
            )

    async def create(self, title: str, owner_id: UUID, snapshot: str = None) -> DocumentEntity:
        async with get_session() as session:
            model = DocumentModel(title=title, owner_id=owner_id, latest_snapshot=snapshot)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return DocumentEntity(
                id=model.id,
                title=model.title,
                owner_id=model.owner_id,
                created_at=model.created_at,
                updated_at=model.updated_at,
                content_preview=(model.latest_snapshot[:200] if model.latest_snapshot else None)
            )

    async def update_snapshot(self, doc_id: UUID, snapshot: str) -> None:
        async with get_session() as session:
            await session.execute(
                update(DocumentModel)
                .where(DocumentModel.id == doc_id)
                .values(latest_snapshot=snapshot)
            )
            await session.commit()
