from src.database.models.base import Base
from sqlmodel import Column, Field, Relationship
from datetime import UTC, datetime
from typing import Optional, TYPE_CHECKING
import uuid
import sqlalchemy as sa

if TYPE_CHECKING:
    from src.database.models.submission import Submission
    from src.database.models.users import Users

class Assignment(Base, table=True):
    __tablename__ = "assignments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    topic: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    due_date: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False)
    )
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

    creator: Optional["Users"] = Relationship(back_populates="assignments")
    submissions: list["Submission"] = Relationship(back_populates="assignment")
