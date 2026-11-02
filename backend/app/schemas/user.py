import re
import uuid
from datetime import datetime
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_str(v: str) -> str:
    if not isinstance(v, str) or not EMAIL_REGEX.match(v.strip()):
        raise ValueError("Invalid email address format")
    return v.lower().strip()


EmailType = Annotated[str, AfterValidator(validate_email_str)]


class UserBase(BaseModel):
    email: EmailType
    full_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = Field(None, max_length=512)
    bio: str | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avatar_url: str | None = None
    bio: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
