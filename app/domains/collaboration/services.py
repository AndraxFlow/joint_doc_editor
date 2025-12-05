from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import asyncio
from datetime import datetime, timedelta

from app.db.repositories.collaboration_repository import (
    DocumentSessionRepository, OperationRepository, UserCursorRepository
)
from app.domains.collaboration.entities import (
    DocumentSession, Operation, OperationHistory, OperationType
)
from app.domains.collaboration.schemas import (
    OperationCreate, DocumentSessionCreate, DocumentSessionUpdate,
    DocumentSyncRequest, OperationBatch
)


class CollaborationService:
    """Сервис для управления совместным редактированием"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repository = DocumentSessionRepository(session)
        self.operation_repository = OperationRepository(session)
        self.cursor_repository = UserCursorRepository(session)
        
        # In-memory хранилище для активных сессий и историй операций
        self._active_sessions: Dict[uuid.UUID, DocumentSession] = {}
        self._operation_histories: Dict[uuid.UUID, OperationHistory] = {}
        self._websocket_connections: Dict[uuid.UUID, List] = {}
    
    async def join_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> DocumentSession:
        """Присоединение пользователя к документу"""
        # Проверяем, есть ли уже активная сессия
        existing_session = await self.session_repository.get_by_document_and_user(document_id, user_id)
        
        if existing_session:
            # Обновляем существующую сессию
            existing_session.update_activity()
            await self.session_repository.update(existing_session)
            self._active_sessions[existing_session.uuid] = existing_session
            return existing_session
        
        # Создаем новую сессию
        session = DocumentSession(document_id=document_id, user_id=user_id)
        created_session = await self.session_repository.create(session)
        self._active_sessions[created_session.uuid] = created_session
        
        # Инициализируем историю операций, если нужно
        if document_id not in self._operation_histories:
            self._operation_histories[document_id] = OperationHistory(document_id)
            # Загружаем существующие операции из БД
            await self._load_operation_history(document_id)
        
        return created_session
    
    async def leave_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Выход пользователя из документа"""
        session = await self.session_repository.get_by_document_and_user(document_id, user_id)
        
        if not session:
            return False
        
        session.leave_session()
        await self.session_repository.deactivate_session(session.uuid)
        
        # Удаляем из активных сессий
        if session.uuid in self._active_sessions:
            del self._active_sessions[session.uuid]
        
        # Удаляем курсор
        await self.cursor_repository.remove_cursor(document_id, user_id)
        
        return True
    
    async def apply_operation(self, operation_data: OperationCreate) -> Operation:
        """Применение операции к документу"""
        document_id = operation_data.author_id  # Временно, нужно исправить
        
        # Получаем историю операций
        if document_id not in self._operation_histories:
            self._operation_histories[document_id] = OperationHistory(document_id)
            await self._load_operation_history(document_id)
        
        history = self._operation_histories[document_id]
        
        # Создаем операцию
        operation = Operation(
            operation_type=operation_data.type,
            position=operation_data.position,
            content=operation_data.content,
            length=operation_data.length,
            author_id=operation_data.author_id,
            version=operation_data.version
        )
        
        # Трансформируем операцию относительно существующих
        transformed_operation = history.transform_operation(operation)
        
        # Добавляем в историю
        history.add_operation(transformed_operation)
        
        # Сохраняем в БД
        await self.operation_repository.create(transformed_operation)
        
        # Рассылаем операцию другим пользователям
        await self._broadcast_operation(document_id, transformed_operation)
        
        return transformed_operation
    
    async def update_cursor(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        position: int,
        selection_start: int = None,
        selection_end: int = None
    ) -> None:
        """Обновление позиции курсора пользователя"""
        if selection_start is None:
            selection_start = position
        if selection_end is None:
            selection_end = position
        
        # Получаем сессию пользователя
        session = await self.session_repository.get_by_document_and_user(document_id, user_id)
        if session:
            session.update_cursor(position, selection_start, selection_end)
            await self.session_repository.update(session)
        
        # Обновляем курсор в БД
        await self.cursor_repository.update_cursor(
            document_id=document_id,
            user_id=user_id,
            position=position,
            selection_start=selection_start,
            selection_end=selection_end,
            color=session.color if session else "#FF0000"
        )
        
        # Рассылаем обновление курсора другим пользователям
        await self._broadcast_cursor_update(document_id, user_id, position, selection_start, selection_end)
    
    async def get_active_users(self, document_id: uuid.UUID) -> List[DocumentSession]:
        """Получение списка активных пользователей документа"""
        # Сначала получаем из БД
        db_sessions = await self.session_repository.get_active_sessions(document_id)
        
        # Обновляем in-memory кэш
        for session in db_sessions:
            self._active_sessions[session.uuid] = session
        
        return list(self._active_sessions.values())
    
    async def sync_document(self, sync_request: DocumentSyncRequest) -> Dict[str, Any]:
        """Синхронизация документа для клиента"""
        document_id = sync_request.document_id
        client_version = sync_request.client_version
        
        # Получаем историю операций
        if document_id not in self._operation_histories:
            self._operation_histories[document_id] = OperationHistory(document_id)
            await self._load_operation_history(document_id)
        
        history = self._operation_histories[document_id]
        
        # Получаем операции, которые есть на сервере, но нет у клиента
        pending_operations = history.get_operations_since(client_version)
        
        # Получаем активных пользователей
        active_users = await self.get_active_users(document_id)
        
        # Получаем текущее содержимое документа (здесь нужно будет интегрироваться с DocumentService)
        current_content = ""  # Временно
        
        return {
            "document_id": document_id,
            "current_version": history.current_version,
            "current_content": current_content,
            "pending_operations": pending_operations,
            "active_users": active_users
        }
    
    async def apply_operation_batch(self, batch: OperationBatch) -> Dict[str, Any]:
        """Применение пакета операций"""
        document_id = batch.document_id
        processed_operations = []
        failed_operations = []
        
        # Получаем историю операций
        if document_id not in self._operation_histories:
            self._operation_histories[document_id] = OperationHistory(document_id)
            await self._load_operation_history(document_id)
        
        history = self._operation_histories[document_id]
        
        # Применяем операции по порядку
        for i, op_data in enumerate(batch.operations):
            try:
                operation = Operation(
                    operation_type=op_data.type,
                    position=op_data.position,
                    content=op_data.content,
                    length=op_data.length,
                    author_id=op_data.author_id,
                    version=op_data.version
                )
                
                # Трансформируем относительно предыдущих операций в пакете
                for prev_op in processed_operations:
                    operation = operation.transform(prev_op)
                
                # Трансформируем относительно существующих операций
                transformed_operation = history.transform_operation(operation)
                
                # Добавляем в историю
                history.add_operation(transformed_operation)
                
                # Сохраняем в БД
                await self.operation_repository.create(transformed_operation)
                
                processed_operations.append(transformed_operation)
                
            except Exception as e:
                failed_operations.append({
                    "operation_index": i,
                    "operation_data": op_data.dict(),
                    "error": str(e)
                })
        
        # Рассылаем операции другим пользователям
        for operation in processed_operations:
            await self._broadcast_operation(document_id, operation)
        
        return {
            "batch_id": batch.batch_id,
            "document_id": document_id,
            "processed_operations": processed_operations,
            "failed_operations": failed_operations,
            "final_version": history.current_version
        }
    
    async def get_collaboration_stats(self, document_id: uuid.UUID) -> Dict[str, Any]:
        """Получение статистики совместной работы"""
        # Количество операций
        total_operations = await self.operation_repository.count_operations(document_id)
        
        # Активные пользователи
        active_users = await self.get_active_users(document_id)
        
        # Последняя активность
        last_activity = None
        if active_users:
            last_activity = max(session.last_activity for session in active_users)
        
        # Самый активный пользователь (упрощенно)
        most_active_user = None
        if active_users:
            most_active_user = max(
                active_users, 
                key=lambda s: s.last_activity
            ).user_id
        
        return {
            "document_id": document_id,
            "total_operations": total_operations,
            "active_users": len(active_users),
            "total_editing_time_minutes": 0,  # Нужно будет реализовать
            "most_active_user": most_active_user,
            "last_activity": last_activity or datetime.utcnow()
        }
    
    async def cleanup_inactive_sessions(self) -> int:
        """Очистка неактивных сессий"""
        # Очистка в БД
        db_cleaned = await self.session_repository.cleanup_inactive_sessions(minutes=30)
        
        # Очистка в памяти
        current_time = datetime.utcnow()
        inactive_sessions = [
            uuid for uuid, session in self._active_sessions.items()
            if current_time - session.last_activity > timedelta(minutes=30)
        ]
        
        for session_uuid in inactive_sessions:
            del self._active_sessions[session_uuid]
        
        # Очистка старых курсоров
        cursor_cleaned = await self.cursor_repository.cleanup_old_cursors(minutes=10)
        
        return db_cleaned + len(inactive_sessions) + cursor_cleaned
    
    async def _load_operation_history(self, document_id: uuid.UUID) -> None:
        """Загрузка истории операций из БД"""
        operations = await self.operation_repository.get_by_document(document_id, limit=1000)
        
        history = self._operation_histories[document_id]
        history.clear()
        
        for operation in operations:
            history.add_operation(operation)
    
    async def _broadcast_operation(self, document_id: uuid.UUID, operation: Operation) -> None:
        """Рассылка операции другим пользователям"""
        # Здесь будет интеграция с WebSocket
        # Временно просто логируем
        print(f"Broadcasting operation {operation} to document {document_id}")
    
    async def _broadcast_cursor_update(
        self, 
        document_id: uuid.UUID, 
        user_id: uuid.UUID,
        position: int,
        selection_start: int,
        selection_end: int
    ) -> None:
        """Рассылка обновления курсора другим пользователям"""
        # Здесь будет интеграция с WebSocket
        # Временно просто логируем
        print(f"Broadcasting cursor update for user {user_id} in document {document_id}: pos={position}")


