from pydantic import BaseModel
import uuid
from datetime import datetime


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    original_filename: str | None
    file_path: str | None
    created_at: datetime
    updated_at: datetime


class PlagiarismResultResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    # corpus comparison
    reference_filename: str | None
    # peer comparison
    reference_submission_id: uuid.UUID | None
    tfidf_similarity: float | None
    xlm_similarity: float | None
    is_plagiarized: bool | None
    matched_sentences: list | None
    task_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckStatusResponse(BaseModel):
    submission_id: uuid.UUID
    overall_status: str          # pending | running | done | failed
    max_tfidf_similarity: float | None
    results: list[PlagiarismResultResponse]
