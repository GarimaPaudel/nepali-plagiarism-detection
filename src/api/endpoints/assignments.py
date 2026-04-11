from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.main import get_session
from src.schemas.assignment_schemas import CreateAssignment, UpdateAssignment, AssignmentResponse
from src.services.assignments import (
    create_assignment,
    get_assignment,
    get_all_assignments,
    update_assignment,
    delete_assignment,
)
import uuid

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create(details: CreateAssignment, session: AsyncSession = Depends(get_session)):
    return await create_assignment(session, details)


@router.get("/", response_model=list[AssignmentResponse])
async def list_assignments(session: AsyncSession = Depends(get_session)):
    return await get_all_assignments(session)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_one(assignment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    assignment = await get_assignment(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update(
    assignment_id: uuid.UUID,
    details: UpdateAssignment,
    session: AsyncSession = Depends(get_session),
):
    assignment = await update_assignment(session, assignment_id, details)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(assignment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    deleted = await delete_assignment(session, assignment_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
