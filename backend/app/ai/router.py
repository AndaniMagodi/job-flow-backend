import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.schemas import JobMatchResult, MatchRequest, SearchFilters, SearchRequest
from app.ai.service import AIServiceError, AIUnavailableError, ai_service
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.jobs.router import MAX_PAGE_SIZE, _apply_filters
from app.jobs.schemas import JobResponse
from app.models.jobs import Job, JobMatch
from app.models.users import User

router = APIRouter(prefix="/ai", tags=["ai"])


class AIStatus(BaseModel):
    available: bool
    model: str | None = None


class SmartSearchResponse(BaseModel):
    filters: SearchFilters
    items: list[JobResponse]
    total: int


@router.get("/status", response_model=AIStatus)
def ai_status():
    """Lets the UI hide AI affordances instead of offering a button that 503s."""
    return AIStatus(
        available=ai_service.is_available(),
        model=ai_service.model if ai_service.is_available() else None,
    )


@router.post("/match", response_model=JobMatchResult)
def match_cv_to_job(
    body: MatchRequest,
    refresh: bool = Query(False, description="Ignore any cached match and re-run"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(Job, body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    cv_hash = hashlib.sha256(body.cv_text.strip().encode("utf-8")).hexdigest()

    if not refresh:
        cached = (
            db.query(JobMatch)
            .filter(
                JobMatch.user_id == current_user.id,
                JobMatch.job_id == job.id,
                JobMatch.cv_hash == cv_hash,
            )
            .one_or_none()
        )
        if cached:
            return _to_result(cached)

    try:
        result = ai_service.match_cv_to_job(
            cv_text=body.cv_text,
            job={
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "province": job.province,
                "experience_level": job.experience_level,
                "contract_type": job.contract_type,
                "description": job.description,
            },
        )
    except AIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}") from e

    _persist(db, current_user.id, job.id, cv_hash, result)
    return result


@router.post("/search", response_model=SmartSearchResponse)
def smart_search(
    body: SearchRequest,
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    """Parse a plain-English query into filters, then run it against the board."""
    try:
        parsed = ai_service.parse_search_query(body.query)
    except AIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI search failed: {e}") from e

    filters = SearchFilters.model_validate(parsed)

    query = _apply_filters(
        db.query(Job),
        q=filters.keywords,
        province=filters.province,
        is_remote=filters.is_remote,
        category=filters.category,
        experience_level=filters.experience_level,
        contract_type=filters.contract_type,
        salary_min=filters.salary_min,
        salary_max=filters.salary_max,
    )

    total = query.count()
    items = (
        query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        .limit(page_size)
        .all()
    )

    return SmartSearchResponse(filters=filters, items=items, total=total)


def _persist(db: Session, user_id: int, job_id: int, cv_hash: str, result: dict) -> None:
    db.add(
        JobMatch(
            user_id=user_id,
            job_id=job_id,
            cv_hash=cv_hash,
            match_score=result["match_score"],
            verdict=result["verdict"],
            summary=result["summary"],
            strengths=json.dumps(result.get("strengths", [])),
            gaps=json.dumps(result.get("gaps", [])),
            suggestions=json.dumps(result.get("suggestions", [])),
        )
    )
    db.commit()


def _to_result(match: JobMatch) -> JobMatchResult:
    return JobMatchResult(
        match_score=match.match_score,
        verdict=match.verdict,
        summary=match.summary,
        strengths=json.loads(match.strengths),
        gaps=json.loads(match.gaps),
        suggestions=json.loads(match.suggestions),
    )