class OperationalTransformationService:
    """Сервис для алгоритмов Operational Transformation"""
    
    @staticmethod
    def transform_operations(op1: Operation, op2: Operation) -> tuple[Operation, Operation]:
        """Трансформация двух concurrent операций"""
        transformed1 = op1.transform(op2)
        transformed2 = op2.transform(op1)
        
        return transformed1, transformed2
    
    @staticmethod
    def compose_operations(op1: Operation, op2: Operation) -> Operation:
        """Композиция двух операций"""
        # Упрощенная реализация композиции
        if op1.operation_type == OperationType.INSERT and op2.operation_type == OperationType.INSERT:
            if op1.position <= op2.position:
                return Operation(
                    operation_type=OperationType.INSERT,
                    position=op1.position,
                    content=op1.content + op2.content,
                    author_id=op1.author_id
                )
            else:
                return Operation(
                    operation_type=OperationType.INSERT,
                    position=op2.position,
                    content=op2.content + op1.content,
                    author_id=op2.author_id
                )
        
        # Для других случаев возвращаем вторую операцию
        return op2
    
    @staticmethod
    def invert_operation(operation: Operation, text_length: int) -> Operation:
        """Инвертирование операции (для undo)"""
        if operation.operation_type == OperationType.INSERT:
            return Operation(
                operation_type=OperationType.DELETE,
                position=operation.position,
                length=len(operation.content),
                author_id=operation.author_id
            )
        elif operation.operation_type == OperationType.DELETE:
            # Для delete нужно знать содержимое, которое было удалено
            # Упрощенная реализация
            return Operation(
                operation_type=OperationType.INSERT,
                position=operation.position,
                content="",  # Нужно восстановить удаленный текст
                author_id=operation.author_id
            )
        
        return operation