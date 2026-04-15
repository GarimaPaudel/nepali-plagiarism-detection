from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.deps import CurrentUser, TeacherUser
from src.core.exception import CustomException, NotFoundException
from src.core.responses import APIResponse
from src.database.main import get_session
from src.schemas.assignment_schemas import AssignmentResponse, CreateAssignment, UpdateAssignment
from src.services.assignments import (
    create_assignment,
    delete_assignment,
    get_all_assignments,
    get_assignment,
    update_assignment,
)
import uuid

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("/", response_model=APIResponse[AssignmentResponse], status_code=status.HTTP_201_CREATED)
async def create(
    details: CreateAssignment,
    current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        assignment = await create_assignment(session, details, created_by=current_user.id)
        return APIResponse(success=True, message="Assignment created successfully", data=assignment)
    except Exception as e:
        logger.error(f"Error creating assignment: {e!s}")
        raise CustomException(message="Error while creating assignment") from e


@router.get("/", response_model=APIResponse[list[AssignmentResponse]])
async def list_assignments(
    _current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> APIResponse:
    try:
        assignments = await get_all_assignments(session)
        return APIResponse(success=True, message="Assignments retrieved successfully", data=assignments)
    except Exception as e:
        logger.error(f"Error listing assignments: {e!s}")
        raise CustomException(message="Error retrieving assignments") from e


@router.get("/{assignment_id}", response_model=APIResponse[AssignmentResponse])
async def get_one(
    assignment_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        assignment = await get_assignment(session, assignment_id)
        return APIResponse(success=True, message="Assignment retrieved successfully", data=assignment)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving assignment: {e!s}")
        raise CustomException(message="Error retrieving assignment") from e


@router.patch("/{assignment_id}", response_model=APIResponse[AssignmentResponse])
async def update(
    assignment_id: uuid.UUID,
    details: UpdateAssignment,
    current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        assignment = await update_assignment(session, assignment_id, details)
        return APIResponse(success=True, message="Assignment updated successfully", data=assignment)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error updating assignment: {e!s}")
        raise CustomException(message="Error updating assignment") from e


@router.delete("/{assignment_id}", response_model=APIResponse)
async def delete(
    assignment_id: uuid.UUID,
    _current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        await delete_assignment(session, assignment_id)
        return APIResponse(success=True, message="Assignment deleted successfully", data =[])
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assignment: {e!s}")
        raise CustomException(message="Error deleting assignment") from e
