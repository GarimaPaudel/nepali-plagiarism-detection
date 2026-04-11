from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.main import get_session
from src.schemas.submission_schemas import CreateSubmission, SubmissionResponse
from src.services.submissions import (
    create_submission,
    get_submission,
    get_submissions_by_assignment,
    get_submissions_by_student,
    delete_submission,
)
import uuid

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create(details: CreateSubmission, session: AsyncSession = Depends(get_session)):
    return await create_submission(session, details)


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_one(submission_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    submission = await get_submission(session, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


@router.get("/by-assignment/{assignment_id}", response_model=list[SubmissionResponse])
async def by_assignment(assignment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await get_submissions_by_assignment(session, assignment_id)


@router.get("/by-student/{student_id}", response_model=list[SubmissionResponse])
async def by_student(student_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await get_submissions_by_student(session, student_id)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(submission_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    deleted = await delete_submission(session, submission_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
