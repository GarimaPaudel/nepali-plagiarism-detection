import io
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.deps import CurrentUser, TeacherUser
from src.core.exception import CustomException, ForbiddenException, NotFoundException
from src.core.responses import APIResponse
from src.database.main import get_session
from src.database.models.submission import PlagiarismResult, Submission
from src.ml.pipeline import extract_text_from_pdf
from src.schemas.submission_schemas import (
    CheckStatusResponse,
    PlagiarismResultResponse,
    SubmissionResponse,
)
from src.services.plagiarism_service import get_worst_similarity, run_check_and_save
from src.services.report_service import build_pdf_report

router = APIRouter(prefix="/submissions", tags=["submissions"])


# ---------------------------------------------------------------------------
# POST /submissions/   — student submits a file (txt or pdf)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=APIResponse[SubmissionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def submit_assignment(
    assignment_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        if file.filename.endswith(".txt"):
            content = (await file.read()).decode("utf-8", errors="ignore")
        elif file.filename.endswith(".pdf"):
            content = extract_text_from_pdf(io.BytesIO(await file.read()))
        else:
            from src.core.exception import CustomException
            raise CustomException(message="Only .txt and .pdf files are accepted")

        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            content=content,
        )
        session.add(submission)
        await session.flush()  # get submission.id before commit

        # Seed pending result rows so status polling works immediately
        import os
        from src.config import settings
        corpus_path = settings.CORPUS_PATH
        if os.path.exists(corpus_path):
            for fname in os.listdir(corpus_path):
                if fname.endswith((".txt", ".pdf")):
                    session.add(PlagiarismResult(
                        submission_id=submission.id,
                        reference_filename=fname,
                        status="pending",
                    ))

        await session.commit()
        await session.refresh(submission)

        # Dispatch async Celery task; fall back to sync if Celery unavailable
        try:
            from src.tasks.plagiarism_tasks import run_plagiarism_check
            task = run_plagiarism_check.delay(str(submission.id))
            # Stamp task_id on pending rows
            pending_rows = await session.exec(
                select(PlagiarismResult).where(
                    PlagiarismResult.submission_id == submission.id
                )
            )
            for row in pending_rows.all():
                row.task_id = task.id
            await session.commit()
        except Exception:
            # Celery not available — run synchronously
            await run_check_and_save(session, submission.id)

        await session.refresh(submission)
        return APIResponse(
            success=True,
            message="Submission created and plagiarism check triggered",
            data=submission,
        )
    except Exception as e:
        logger.error(f"Error creating submission: {e!s}")
        raise CustomException(message="Error while creating submission") from e


# ---------------------------------------------------------------------------
# GET /submissions/{submission_id}/status
# ---------------------------------------------------------------------------

@router.get(
    "/{submission_id}/status",
    response_model=APIResponse[CheckStatusResponse],
)
async def check_status(
    submission_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        result = await session.exec(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.first()
        if not submission:
            raise NotFoundException(message="Submission not found")
        if submission.student_id != current_user.id and current_user.role.value != "teacher":
            raise ForbiddenException(message="Not your submission")

        results_result = await session.exec(
            select(PlagiarismResult).where(
                PlagiarismResult.submission_id == submission_id
            )
        )
        results = results_result.all()

        statuses = {r.status for r in results}
        if statuses == {"done"}:
            overall = "done"
        elif "failed" in statuses:
            overall = "failed"
        elif statuses == {"pending"} or not statuses:
            overall = "pending"
        else:
            overall = "running"

        max_similarity = get_worst_similarity(results) if overall == "done" else None

        return APIResponse(
            success=True,
            message="Status retrieved successfully",
            data=CheckStatusResponse(
                submission_id=submission_id,
                overall_status=overall,
                max_tfidf_similarity=max_similarity,
                results=[PlagiarismResultResponse.model_validate(r) for r in results],
            ),
        )
    except (NotFoundException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Error retrieving status: {e!s}")
        raise CustomException(message="Error retrieving plagiarism status") from e


# ---------------------------------------------------------------------------
# GET /submissions/{submission_id}/report  — download PDF
# ---------------------------------------------------------------------------

@router.get("/{submission_id}/report")
async def download_report(
    submission_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.exec(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.first()
        if not submission:
            raise NotFoundException(message="Submission not found")
        if submission.student_id != current_user.id and current_user.role.value != "teacher":
            raise ForbiddenException(message="Not your submission")

        results_result = await session.exec(
            select(PlagiarismResult).where(
                PlagiarismResult.submission_id == submission_id,
                PlagiarismResult.status == "done",
            )
        )
        results = results_result.all()

        buf = io.BytesIO()
        build_pdf_report(buf, submission.content, results)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{submission_id}.pdf"
            },
        )
    except (NotFoundException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e!s}")
        raise CustomException(message="Error generating plagiarism report") from e


# ---------------------------------------------------------------------------
# Existing list endpoints kept intact
# ---------------------------------------------------------------------------

@router.get("/{submission_id}", response_model=APIResponse[SubmissionResponse])
async def get_one(
    submission_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        result = await session.exec(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.first()
        if not submission:
            raise NotFoundException(message="Submission not found")
        return APIResponse(
            success=True, message="Submission retrieved successfully", data=submission
        )
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving submission: {e!s}")
        raise CustomException(message="Error retrieving submission") from e


@router.get(
    "/by-assignment/{assignment_id}",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def by_assignment(
    assignment_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        result = await session.exec(
            select(Submission).where(Submission.assignment_id == assignment_id)
        )
        submissions = result.all()
        return APIResponse(
            success=True, message="Submissions retrieved successfully", data=submissions
        )
    except Exception as e:
        logger.error(f"Error retrieving submissions: {e!s}")
        raise CustomException(message="Error retrieving submissions") from e


@router.get(
    "/by-student/{student_id}",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def by_student(
    student_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        result = await session.exec(
            select(Submission).where(Submission.student_id == student_id)
        )
        submissions = result.all()
        return APIResponse(
            success=True, message="Submissions retrieved successfully", data=submissions
        )
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
        result = await session.exec(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.first()
        if not submission:
            raise NotFoundException(message="Submission not found")
        await session.delete(submission)
        await session.commit()
        return APIResponse(success=True, message="Submission deleted successfully")
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting submission: {e!s}")
        raise CustomException(message="Error deleting submission") from e
