from fastapi import APIRouter
from app.api.v1 import identity, documents, collaboration

api_router = APIRouter()
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(collaboration.router, prefix="/collaboration", tags=["collaboration"])
