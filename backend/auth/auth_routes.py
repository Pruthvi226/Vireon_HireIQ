from __future__ import annotations

from fastapi import APIRouter, Depends

from auth.auth_service import authenticate_user, public_user, register_user
from auth.dependencies import get_current_user
from auth.security import create_access_token
from schemas.auth_schema import AuthResponse, LoginRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> dict:
    user = register_user(payload)
    token = create_access_token(str(user["id"]), {"role": user["role"], "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> dict:
    user = authenticate_user(payload)
    token = create_access_token(str(user["id"]), {"role": user["role"], "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> dict:
    return user
