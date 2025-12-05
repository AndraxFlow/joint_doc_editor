from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid

from app.core.db import get_db
from app.domains.documents.schemas import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    DocumentSearchRequest, DocumentSearchResponse, DocumentStatsResponse,
    DocumentExportRequest, DocumentExportResponse
)
from app.domains.documents.services import DocumentService, DocumentVersionService
from app.domains.identity.entities import User

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание нового документа"""
    document_service = DocumentService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    document = await document_service.create_document(document_data, default_user_uuid)
    
    return DocumentResponse(
        uuid=document.uuid,
        title=document.title,
        content=document.content,
        version=document.version,
        owner_id=document.owner_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        word_count=document.get_word_count(),
        content_length=document.get_content_length()
    )


@router.get("/", response_model=DocumentListResponse)
async def get_user_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка документов"""
    document_service = DocumentService(db)
    
    offset = (page - 1) * per_page
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    documents = await document_service.get_user_documents(
        default_user_uuid,
        limit=per_page,
        offset=offset
    )
    
    # Получаем общее количество документов
    from app.db.repositories.document_repository import DocumentRepository
    repo = DocumentRepository(db)
    total = await repo.count_by_owner(default_user_uuid)
    
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
    
    return DocumentListResponse(
        documents=document_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{document_uuid}", response_model=DocumentResponse)
async def get_document(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получение документа по UUID"""
    document_service = DocumentService(db)
    
    document = await document_service.get_document(document_uuid)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse(
        uuid=document.uuid,
        title=document.title,
        content=document.content,
        version=document.version,
        owner_id=document.owner_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        word_count=document.get_word_count(),
        content_length=document.get_content_length()
    )


@router.put("/{document_uuid}", response_model=DocumentResponse)
async def update_document(
    document_uuid: uuid.UUID,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление документа"""
    document_service = DocumentService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    
    try:
        document = await document_service.update_document(
            document_uuid,
            update_data,
            default_user_uuid
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResponse(
            uuid=document.uuid,
            title=document.title,
            content=document.content,
            version=document.version,
            owner_id=document.owner_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            word_count=document.get_word_count(),
            content_length=document.get_content_length()
        )
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{document_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удаление документа"""
    document_service = DocumentService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    
    try:
        success = await document_service.delete_document(document_uuid, default_user_uuid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_request: DocumentSearchRequest,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Поиск документов"""
    document_service = DocumentService(db)
    
    offset = (page - 1) * per_page
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    documents, search_time = await document_service.search_documents(
        search_request,
        user_id=default_user_uuid,
        limit=per_page,
        offset=offset
    )
    
    # Получаем общее количество результатов
    from app.db.repositories.document_repository import DocumentRepository
    repo = DocumentRepository(db)
    total_found = await repo.count_search_results(
        search_request.query,
        default_user_uuid,
        search_request.search_in_title,
        search_request.search_in_content
    )
    
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
    
    return DocumentSearchResponse(
        documents=document_responses,
        total_found=total_found,
        query=search_request.query,
        search_time_ms=search_time
    )


@router.get("/{document_uuid}/stats", response_model=DocumentStatsResponse)
async def get_document_stats(
    document_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получение статистики документа"""
    document_service = DocumentService(db)
    
    stats = await document_service.get_document_stats(document_uuid)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentStatsResponse(**stats)


@router.post("/{document_uuid}/export", response_model=DocumentExportResponse)
async def export_document(
    document_uuid: uuid.UUID,
    export_request: DocumentExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Экспорт документа"""
    document_service = DocumentService(db)
    
    export_data = await document_service.export_document(
        document_uuid,
        export_request.format,
        export_request.include_versions
    )
    
    if not export_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentExportResponse(**export_data)


# Версии документов
@router.get("/{document_uuid}/versions")
async def get_document_versions(
    document_uuid: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Получение версий документа"""
    document_service = DocumentService(db)
    version_service = DocumentVersionService(db)
    
    offset = (page - 1) * per_page
    versions = await version_service.get_document_versions(document_uuid, per_page, offset)
    
    from app.domains.documents.schemas import DocumentVersionResponse
    version_responses = [
        DocumentVersionResponse(
            uuid=version.uuid,
            document_id=version.document_id,
            content=version.content,
            version_number=version.version_number,
            created_by=version.created_by,
            created_at=version.created_at,
            word_count=len(version.content.split()) if version.content else 0,
            content_length=len(version.content)
        )
        for version in versions
    ]
    
    return {
        "versions": version_responses,
        "page": page,
        "per_page": per_page
    }


@router.post("/{document_uuid}/versions/{version_number}/restore")
async def restore_document_version(
    document_uuid: uuid.UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db)
):
    """Восстановление документа из версии"""
    document_service = DocumentService(db)
    version_service = DocumentVersionService(db)
    
    # Используем существующего пользователя для демонстрации
    default_user_uuid = uuid.UUID("c1de4629-e46b-4baf-b401-da37097508f7")
    
    try:
        document = await version_service.restore_version(
            document_uuid,
            version_number,
            default_user_uuid
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document or version not found"
            )
        
        return DocumentResponse(
            uuid=document.uuid,
            title=document.title,
            content=document.content,
            version=document.version,
            owner_id=document.owner_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            word_count=document.get_word_count(),
            content_length=document.get_content_length()
        )
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )