from src.database.models.base import Base
from sqlmodel import Column, Field, Relationship
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.database.models.assignment import Assignment
    from src.database.models.users import Users
import uuid
import sqlalchemy as sa


class Submission(Base, table=True):
    __tablename__ = "submissions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    assignment_id: uuid.UUID = Field(foreign_key="assignments.id", nullable=False)
    student_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    original_filename: Optional[str] = Field(default=None, nullable=True)
    file_path: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    assignment: Optional["Assignment"] = Relationship(back_populates="submissions")
    student: Optional["Users"] = Relationship(back_populates="submissions")
    plagiarism_results: list["PlagiarismResult"] = Relationship(
        back_populates="submission",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "[PlagiarismResult.submission_id]"},
    )


class PlagiarismResult(Base, table=True):
    __tablename__ = "plagiarism_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    submission_id: uuid.UUID = Field(foreign_key="submissions.id", nullable=False)
    # corpus comparison — set when checking against a corpus file
    reference_filename: Optional[str] = Field(default=None, nullable=True)
    # peer comparison — set when checking against another student's submission
    reference_submission_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="submissions.id", nullable=True
    )
    tfidf_similarity: Optional[float] = Field(default=None)
    xlm_similarity: Optional[float] = Field(default=None)
    is_plagiarized: Optional[bool] = Field(default=None)
    matched_sentences: Optional[list] = Field(default=None, sa_column=Column(sa.JSON))
    task_id: Optional[str] = Field(default=None)
    status: str = Field(default="pending")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    submission: Optional["Submission"] = Relationship(
        back_populates="plagiarism_results",
        sa_relationship_kwargs={"foreign_keys": "[PlagiarismResult.submission_id]"},
    )
