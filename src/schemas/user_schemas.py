from pydantic import BaseModel, EmailStr
from src.database.models.users import UserRole
import uuid
from datetime import datetime


class RegisterTeacher(BaseModel):
    username: str
    email: EmailStr
    password: str


class CreateStudent(BaseModel):
    username: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
