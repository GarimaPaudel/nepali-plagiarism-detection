from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.models.submission import Submission
from src.schemas.submission_schemas import CreateSubmission
import uuid


async def create_submission(session: AsyncSession, details: CreateSubmission) -> Submission:
    submission = Submission(
        assignment_id=details.assignment_id,
        student_id=details.student_id,
        content=details.content,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return submission


async def get_submission(session: AsyncSession, submission_id: uuid.UUID) -> Submission | None:
    result = await session.exec(select(Submission).where(Submission.id == submission_id))
    return result.first()


async def get_submissions_by_assignment(
    session: AsyncSession, assignment_id: uuid.UUID
) -> list[Submission]:
    result = await session.exec(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    return list(result.all())


async def get_submissions_by_student(
    session: AsyncSession, student_id: uuid.UUID
) -> list[Submission]:
    result = await session.exec(
        select(Submission).where(Submission.student_id == student_id)
    )
    return list(result.all())


async def delete_submission(session: AsyncSession, submission_id: uuid.UUID) -> bool:
    submission = await get_submission(session, submission_id)
    if not submission:
        return False
    await session.delete(submission)
    await session.commit()
    return True
