from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime, timedelta

from app.db.models.collaboration import (
    DocumentSession as DocumentSessionModel,
    Operation as OperationModel,
    UserCursor as UserCursorModel
)

if TYPE_CHECKING:
    from app.domains.collaboration.entities import DocumentSession, Operation


class DocumentSessionRepository:
    """Репозиторий для работы с сессиями документов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, session: "DocumentSession") -> "DocumentSession":
        """Создание новой сессии"""
        db_session = DocumentSessionModel(
            uuid=session.uuid,
            document_id=session.document_id,
            user_id=session.user_id,
            cursor_position=session.cursor_position,
            is_active=session.is_active,
            last_activity=session.last_activity
        )
        
        self.session.add(db_session)
        await self.session.commit()
        await self.session.refresh(db_session)
        return self._to_domain(db_session)
    
    async def get_by_uuid(self, session_uuid: uuid.UUID) -> Optional["DocumentSession"]:
        """Получение сессии по UUID"""
        result = await self.session.execute(
            select(DocumentSessionModel).where(DocumentSessionModel.uuid == session_uuid)
        )
        db_session = result.scalar_one_or_none()
        return self._to_domain(db_session) if db_session else None
    
    async def get_by_document_and_user(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional["DocumentSession"]:
        """Получение сессии по документу и пользователю"""
        result = await self.session.execute(
            select(DocumentSessionModel).where(
                and_(
                    DocumentSessionModel.document_id == document_id,
                    DocumentSessionModel.user_id == user_id,
                    DocumentSessionModel.is_active == True
                )
            )
        )
        db_session = result.scalar_one_or_none()
        return self._to_domain(db_session) if db_session else None
    
    async def get_active_sessions(self, document_id: uuid.UUID) -> List["DocumentSession"]:
        """Получение активных сессий документа"""
        result = await self.session.execute(
            select(DocumentSessionModel)
            .where(
                and_(
                    DocumentSessionModel.document_id == document_id,
                    DocumentSessionModel.is_active == True
                )
            )
            .order_by(DocumentSessionModel.last_activity.desc())
        )
        db_sessions = result.scalars().all()
        return [self._to_domain(session) for session in db_sessions]
    
    async def update(self, session: "DocumentSession") -> "DocumentSession":
        """Обновление сессии"""
        stmt = (
            update(DocumentSessionModel)
            .where(DocumentSessionModel.uuid == session.uuid)
            .values(
                cursor_position=session.cursor_position,
                is_active=session.is_active,
                last_activity=session.last_activity
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_by_uuid(session.uuid)
    
    async def deactivate_session(self, session_uuid: uuid.UUID) -> bool:
        """Деактивация сессии"""
        stmt = (
            update(DocumentSessionModel)
            .where(DocumentSessionModel.uuid == session_uuid)
            .values(is_active=False, last_activity=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def cleanup_inactive_sessions(self, minutes: int = 30) -> int:
        """Очистка неактивных сессий"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        stmt = (
            update(DocumentSessionModel)
            .where(DocumentSessionModel.last_activity < cutoff_time)
            .where(DocumentSessionModel.is_active == True)
            .values(is_active=False)
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def count_active_sessions(self, document_id: uuid.UUID) -> int:
        """Подсчет активных сессий документа"""
        result = await self.session.execute(
            select(func.count(DocumentSessionModel.uuid))
            .where(
                and_(
                    DocumentSessionModel.document_id == document_id,
                    DocumentSessionModel.is_active == True
                )
            )
        )
        return result.scalar()
    
    def _to_domain(self, db_session: DocumentSessionModel) -> "DocumentSession":
        """Преобразование модели БД в доменную сущность"""
        from app.domains.collaboration.entities import DocumentSession
        
        session = DocumentSession(
            document_id=db_session.document_id,
            user_id=db_session.user_id,
            cursor_position=db_session.cursor_position
        )
        session.uuid = db_session.uuid
        session.joined_at = db_session.created_at
        session.last_activity = db_session.last_activity
        session.is_active = db_session.is_active
        
        return session


