from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import uuid
import json
import asyncio

from app.core.db import get_db
from app.domains.collaboration.schemas import (
    OperationCreate, OperationResponse, DocumentSessionResponse,
    ActiveUsersResponse, DocumentSyncRequest, DocumentSyncResponse,
    CollaborationStatsResponse, OperationBatch, OperationBatchResponse
)
from app.domains.collaboration.services import CollaborationService, OperationalTransformationService
from app.domains.identity.entities import User

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# Глобальное хранилище для WebSocket соединений
websocket_connections: Dict[uuid.UUID, List[WebSocket]] = {}


@router.post("/documents/{document_uuid}/join", response_model=DocumentSessionResponse)
async def join_document(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Присоединение к совместному редактированию документа"""
    collaboration_service = CollaborationService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    session = await collaboration_service.join_document(document_uuid, default_user_uuid)
    
    return DocumentSessionResponse(
        uuid=session.uuid,
        document_id=session.document_id,
        user_id=session.user_id,
        cursor_position=session.cursor_position,
        selection_start=session.selection_start,
        selection_end=session.selection_end,
        color=session.color,
        joined_at=session.joined_at,
        last_activity=session.last_activity,
        is_active=session.is_active
    )


@router.post("/documents/{document_uuid}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_document(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Выход из совместного редактирования документа"""
    collaboration_service = CollaborationService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    success = await collaboration_service.leave_document(document_uuid, default_user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )


@router.post("/documents/{document_uuid}/operations", response_model=OperationResponse)
async def apply_operation(
    document_uuid: uuid.UUID,
    operation_data: OperationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Применение операции к документу"""
    collaboration_service = CollaborationService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    operation_data.author_id = default_user_uuid
    
    try:
        operation = await collaboration_service.apply_operation(operation_data)
        
        return OperationResponse(
            uuid=operation.uuid,
            type=operation.operation_type,
            position=operation.position,
            content=operation.content,
            length=operation.length,
            author_id=operation.author_id,
            timestamp=operation.timestamp,
            version=operation.version
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to apply operation: {str(e)}"
        )


@router.post("/documents/{document_uuid}/operations/batch", response_model=OperationBatchResponse)
async def apply_operation_batch(
    document_uuid: uuid.UUID,
    batch: OperationBatch,
    db: AsyncSession = Depends(get_db)
):
    """Применение пакета операций"""
    collaboration_service = CollaborationService(db)
    
    # Устанавливаем document_id в batch
    batch.document_id = document_uuid
    
    try:
        result = await collaboration_service.apply_operation_batch(batch)
        
        processed_operations = [
            OperationResponse(
                uuid=op.uuid,
                type=op.operation_type,
                position=op.position,
                content=op.content,
                length=op.length,
                author_id=op.author_id,
                timestamp=op.timestamp,
                version=op.version
            )
            for op in result["processed_operations"]
        ]
        
        return OperationBatchResponse(
            batch_id=result["batch_id"],
            document_id=result["document_id"],
            processed_operations=processed_operations,
            failed_operations=result["failed_operations"],
            final_version=result["final_version"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to apply operation batch: {str(e)}"
        )


@router.post("/documents/{document_uuid}/sync", response_model=DocumentSyncResponse)
async def sync_document(
    document_uuid: uuid.UUID,
    sync_request: DocumentSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """Синхронизация документа"""
    collaboration_service = CollaborationService(db)
    
    sync_request.document_id = document_uuid
    
    try:
        sync_data = await collaboration_service.sync_document(sync_request)
        
        pending_operations = [
            OperationResponse(
                uuid=op.uuid,
                type=op.operation_type,
                position=op.position,
                content=op.content,
                length=op.length,
                author_id=op.author_id,
                timestamp=op.timestamp,
                version=op.version
            )
            for op in sync_data["pending_operations"]
        ]
        
        active_users = [
            DocumentSessionResponse(
                uuid=session.uuid,
                document_id=session.document_id,
                user_id=session.user_id,
                cursor_position=session.cursor_position,
                selection_start=session.selection_start,
                selection_end=session.selection_end,
                color=session.color,
                joined_at=session.joined_at,
                last_activity=session.last_activity,
                is_active=session.is_active
            )
            for session in sync_data["active_users"]
        ]
        
        return DocumentSyncResponse(
            document_id=sync_data["document_id"],
            current_version=sync_data["current_version"],
            current_content=sync_data["current_content"],
            pending_operations=pending_operations,
            active_users=active_users
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync document: {str(e)}"
        )


@router.get("/documents/{document_uuid}/users", response_model=ActiveUsersResponse)
async def get_active_users(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка активных пользователей документа"""
    collaboration_service = CollaborationService(db)
    
    active_sessions = await collaboration_service.get_active_users(document_uuid)
    
    active_users = [
        DocumentSessionResponse(
            uuid=session.uuid,
            document_id=session.document_id,
            user_id=session.user_id,
            cursor_position=session.cursor_position,
            selection_start=session.selection_start,
            selection_end=session.selection_end,
            color=session.color,
            joined_at=session.joined_at,
            last_activity=session.last_activity,
            is_active=session.is_active
        )
        for session in active_sessions
    ]
    
    return ActiveUsersResponse(
        document_id=document_uuid,
        active_sessions=active_users,
        total_users=len(active_users)
    )


@router.post("/documents/{document_uuid}/cursor")
async def update_cursor(
    document_uuid: uuid.UUID,
    cursor_data: Dict[str, int],
    db: AsyncSession = Depends(get_db)
):
    """Обновление позиции курсора"""
    collaboration_service = CollaborationService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    
    position = cursor_data.get("position", 0)
    selection_start = cursor_data.get("selection_start", position)
    selection_end = cursor_data.get("selection_end", position)
    
    await collaboration_service.update_cursor(
        document_uuid,
        default_user_uuid,
        position,
        selection_start,
        selection_end
    )
    
    return {"message": "Cursor updated successfully"}


@router.get("/documents/{document_uuid}/stats", response_model=CollaborationStatsResponse)
async def get_collaboration_stats(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получение статистики совместной работы"""
    collaboration_service = CollaborationService(db)
    
    stats = await collaboration_service.get_collaboration_stats(document_uuid)
    
    return CollaborationStatsResponse(**stats)


# WebSocket функциональность перенесена в app/api/ws/sync.py