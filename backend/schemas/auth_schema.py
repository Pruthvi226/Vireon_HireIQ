from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


Role = Literal["ADMIN", "RECRUITER", "CANDIDATE"]


class PasswordInput(BaseModel):
    @field_validator("password", check_fields=False)
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class RegisterRequest(PasswordInput):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Role = "CANDIDATE"
    company_name: str | None = Field(default=None, max_length=160)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least two non-whitespace characters")
        return value


class LoginRequest(PasswordInput):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=200)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(PasswordInput):
    token: str = Field(..., min_length=20, max_length=200)
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    company_name: str | None = None
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    user: UserResponse
