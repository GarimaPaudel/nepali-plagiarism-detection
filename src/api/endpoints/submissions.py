import io
import os
import uuid
from pathlib import Path


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
        raw_bytes = await file.read()
        original_filename = file.filename or "upload"

        if not original_filename.endswith((".txt", ".pdf")):
            raise CustomException(message="Only .txt and .pdf files are accepted")

        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            original_filename=original_filename,
        )
        session.add(submission)
        await session.flush()  # get submission.id before commit

        # Save file to disk: /app/uploads/{assignment_id}/{submission_id}_{filename}
        from src.config import settings as app_settings
        upload_dir = Path(app_settings.UPLOADS_PATH) / str(assignment_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{submission.id}_{original_filename}"
        file_path.write_bytes(raw_bytes)
        submission.file_path = str(file_path)

        # Seed pending result rows so status polling works immediately
        corpus_path = app_settings.CORPUS_PATH
        if os.path.exists(corpus_path):
            for fname in os.listdir(corpus_path):
                if fname.endswith((".txt", ".pdf")):
                    session.add(PlagiarismResult(
                        submission_id=submission.id,
                        reference_filename=fname,
                        status="pending",
                    ))

        # Seed pending rows for existing peer submissions in the same assignment
        peers_result = await session.exec(
            select(Submission).where(
                Submission.assignment_id == assignment_id,
                Submission.id != submission.id,
            )
        )
        for peer in peers_result.all():
            session.add(PlagiarismResult(
                submission_id=submission.id,
                reference_submission_id=peer.id,
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

        if not submission.file_path:
            raise CustomException(message="Submission file not found on disk")

        buf = io.BytesIO()
        build_pdf_report(buf, submission.file_path, results)
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
