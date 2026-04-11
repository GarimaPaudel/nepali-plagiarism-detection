from pydantic import BaseModel
from src.database.models.users import UserRole
import uuid
from datetime import datetime


class CreateUser(BaseModel):
    username: str
    password: str
    role: UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