class OperationRepository:
    """Репозиторий для работы с операциями"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, operation: "Operation") -> "Operation":
        """Создание новой операции"""
        db_operation = OperationModel(
            uuid=operation.uuid,
            document_id=operation.author_id,  # Временно, нужно исправить
            user_id=operation.author_id,
            operation_type=operation.operation_type.value,
            position=operation.position,
            content=operation.content,
            length=operation.length,
            version=operation.version,
            timestamp=operation.timestamp
        )
        
        self.session.add(db_operation)
        await self.session.commit()
        await self.session.refresh(db_operation)
        return self._to_domain(db_operation)
    
    async def get_by_uuid(self, operation_uuid: uuid.UUID) -> Optional["Operation"]:
        """Получение операции по UUID"""
        result = await self.session.execute(
            select(OperationModel).where(OperationModel.uuid == operation_uuid)
        )
        db_operation = result.scalar_one_or_none()
        return self._to_domain(db_operation) if db_operation else None
    
    async def get_by_document(
        self,
        document_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List["Operation"]:
        """Получение операций документа"""
        result = await self.session.execute(
            select(OperationModel)
            .where(OperationModel.document_id == document_id)
            .order_by(OperationModel.version.asc())
            .offset(offset)
            .limit(limit)
        )
        db_operations = result.scalars().all()
        return [self._to_domain(op) for op in db_operations]
    
    async def get_operations_since(
        self,
        document_id: uuid.UUID,
        version: int
    ) -> List["Operation"]:
        """Получение операций с указанной версии"""
        result = await self.session.execute(
            select(OperationModel)
            .where(
                and_(
                    OperationModel.document_id == document_id,
                    OperationModel.version > version
                )
            )
            .order_by(OperationModel.version.asc())
        )
        db_operations = result.scalars().all()
        return [self._to_domain(op) for op in db_operations]
    
    async def get_latest_version(self, document_id: uuid.UUID) -> int:
        """Получение последней версии документа"""
        result = await self.session.execute(
            select(func.coalesce(func.max(OperationModel.version), 0))
            .where(OperationModel.document_id == document_id)
        )
        return result.scalar() or 0
    
    async def count_operations(self, document_id: uuid.UUID) -> int:
        """Подсчет количества операций документа"""
        result = await self.session.execute(
            select(func.count(OperationModel.uuid))
            .where(OperationModel.document_id == document_id)
        )
        return result.scalar()
    
    async def delete_old_operations(self, document_id: uuid.UUID, keep_last: int = 1000) -> int:
        """Удаление старых операций, оставляя только последние"""
        # Получаем версию, после которой нужно удалить
        result = await self.session.execute(
            select(OperationModel.version)
            .where(OperationModel.document_id == document_id)
            .order_by(OperationModel.version.desc())
            .offset(keep_last)
            .limit(1)
        )
        cutoff_version = result.scalar_one_or_none()
        
        if cutoff_version is None:
            return 0
        
        stmt = delete(OperationModel).where(
            and_(
                OperationModel.document_id == document_id,
                OperationModel.version <= cutoff_version
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    def _to_domain(self, db_operation: OperationModel) -> "Operation":
        """Преобразование модели БД в доменную сущность"""
        from app.domains.collaboration.entities import OperationType, Operation
        
        operation = Operation(
            operation_type=OperationType(db_operation.operation_type),
            position=db_operation.position,
            content=db_operation.content or "",
            length=db_operation.length or 0,
            author_id=db_operation.user_id,
            timestamp=db_operation.timestamp,
            version=db_operation.version
        )
        operation.uuid = db_operation.uuid
        
        return operation


class UserCursorRepository:
    """Репозиторий для работы с курсорами пользователей"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def update_cursor(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        position: int,
        selection_start: int,
        selection_end: int,
        color: str = "#FF0000"
    ) -> None:
        """Обновление позиции курсора пользователя"""
        # Сначала пытаемся обновить существующий курсор
        stmt = (
            update(UserCursorModel)
            .where(
                and_(
                    UserCursorModel.document_id == document_id,
                    UserCursorModel.user_id == user_id
                )
            )
            .values(
                position=position,
                selection_start=selection_start,
                selection_end=selection_end,
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.session.execute(stmt)
        
        # Если курсор не найден, создаем новый
        if result.rowcount == 0:
            db_cursor = UserCursorModel(
                document_id=document_id,
                user_id=user_id,
                position=position,
                selection_start=selection_start,
                selection_end=selection_end,
                color=color
            )
            self.session.add(db_cursor)
        
        await self.session.commit()
    
    async def get_active_cursors(self, document_id: uuid.UUID) -> List[dict]:
        """Получение активных курсоров документа"""
        result = await self.session.execute(
            select(UserCursorModel)
            .where(UserCursorModel.document_id == document_id)
            .order_by(UserCursorModel.updated_at.desc())
        )
        
        cursors = []
        for cursor in result.scalars().all():
            # Проверяем, что курсор обновлялся недавно (например, последние 5 минут)
            if cursor.updated_at > datetime.utcnow() - timedelta(minutes=5):
                cursors.append({
                    "user_id": cursor.user_id,
                    "position": cursor.position,
                    "selection_start": cursor.selection_start,
                    "selection_end": cursor.selection_end,
                    "color": cursor.color,
                    "updated_at": cursor.updated_at
                })
        
        return cursors
    
    async def remove_cursor(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Удаление курсора пользователя"""
        stmt = delete(UserCursorModel).where(
            and_(
                UserCursorModel.document_id == document_id,
                UserCursorModel.user_id == user_id
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def cleanup_old_cursors(self, minutes: int = 10) -> int:
        """Очистка старых курсоров"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        stmt = delete(UserCursorModel).where(UserCursorModel.updated_at < cutoff_time)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount