from pydantic import BaseModel
import uuid
from datetime import datetime


class CreateAssignment(BaseModel):
    topic: str
    description: str | None = None
    due_date: datetime


class UpdateAssignment(BaseModel):
    topic: str | None = None
    description: str | None = None
    due_date: datetime | None = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    topic: str
    description: str | None
    created_by: uuid.UUID
    due_date: datetime
    created_at: datetime
    updated_at: datetime


