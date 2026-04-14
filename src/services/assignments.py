from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.models.assignment import Assignment
from src.schemas.assignment_schemas import CreateAssignment, UpdateAssignment
import uuid


async def create_assignment(
    session: AsyncSession, details: CreateAssignment, created_by: uuid.UUID
) -> Assignment:
    assignment = Assignment(
        topic=details.topic,
        description=details.description,
        due_date=details.due_date,
        created_by=created_by,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def get_assignment(session: AsyncSession, assignment_id: uuid.UUID) -> Assignment | None:
    result = await session.exec(select(Assignment).where(Assignment.id == assignment_id))
    return result.first()


async def get_all_assignments(session: AsyncSession) -> list[Assignment]:
    result = await session.exec(select(Assignment))
    return list(result.all())


async def update_assignment(
    session: AsyncSession, assignment_id: uuid.UUID, details: UpdateAssignment
) -> Assignment | None:
    assignment = await get_assignment(session, assignment_id)
    if not assignment:
        return None
    for field, value in details.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def delete_assignment(session: AsyncSession, assignment_id: uuid.UUID) -> bool:
    assignment = await get_assignment(session, assignment_id)
    if not assignment:
        return False
    await session.delete(assignment)
    await session.commit()
    return True
