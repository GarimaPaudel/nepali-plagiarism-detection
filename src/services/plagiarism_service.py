"""
Plagiarism service — runs the full check pipeline and persists results.

Called by:
  - Celery worker (async path, production)
  - API endpoint directly (sync fallback, dev mode)
"""
import uuid

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database.models.submission import PlagiarismResult, Submission
from src.ml.pipeline import compare_against_corpus


async def run_check_and_save(
    session: AsyncSession, submission_id: uuid.UUID
) -> list[PlagiarismResult]:
    """
    Run plagiarism check for a submission and persist each result row.
    Returns the saved PlagiarismResult rows.
    """
    result = await session.exec(select(Submission).where(Submission.id == submission_id))
    submission: Submission | None = result.first()
    if not submission:
        raise ValueError(f"Submission {submission_id} not found")

    # Mark pending results as running
    pending = await session.exec(
        select(PlagiarismResult).where(
            PlagiarismResult.submission_id == submission_id,
            PlagiarismResult.status == "pending",
        )
    )
    for row in pending.all():
        row.status = "running"
    await session.commit()

    raw_results = compare_against_corpus(submission.content)
    if raw_results is None:
        logger.error("Corpus directory missing — cannot run plagiarism check.")
        return []

    saved = []
    for r in raw_results:
        existing_result = await session.exec(
            select(PlagiarismResult).where(
                PlagiarismResult.submission_id == submission_id,
                PlagiarismResult.reference_filename == r["filename"],
            )
        )
        existing = existing_result.first()
        if existing:
            row = existing
        else:
            row = PlagiarismResult(
                submission_id=submission_id,
                reference_filename=r["filename"],
            )
            session.add(row)

        row.tfidf_similarity = r["similarity_score"]
        row.xlm_similarity = r.get("xlm_similarity")
        row.is_plagiarized = r["is_plagiarized"]
        row.matched_sentences = r["matches"]
        row.status = "done"
        saved.append(row)

    await session.commit()
    for row in saved:
        await session.refresh(row)

    return saved


def get_worst_similarity(results: list[PlagiarismResult]) -> float:
    scores = [r.tfidf_similarity for r in results if r.tfidf_similarity is not None]
    return max(scores, default=0.0)
