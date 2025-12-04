from fastapi import APIRouter, Depends
from app.domains.identity.schemas import UserCreate, UserLogin, UserOut
from app.domains.identity.services import IdentityService
from app.core.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserOut)
async def register(data: UserCreate):
    user = await IdentityService.register(data.email, data.password)
    return user

@router.post("/login")
async def login(data: UserLogin):
    token, user = await IdentityService.login(data.email, data.password)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return user
