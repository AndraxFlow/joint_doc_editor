from app.api.http.health import router as health_router
from app.api.http.auth import router as auth_router
from app.api.http.users import router as users_router
from app.api.http.documents import router as documents_router
from app.api.http.collaboration import router as collaboration_router

__all__ = [
    "health_router",
    "auth_router", 
    "users_router",
    "documents_router",
    "collaboration_router"
]