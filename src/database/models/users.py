from src.database.models.base import Base
from enum import Enum
from sqlmodel import Column, Field, Relationship
from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid
import sqlalchemy as sa

if TYPE_CHECKING:
    from src.database.models.submission import Submission
    from src.database.models.assignment import Assignment


class UserRole(str, Enum):
    teacher = "teacher"
    student = "student"


class Users(Base, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    username: str = Field(nullable=False, unique=True, index=True)
    hashed_password: str = Field(nullable=False)
    role: UserRole = Field(nullable=False)
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

    assignments: list["Assignment"] = Relationship(back_populates="creator")
    submissions: list["Submission"] = Relationship(back_populates="student")
