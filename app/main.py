from fastapi import FastAPI
from app.api.http.health import router as health_router
from app.domains.identity.router import router as identity_router

app = FastAPI(title="DocCollab")

app.include_router(health_router)
app.include_router(identity_router)
