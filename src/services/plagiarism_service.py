"""
Plagiarism service — runs the full check pipeline and persists results.

Two comparison passes per submission:
  1. Corpus check  — against static reference files in /app/corpus/
  2. Peer check    — against all other submissions for the same assignment

Called by:
  - Celery worker (async path, production)
  - API endpoint directly (sync fallback, dev mode)
"""
import uuid

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database.models.submission import PlagiarismResult, Submission
from src.ml.pipeline import compare_against_corpus, compare_against_submissions, get_submission_text


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

    if not submission.file_path:
        raise ValueError(f"Submission {submission_id} has no file_path — cannot run check.")

    submitted_text = get_submission_text(submission.file_path)

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

    saved = []

    # ------------------------------------------------------------------
    # Pass 1: corpus comparison
    # ------------------------------------------------------------------
    corpus_results = compare_against_corpus(submitted_text)
    if corpus_results is None:
        logger.error("Corpus directory missing — skipping corpus check.")
    else:
        for r in corpus_results:
            existing_result = await session.exec(
                select(PlagiarismResult).where(
                    PlagiarismResult.submission_id == submission_id,
                    PlagiarismResult.reference_filename == r["filename"],
                )
            )
            existing = existing_result.first()
            row = existing or PlagiarismResult(
                submission_id=submission_id,
                reference_filename=r["filename"],
            )
            if not existing:
                session.add(row)

            row.tfidf_similarity = r["similarity_score"]
            row.xlm_similarity = r.get("xlm_similarity")
            row.is_plagiarized = r["is_plagiarized"]
            row.matched_sentences = r["matches"]
            row.status = "done"
            saved.append(row)

    # ------------------------------------------------------------------
    # Pass 2: peer comparison — all other submissions for same assignment
    # ------------------------------------------------------------------
    peers_result = await session.exec(
        select(Submission).where(
            Submission.assignment_id == submission.assignment_id,
            Submission.id != submission_id,
        )
    )
    peers = peers_result.all()

    if peers:
        peer_dicts = [
            {
                "submission_id": str(p.id),
                "content": get_submission_text(p.file_path) if p.file_path else "",
                "original_filename": p.original_filename,
            }
            for p in peers
            if p.file_path
        ]
        peer_results = compare_against_submissions(submitted_text, peer_dicts)

        for r in peer_results:
            peer_uuid = uuid.UUID(r["submission_id"])
            existing_result = await session.exec(
                select(PlagiarismResult).where(
                    PlagiarismResult.submission_id == submission_id,
                    PlagiarismResult.reference_submission_id == peer_uuid,
                )
            )
            existing = existing_result.first()
            row = existing or PlagiarismResult(
                submission_id=submission_id,
                reference_submission_id=peer_uuid,
            )
            if not existing:
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
