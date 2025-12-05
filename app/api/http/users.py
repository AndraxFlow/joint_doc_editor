from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.core.db import get_db
from app.domains.identity.schemas import UserResponse
from app.domains.identity.services import IdentityService
from app.domains.identity.entities import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка пользователей"""
    identity_service = IdentityService(db)
    
    offset = (page - 1) * per_page
    users = await identity_service.list_users(limit=per_page, offset=offset)
    
    user_responses = [
        UserResponse(
            uuid=user.uuid,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            word_count=0,  # Для пользователей не применимо
            content_length=0  # Для пользователей не применимо
        )
        for user in users
    ]
    
    return user_responses


@router.get("/{user_uuid}", response_model=UserResponse)
async def get_user(
    user_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о пользователе"""
    identity_service = IdentityService(db)
    
    user = await identity_service.get_user_by_uuid(user_uuid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        uuid=user.uuid,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        word_count=0,
        content_length=0
    )


@router.get("/{user_uuid}/documents")
async def get_user_documents(
    user_uuid: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Получение документов пользователя"""
    from app.domains.documents.services import DocumentService
    document_service = DocumentService(db)
    
    offset = (page - 1) * per_page
    documents = await document_service.get_user_documents(
        user_uuid,
        limit=per_page,
        offset=offset
    )
    
    from app.domains.documents.schemas import DocumentResponse
    
    document_responses = [
        DocumentResponse(
            uuid=doc.uuid,
            title=doc.title,
            content=doc.content,
            version=doc.version,
            owner_id=doc.owner_id,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            word_count=doc.get_word_count(),
            content_length=doc.get_content_length()
        )
        for doc in documents
    ]
    
    # Получаем общее количество документов
    from app.db.repositories.document_repository import DocumentRepository
    repo = DocumentRepository(db)
    total = await repo.count_by_owner(user_uuid)
    
    return {
        "documents": document_responses,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.post("/{user_uuid}/deactivate")
async def deactivate_user(
    user_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Деактивация пользователя"""
    identity_service = IdentityService(db)
    
    success = await identity_service.deactivate_user(user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_uuid}/activate")
async def activate_user(
    user_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Активация пользователя"""
    identity_service = IdentityService(db)
    
    success = await identity_service.activate_user(user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User activated successfully"}


@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удаление пользователя"""
    identity_service = IdentityService(db)
    
    success = await identity_service.delete_user(user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )