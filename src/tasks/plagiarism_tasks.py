"""
Celery task for async plagiarism checking.

Worker start (from project root inside container):
    celery -A src.tasks.celery_app worker --loglevel=info
"""
import asyncio
import uuid

from loguru import logger

from src.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="src.tasks.plagiarism_tasks.run_plagiarism_check",
)
def run_plagiarism_check(self, submission_id: str):
    """
    Background task: run plagiarism check for a submission and persist results.
    submission_id is str (UUID) because Celery serializes over JSON.
    """
    from src.database.main import async_session_maker
    from src.services.plagiarism_service import run_check_and_save

    sid = uuid.UUID(submission_id)

    async def _run():
        async with async_session_maker() as session:
            await run_check_and_save(session, sid)

    try:
        logger.info(f"Starting plagiarism check for submission_id {submission_id}")
        asyncio.run(_run())
        logger.info(f"Plagiarism check complete for submission_id {submission_id}")
    except Exception as exc:
        logger.exception("Plagiarism check failed for submission_id {submission_id}")
        raise self.retry(exc=exc)
