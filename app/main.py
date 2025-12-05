from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.http.health import router as health_router
from app.api.http.auth import router as auth_router
from app.api.http.users import router as users_router
from app.api.http.documents import router as documents_router
from app.api.http.collaboration import router as collaboration_router
from app.api.ws.sync import router as websocket_router

app = FastAPI(
    title="DocCollab",
    description="Веб-приложение для совместного редактирования документов",
    version="1.0.0"
)

# Настройка CORS для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы без кэширования для разработки
if os.path.exists("app/static"):
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            response = await super().get_response(path, scope)
            if response:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            return response
    
    app.mount("/static", NoCacheStaticFiles(directory="app/static"), name="static")

# Подключаем роутеры
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(collaboration_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Корневой эндпоинт - отдаем главную страницу"""
    if os.path.exists("app/static/index.html"):
        return FileResponse("app/static/index.html")
    return {
        "message": "DocCollab API",
        "version": "1.0.0",
        "description": "Веб-приложение для совместного редактирования документов",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/app")
async def app_page():
    """Эндпоинт для приложения"""
    if os.path.exists("app/static/index.html"):
        return FileResponse("app/static/index.html")
    return {"error": "Frontend not found"}
