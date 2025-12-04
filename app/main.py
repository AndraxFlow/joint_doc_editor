from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="DocCollab")

# Подключаем главный роутер
app.include_router(api_router, prefix="/api/v1")
