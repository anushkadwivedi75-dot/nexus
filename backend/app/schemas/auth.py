from datetime import datetime
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field
from app.schemas.user import EmailType, UserResponse

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class APIErrorDetails(BaseModel):
    code: str
    message: str
    details: dict | list | None = None


class APIErrorResponse(BaseModel):
    success: bool = False
    error: APIErrorDetails


class RegisterRequest(BaseModel):
    email: EmailType
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailType
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class SessionResponse(BaseModel):
    family_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    is_current: bool = False
