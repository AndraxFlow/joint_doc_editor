from fastapi import FastAPI
from app.api.http.health import router as health_router

app = FastAPI(title="DocCollab")

app.include_router(health_router)
