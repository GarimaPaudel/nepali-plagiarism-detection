from pydantic import BaseModel
import uuid
from datetime import datetime


class CreateSubmission(BaseModel):
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    content: str


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime
