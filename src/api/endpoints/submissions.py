from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.deps import CurrentUser, TeacherUser
from src.core.exception import CustomException, NotFoundException
from src.core.responses import APIResponse
from src.database.main import get_session
from src.schemas.submission_schemas import CreateSubmission, SubmissionResponse
from src.services.submissions import (
    create_submission,
    delete_submission,
    get_submission,
    get_submissions_by_assignment,
    get_submissions_by_student,
)
import uuid

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/", response_model=APIResponse[SubmissionResponse], status_code=status.HTTP_201_CREATED)
async def create(
    details: CreateSubmission,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        submission = await create_submission(session, details, student_id=current_user.id)
        return APIResponse(success=True, message="Submission created successfully", data=submission)
    except Exception as e:
        logger.error(f"Error creating submission: {e!s}")
        raise CustomException(message="Error while creating submission") from e


@router.get("/{submission_id}", response_model=APIResponse[SubmissionResponse])
async def get_one(
    submission_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        submission = await get_submission(session, submission_id)
        if not submission:
            raise NotFoundException(message="Submission not found")
        return APIResponse(success=True, message="Submission retrieved successfully", data=submission)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving submission: {e!s}")
        raise CustomException(message="Error retrieving submission") from e


@router.get("/by-assignment/{assignment_id}", response_model=APIResponse[list[SubmissionResponse]])
async def by_assignment(
    assignment_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        submissions = await get_submissions_by_assignment(session, assignment_id)
        return APIResponse(success=True, message="Submissions retrieved successfully", data=submissions)
    except Exception as e:
        logger.error(f"Error retrieving submissions: {e!s}")
        raise CustomException(message="Error retrieving submissions") from e


@router.get("/by-student/{student_id}", response_model=APIResponse[list[SubmissionResponse]])
async def by_student(
    student_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        submissions = await get_submissions_by_student(session, student_id)
        return APIResponse(success=True, message="Submissions retrieved successfully", data=submissions)
    except Exception as e:
        logger.error(f"Error retrieving submissions: {e!s}")
        raise CustomException(message="Error retrieving submissions") from e


@router.delete("/{submission_id}", response_model=APIResponse)
async def delete(
    submission_id: uuid.UUID,
    _current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        deleted = await delete_submission(session, submission_id)
        if not deleted:
            raise NotFoundException(message="Submission not found")
        return APIResponse(success=True, message="Submission deleted successfully")
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting submission: {e!s}")
        raise CustomException(message="Error deleting submission") from e
