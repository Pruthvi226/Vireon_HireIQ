from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from auth.auth_service import authenticate_user, create_password_reset_token, issue_refresh_token, public_user, register_user, reset_password, revoke_refresh_tokens, rotate_refresh_token
from auth.dependencies import get_current_user
from auth.security import create_access_token
from app.config import DEVELOPMENT
from schemas.auth_schema import AuthResponse, LoginRequest, PasswordResetConfirm, PasswordResetRequest, RefreshRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> dict:
    if payload.role != "CANDIDATE":
        raise HTTPException(status_code=403, detail="Staff accounts must be provisioned by an administrator")
    user = register_user(payload)
    token = create_access_token(str(user["id"]), {"role": user["role"], "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "refresh_token": issue_refresh_token(user["id"]), "user": public_user(user)}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> dict:
    user = authenticate_user(payload)
    token = create_access_token(str(user["id"]), {"role": user["role"], "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "refresh_token": issue_refresh_token(user["id"]), "user": public_user(user)}


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest) -> dict:
    user = rotate_refresh_token(payload.refresh_token)
    token = create_access_token(str(user["id"]), {"role": user["role"], "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "refresh_token": issue_refresh_token(user["id"]), "user": public_user(user)}


@router.post("/logout")
def logout(user: dict = Depends(get_current_user)) -> dict:
    revoke_refresh_tokens(user["id"])
    return {"message": "Logged out"}


@router.post("/password-reset/request")
def request_password_reset(payload: PasswordResetRequest) -> dict:
    if not DEVELOPMENT:
        raise HTTPException(status_code=503, detail="Password reset delivery is not configured; contact the workspace administrator")
    token = create_password_reset_token(payload.email)
    return {"message": "If the account exists, a reset token has been issued", "reset_token": token if os.getenv("APP_ENV", "local").lower() in {"local", "dev", "development", "test"} else None}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm) -> dict:
    reset_password(payload.token, payload.password)
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> dict:
    return user
